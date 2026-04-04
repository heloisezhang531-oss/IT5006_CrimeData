from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from tidb_utils import create_tidb_engine, resolve_chicago_table_name
from backend.app.core.config import settings


class DataProvider:
    def __init__(self) -> None:
        self.mode = settings.data_source_mode.lower()
        self.cache_dir = settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
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
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_cache(self, key: str, payload: dict[str, Any]) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def fetch(
        self,
        key: str,
        fetcher: Callable[[Any, str], dict[str, Any]],
        fallback: Callable[[], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.mode == "cache":
            cached = self._load_cache(key)
            if cached is not None:
                return {**cached, "meta": {**cached.get("meta", {}), "source": "cache"}}
            if fallback:
                payload = fallback()
                payload.setdefault("meta", {})["source"] = "fallback"
                self._save_cache(key, payload)
                return payload
            return {"meta": {"source": "cache", "warning": "cache_miss"}, "data": []}

        try:
            payload = fetcher(self.engine, self.table_name)
            payload.setdefault("meta", {})["source"] = "tidb" if self.db_available else "computed_fallback"
            self._save_cache(key, payload)
            return payload
        except Exception:
            pass

        cached = self._load_cache(key)
        if cached is not None:
            return {**cached, "meta": {**cached.get("meta", {}), "source": "cache_fallback"}}

        if fallback:
            payload = fallback()
            payload.setdefault("meta", {})["source"] = "fallback"
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
