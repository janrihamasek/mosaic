import os
from pathlib import Path
from typing import Optional, Tuple


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
    normalized = server_ip.replace(":", "-").replace(".", "-")
    fallback_cert = base_path / f"{server_ip}.pem"
    fallback_key = base_path / f"{server_ip}-key.pem"

    cert_path = base_path / f"{normalized}.pem"
    key_path = base_path / f"{normalized}-key.pem"

    if not cert_path.exists() or not key_path.exists():
        cert_path = fallback_cert
        key_path = fallback_key

    if not cert_path.exists() or not key_path.exists():
        raise RuntimeError(
            f"SSL certificate or key missing for {server_ip}: {cert_path}, {key_path}. "
            "Ensure mkcert output is placed in ./certs or set SSL_CERT_DIR."
        )

    return str(cert_path), str(key_path)
