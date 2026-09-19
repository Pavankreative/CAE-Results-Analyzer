"""Runtime configuration. Environment variables override the defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Settings:
    app_name: str = "CAE Results Analyzer"
    version: str = "0.1.0"
    data_dir: Path = Path(os.getenv("CAER_DATA_DIR", ROOT / "data"))
    samples_dir: Path = Path(os.getenv("CAER_SAMPLES_DIR", ROOT / "samples"))
    cors_origins: tuple = tuple(
        os.getenv("CAER_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    )
    log_level: str = os.getenv("CAER_LOG_LEVEL", "INFO")
    max_upload_mb: int = int(os.getenv("CAER_MAX_UPLOAD_MB", "200"))


settings = Settings()
