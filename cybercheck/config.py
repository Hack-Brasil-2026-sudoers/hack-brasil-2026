import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class Settings:
    api_token: str
    data_dir: Path = Path(".data")
    app_id: str = ""
    installation_id: str = ""
    private_key_path: str = ""
    osv_bin: str = "osv-scanner"
    betterleaks_bin: str = "betterleaks"
    scanner_timeout: int = 120
    cors_origins: tuple[str, ...] = ()
    github_client_id: str = ""
    github_client_secret: str = ""
    public_url: str = "http://127.0.0.1:8000"
    session_key: str = ""

    def __post_init__(self):
        if not self.github_client_id and len(self.api_token) < 32:
            raise ValueError("CYBERCHECK_API_TOKEN must contain at least 32 random characters.")
        if not 5 <= self.scanner_timeout <= 600:
            raise ValueError("CYBERCHECK_SCANNER_TIMEOUT must be between 5 and 600 seconds.")
        if any((self.github_client_id, self.github_client_secret, self.session_key)):
            if not all((self.github_client_id, self.github_client_secret, self.session_key)):
                raise ValueError("Configure GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, and CYBERCHECK_SESSION_KEY together.")
            if "*" in self.cors_origins:
                raise ValueError("GitHub login requires explicit CORS origins; wildcard origins are not allowed.")
            try:
                Fernet(self.session_key.encode())
            except (ValueError, TypeError) as exc:
                raise ValueError("CYBERCHECK_SESSION_KEY must be a valid Fernet key.") from exc
            url = urlsplit(self.public_url)
            if (url.scheme not in ("http", "https") or not url.hostname or url.username or url.password
                    or url.path or url.query or url.fragment
                    or (url.scheme == "http" and url.hostname not in ("127.0.0.1", "localhost"))):
                raise ValueError("CYBERCHECK_PUBLIC_URL must be an HTTPS origin, or HTTP on localhost/127.0.0.1.")

    @classmethod
    def from_env(cls):
        return cls(
            api_token=os.getenv("CYBERCHECK_API_TOKEN", ""),
            data_dir=Path(os.getenv("CYBERCHECK_DATA_DIR", ".data")).resolve(),
            app_id=os.getenv("GITHUB_APP_ID", ""),
            installation_id=os.getenv("GITHUB_INSTALLATION_ID", ""),
            private_key_path=os.getenv("GITHUB_PRIVATE_KEY_PATH", ""),
            osv_bin=os.getenv("OSV_SCANNER_BIN", "osv-scanner"),
            betterleaks_bin=os.getenv("BETTERLEAKS_BIN", "betterleaks"),
            scanner_timeout=int(os.getenv("CYBERCHECK_SCANNER_TIMEOUT", "120")),
            cors_origins=tuple(filter(None, (v.strip() for v in os.getenv(
                "CYBERCHECK_CORS_ORIGINS", ""
            ).split(",")))),
            github_client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            github_client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            public_url=os.getenv("CYBERCHECK_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/"),
            session_key=os.getenv("CYBERCHECK_SESSION_KEY", ""),
        )
