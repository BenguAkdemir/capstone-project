"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.employee_routes import router as employee_router
from backend.api.error_handlers import register_error_handlers
from backend.api.routes import router
from backend.config import settings
from backend.infrastructure.db.seed import seed_database_if_empty
from backend.infrastructure.db.session import SessionLocal, init_database
from backend.infrastructure.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    db = SessionLocal()
    try:
        if seed_database_if_empty(db):
            logger.info("Database seeded with 10 mock employees")
    finally:
        db.close()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Hybrid Work Scheduling API",
    description="Generates optimal weekly hybrid work schedules using Gurobi optimization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(employee_router)
register_error_handlers(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
