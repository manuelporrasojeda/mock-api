"""Application entry point for the mock API."""

from fastapi import FastAPI

from app.api.routes import router
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Mock API for systemic token, user token, and status data endpoints, "
        "including configurable delay scenarios for testing."
    ),
)

app.include_router(router)
