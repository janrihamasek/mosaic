import uuid

from app import stream_rtsp


FAKE_FRAME_CHUNK = (
    b"--frame\r\n"
    b"Content-Type: image/jpeg\r\n"
    b"Content-Length: 4\r\n\r\n"
    b"data"
    b"\r\n"
)


def _create_user_and_token(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    password = "StrongPass123"
    register = client.post("/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    payload = login.get_json()
    return payload["access_token"]


def test_stream_proxy_authorized_ok(client, monkeypatch):
    token = _create_user_and_token(client)
    captured = {}

    def fake_stream(url, username, password):
        captured["args"] = (url, username, password)
        yield FAKE_FRAME_CHUNK

    monkeypatch.setattr("app.stream_rtsp", fake_stream)

    response = client.get(
        "/api/stream-proxy",
        query_string={"url": "rtsp://camera.local/live", "username": "user", "password": "secret"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.mimetype == "multipart/x-mixed-replace"
    assert captured["args"] == ("rtsp://camera.local/live", "user", "secret")

    iterator = iter(response.response)
    first_chunk = next(iterator)
    assert b"--frame" in first_chunk
    response.close()


def test_stream_proxy_unauthorized(client):
    response = client.get("/api/stream-proxy")
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["code"] == "unauthorized"


def test_stream_proxy_rate_limit(client, monkeypatch):
    token = _create_user_and_token(client)

    def fake_stream(*_args, **_kwargs):
        yield FAKE_FRAME_CHUNK

    monkeypatch.setattr("app.stream_rtsp", fake_stream)

    for _ in range(2):
        resp = client.get(
            "/api/stream-proxy",
            query_string={"url": "rtsp://camera.local/live"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        next(iter(resp.response))
        resp.close()

    third = client.get(
        "/api/stream-proxy",
        query_string={"url": "rtsp://camera.local/live"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert third.status_code == 429
    payload = third.get_json()
    assert payload["error"]["code"] == "too_many_requests"


def test_stream_proxy_disconnect(monkeypatch):
    class FakeStdout:
        def __init__(self, frame):
            self._frame = frame
            self._read_count = 0
            self.closed = False

        def read(self, _size):
            if self._read_count == 0:
                self._read_count += 1
                return self._frame
            return b""

        def close(self):
            self.closed = True

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeStdout(b"\xff\xd8data\xff\xd9")
            self.stderr = None
            self.terminated = False
            self.killed = False
            self.wait_called = False

        def poll(self):
            return None if not self.terminated else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            self.wait_called = True
            return 0

        def kill(self):
            self.killed = True

    created = {}

    def fake_popen(*_args, **_kwargs):
        process = FakeProcess()
        created["process"] = process
        return process

    monkeypatch.setattr("app.subprocess.Popen", fake_popen)

    generator = stream_rtsp("rtsp://camera.local/live", "", "")
    first_chunk = next(generator)
    assert b"--frame" in first_chunk

    generator.close()

    process = created["process"]
    assert process.terminated is True
    assert process.wait_called is True
    assert process.killed is False
    assert process.stdout.closed is True
