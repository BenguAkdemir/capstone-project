"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from backend.api.error_handlers import register_error_handlers
from backend.api.routes import router
from backend.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app = FastAPI(
    title="Hybrid Work Scheduling API",
    description="Generates optimal weekly hybrid work schedules using Gurobi optimization",
    version="1.0.0",
)

app.include_router(router)
register_error_handlers(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
