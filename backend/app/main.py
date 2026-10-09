"""Minimal FastAPI application for the FixFlow project skeleton."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router

def _configured_cors_origins() -> list[str]:
    """Return configured frontend origins, with safe local defaults."""

    configured = os.getenv(
        "FIXFLOW_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="FixFlow API",
    description="Backend API for the FixFlow maintenance platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Report whether the FixFlow API process is responding."""

    return {"status": "ok", "service": "fixflow-api"}
