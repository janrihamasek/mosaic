import os
from pathlib import Path
from typing import Optional, Tuple


def _resolve_candidate(path_str: str, base_path: Path) -> Path:
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = base_path / candidate
    return candidate


def _find_cert_directory() -> Path:
    env_dir = os.environ.get("SSL_CERT_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if candidate.exists():
            return candidate

    docker_dir = Path("/certs")
    if docker_dir.exists():
        return docker_dir

    cwd_dir = Path.cwd() / "certs"
    if cwd_dir.exists():
        return cwd_dir

    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        candidate = parent / "certs"
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "SSL_CERT_DIR not set and no 'certs' directory found. "
        "Place certificates in ./certs or specify SSL_CERT_DIR."
    )


def resolve_ssl_context() -> Optional[Tuple[str, str]]:
    use_https = os.environ.get("USE_HTTPS", "").strip().lower() in ("1", "true", "yes", "on")
    if not use_https:
        return None

    server_ip = os.environ.get("SERVER_IP", "").strip()
    if not server_ip:
        raise RuntimeError("USE_HTTPS is true but SERVER_IP is not configured.")

    base_path = _find_cert_directory()
    cert_override = os.environ.get("TLS_CERT_FILE", "").strip()
    key_override = os.environ.get("TLS_KEY_FILE", "").strip()
    if cert_override or key_override:
        if not cert_override or not key_override:
            raise RuntimeError("Both TLS_CERT_FILE and TLS_KEY_FILE must be set when overriding cert paths.")
        cert_path = _resolve_candidate(cert_override, base_path)
        key_path = _resolve_candidate(key_override, base_path)
        if not cert_path.exists() or not key_path.exists():
            raise RuntimeError(
                f"SSL certificate or key override path missing: {cert_path}, {key_path}. "
                "Check TLS_CERT_FILE/TLS_KEY_FILE."
            )
        return str(cert_path), str(key_path)

    normalized = server_ip.replace(":", "-").replace(".", "-")
    candidate_pairs = [
        (f"{server_ip}.key.pem", f"{server_ip}.key"),
        (f"{server_ip}.pem", f"{server_ip}.key.pem"),
        (f"{server_ip}.pem", f"{server_ip}-key.pem"),
        (f"{normalized}.pem", f"{normalized}-key.pem"),
        (f"{server_ip}.pem", f"{server_ip}.key"),
    ]

    for cert_name, key_name in candidate_pairs:
        cert_path = base_path / cert_name
        key_path = base_path / key_name
        if cert_path.exists() and key_path.exists():
            return str(cert_path), str(key_path)

    raise RuntimeError(
        f"SSL certificate or key missing for {server_ip}: expected one of {candidate_pairs}. "
        "Ensure mkcert output is placed in ./certs or set SSL_CERT_DIR."
    )
