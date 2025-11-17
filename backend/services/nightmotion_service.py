"""
Nightmotion service.

Contains RTSP normalization and FFmpeg proxy logic that yields MJPEG frames.
Controllers are responsible for wrapping responses/streams.
"""

import subprocess
from threading import Thread
from typing import Iterator, Optional
from urllib.parse import urlparse, urlunparse

from security import ValidationError


def normalize_rtsp_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme.lower() != "rtsp":
        raise ValidationError("URL must use rtsp scheme", code="invalid_query")
    if not parsed.hostname:
        raise ValidationError("Invalid stream URL", code="invalid_query")

    normalized = parsed._replace()
    return urlunparse(normalized)


def _drain_process_stream(pipe, collector: list[str]) -> None:
    try:
        for raw in iter(pipe.readline, b""):
            try:
                text = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                text = ""
            if text:
                collector.append(text)
                if len(collector) > 100:
                    del collector[: len(collector) - 100]
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _raise_stream_error(stderr_lines: list[str], return_code: Optional[int]) -> None:
    snippet = "\n".join(stderr_lines[-10:]).lower()
    if "401" in snippet or "unauthorized" in snippet:
        raise PermissionError("Unauthorized stream access")
    raise RuntimeError(
        f"Unable to proxy stream (ffmpeg exited with code {return_code})"
    )


def stream_rtsp(url: str) -> Iterator[bytes]:
    normalized_url = normalize_rtsp_url(url)
    command = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        normalized_url,
        "-f",
        "mjpeg",
        "-q:v",
        "5",
        "-an",
        "-sn",
        "-dn",
        "pipe:1",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    if not process.stdout:
        raise RuntimeError("Failed to start stream process")

    stderr_lines: list[str] = []
    stderr_thread: Optional[Thread] = None
    if process.stderr is not None:
        stderr_thread = Thread(
            target=_drain_process_stream,
            args=(process.stderr, stderr_lines),
            daemon=True,
        )
        stderr_thread.start()

    buffer = bytearray()
    frame_emitted = False
    try:
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                if process.poll() is None:
                    continue
                if not frame_emitted:
                    _raise_stream_error(stderr_lines, process.returncode)
                break

            buffer.extend(chunk)
            while True:
                start_idx = buffer.find(b"\xff\xd8")
                if start_idx == -1:
                    if len(buffer) > 65536:
                        buffer.clear()
                    break
                if start_idx > 0:
                    del buffer[:start_idx]
                end_idx = buffer.find(b"\xff\xd9")
                if end_idx == -1:
                    break

                frame = bytes(buffer[: end_idx + 2])
                del buffer[: end_idx + 2]
                frame_emitted = True

                headers = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                )
                yield headers + frame + b"\r\n"
    except GeneratorExit:
        raise
    finally:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                process.wait(timeout=0.5)
        except Exception:
            pass
        try:
            process.stdout.close()
        except Exception:
            pass
        if process.stderr:
            try:
                process.stderr.close()
            except Exception:
                pass
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=0.5)
