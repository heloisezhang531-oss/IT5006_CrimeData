from __future__ import annotations

from fastapi import APIRouter

from ..deps import provider
from ...services import chicago_service as svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/command-center")
def command_center():
    return provider.fetch("dashboard_command_center", svc.dashboard_command_center)
