import os
from dataclasses import dataclass
from pathlib import Path


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

    def __post_init__(self):
        if len(self.api_token) < 32:
            raise ValueError("CYBERCHECK_API_TOKEN deve ter pelo menos 32 caracteres aleatórios.")
        if not 5 <= self.scanner_timeout <= 600:
            raise ValueError("CYBERCHECK_SCANNER_TIMEOUT deve estar entre 5 e 600 segundos.")

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
        )
