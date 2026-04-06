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


@app.middleware("http")
async def cache_control_middleware(request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith(settings.api_prefix):
        if request.url.path == f"{settings.api_prefix}/health":
            response.headers["Cache-Control"] = "no-store"
        elif "Cache-Control" not in response.headers:
            max_age = max(0, settings.api_response_cache_max_age)
            response.headers["Cache-Control"] = f"public, max-age={max_age}, stale-while-revalidate={max_age}"
    return response


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
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(eda.router, prefix=settings.api_prefix)
