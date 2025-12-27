from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env if present (local dev)
load_dotenv(override=False)


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = [v.strip() for v in value.split(",")]
    return [p for p in parts if p]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    APP_NAME: str = "LifeOS MCP"
    LOG_LEVEL: str = "INFO"

    # SQLite
    SQLITE_DB_PATH: str = "data/lifeos.db"

    # Transport: auto | stdio | http
    MCP_TRANSPORT: str = "auto"
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000

    # Some platforms inject PORT automatically
    PORT: Optional[int] = None

    # Optional sidecar health server (useful in STDIO mode)
    HEALTH_ENABLED: bool = True
    HEALTH_PORT: int = 8000

    # CSV of allowed base directories for filesystem tools
    # Example: ALLOWED_BASE_PATHS="/home/ec2-user,/data"
    ALLOWED_BASE_PATHS: str = "."

    FILE_SEARCH_DEFAULT_LIMIT: int = 50
    FILE_SEARCH_MAX_LIMIT: int = 200
    FILE_LIST_MAX_LIMIT: int = 500
    FILE_READ_MAX_BYTES: int = 200_000

    # Optional API key gate (primarily for HTTP mode)
    REQUIRE_API_KEY: bool = False
    API_KEY: Optional[str] = None

    @property
    def transport(self) -> str:
        t = (self.MCP_TRANSPORT or "auto").strip().lower()
        if t in ("stdio", "http"):
            return t
        # auto
        if self.PORT is not None or os.getenv("PORT"):
            return "http"
        return "stdio"

    @property
    def http_port(self) -> int:
        if self.PORT is not None:
            return int(self.PORT)
        env_port = os.getenv("PORT")
        if env_port:
            try:
                return int(env_port)
            except ValueError:
                pass
        return int(self.MCP_PORT)

    @property
    def allowed_base_paths(self) -> List[Path]:
        items = _split_csv(self.ALLOWED_BASE_PATHS) or ["."]
        paths: List[Path] = []
        for item in items:
            p = Path(item).expanduser()
            try:
                p = p.resolve()
            except Exception:
                p = p.absolute()
            paths.append(p)
        return paths


settings = Settings()
