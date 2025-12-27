from __future__ import annotations

import threading
from typing import Optional

from fastapi import FastAPI
import uvicorn

from app.utils.logger import logger


def start_health_server(port: int, host: str = "0.0.0.0") -> threading.Thread:
    """Start a tiny /health server in a background thread."""

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    def _run() -> None:
        logger.info(f"Starting health server on http://{host}:{port}/health")
        uvicorn.run(app, host=host, port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True, name="health-server")
    thread.start()
    return thread
