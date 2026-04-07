from __future__ import annotations

import copy
import json
import time
from datetime import date, datetime
from threading import RLock
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from tidb_utils import create_tidb_engine, resolve_chicago_table_name
from ..core.config import settings


class DataProvider:
    def __init__(self) -> None:
        self.mode = settings.data_source_mode.lower()
        self.cache_dir = settings.cache_dir
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Serverless runtimes may have read-only project directories.
            self.cache_dir = Path("/tmp/data_cache")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_seconds = max(0, settings.api_cache_ttl_seconds)
        self.cache_max_entries = max(16, settings.api_cache_max_entries)
        self._memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_lock = RLock()
        self.engine = None
        self.table_name = settings.table_name
        if self.mode in {"hybrid", "tidb"}:
            try:
                self.engine = create_tidb_engine()
                self.table_name = resolve_chicago_table_name(self.engine, preferred=settings.table_name)
            except Exception:
                self.engine = None

    @property
    def db_available(self) -> bool:
        return self.engine is not None

    def _cache_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"{safe}.json"

    def _load_cache(self, key: str) -> dict[str, Any] | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_cache(self, key: str, payload: dict[str, Any]) -> None:
        def _json_default(value: Any):
            if isinstance(value, (datetime, date, pd.Timestamp)):
                return value.isoformat()
            if hasattr(value, "item"):
                try:
                    return value.item()
                except Exception:
                    pass
            if isinstance(value, Path):
                return str(value)
            return str(value)

        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, default=_json_default), encoding="utf-8")

    def _load_memory_cache(self, key: str) -> dict[str, Any] | None:
        if self.cache_ttl_seconds <= 0:
            return None
        now = time.monotonic()
        with self._cache_lock:
            entry = self._memory_cache.get(key)
            if entry is None:
                return None
            expires_at, payload = entry
            if expires_at <= now:
                self._memory_cache.pop(key, None)
                return None
            return copy.deepcopy(payload)

    def _save_memory_cache(self, key: str, payload: dict[str, Any]) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        expires_at = time.monotonic() + float(self.cache_ttl_seconds)
        with self._cache_lock:
            if len(self._memory_cache) >= self.cache_max_entries:
                oldest_key = min(self._memory_cache.items(), key=lambda item: item[1][0])[0]
                self._memory_cache.pop(oldest_key, None)
            self._memory_cache[key] = (expires_at, copy.deepcopy(payload))

    def fetch(
        self,
        key: str,
        fetcher: Callable[[Any, str], dict[str, Any]],
        fallback: Callable[[], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        memory_cached = self._load_memory_cache(key)
        if memory_cached is not None:
            return {**memory_cached, "meta": {**memory_cached.get("meta", {}), "source": "memory_cache"}}

        if self.mode == "cache":
            cached = self._load_cache(key)
            if cached is not None:
                self._save_memory_cache(key, cached)
                return {**cached, "meta": {**cached.get("meta", {}), "source": "cache"}}
            if fallback:
                payload = fallback()
                payload.setdefault("meta", {})["source"] = "fallback"
                self._save_memory_cache(key, payload)
                self._save_cache(key, payload)
                return payload
            return {"meta": {"source": "cache", "warning": "cache_miss"}, "data": []}

        try:
            payload = fetcher(self.engine, self.table_name)
            payload.setdefault("meta", {})["source"] = "tidb" if self.db_available else "computed_fallback"
            self._save_memory_cache(key, payload)
            self._save_cache(key, payload)
            return payload
        except Exception:
            pass

        cached = self._load_cache(key)
        if cached is not None:
            self._save_memory_cache(key, cached)
            return {**cached, "meta": {**cached.get("meta", {}), "source": "cache_fallback"}}

        if fallback:
            payload = fallback()
            payload.setdefault("meta", {})["source"] = "fallback"
            self._save_memory_cache(key, payload)
            self._save_cache(key, payload)
            return payload

        return {"meta": {"source": "unavailable"}, "data": []}


provider = DataProvider()


def df_payload(df: pd.DataFrame, **meta: Any) -> dict[str, Any]:
    if df is None or df.empty:
        return {"meta": {**meta, "rows": 0}, "data": []}
    data = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {"meta": {**meta, "rows": len(data)}, "data": data}


def series_payload(items: Iterable[dict[str, Any]], **meta: Any) -> dict[str, Any]:
    data = list(items)
    return {"meta": {**meta, "rows": len(data)}, "data": data}
