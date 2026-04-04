from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.deps import provider
from backend.app.api.routes import (
    anomaly,
    crime_action,
    dashboard,
    eda,
    meta,
    model,
    model_lab,
    operations,
    performance,
    socio,
    strategic,
)
from backend.app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "meta": {
            "app": settings.app_name,
            "version": settings.app_version,
            "data_source_mode": provider.mode,
            "db_available": provider.db_available,
        },
        "data": [{"status": "ok"}],
    }


app.include_router(meta.router, prefix=settings.api_prefix)
app.include_router(strategic.router, prefix=settings.api_prefix)
app.include_router(operations.router, prefix=settings.api_prefix)
app.include_router(crime_action.router, prefix=settings.api_prefix)
app.include_router(anomaly.router, prefix=settings.api_prefix)
app.include_router(socio.router, prefix=settings.api_prefix)
app.include_router(performance.router, prefix=settings.api_prefix)
app.include_router(model.router, prefix=settings.api_prefix)
app.include_router(model_lab.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(eda.router, prefix=settings.api_prefix)
