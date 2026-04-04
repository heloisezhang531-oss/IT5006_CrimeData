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


class VictimDashboardRequest(BaseModel):
    age_min: int | None = None
    age_max: int | None = None
    offense_categories: list[str] = Field(default_factory=list)
    include_raw_sample: bool = False
    raw_limit: int = Field(default=100, ge=1, le=1000)
