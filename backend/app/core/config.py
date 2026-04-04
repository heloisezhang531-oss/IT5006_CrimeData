from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Crime Intelligence API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    data_source_mode: str = os.getenv("DATA_SOURCE_MODE", "hybrid")
    cache_dir: Path = Path(os.getenv("CACHE_DIR", "data_cache"))
    table_name: str = os.getenv("CHICAGO_TABLE", "chicago_crimes")
    mapbox_token: str = os.getenv("MAPBOX_TOKEN", "")


settings = Settings()
