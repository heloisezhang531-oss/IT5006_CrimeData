from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    data: list[Any] = Field(default_factory=list)


class PredictRequest(BaseModel):
    target_month: str | None = None
    region_ids: list[int] = Field(default_factory=list)
    feature_mode: str = "with_hardship"
