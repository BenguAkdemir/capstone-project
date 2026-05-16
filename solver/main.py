"""Solver service FastAPI entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from solver.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

app = FastAPI(
    title="Hybrid Scheduling Solver",
    description="Gurobi-based optimization service for hybrid work scheduling",
    version="1.0.0",
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("solver.main:app", host="0.0.0.0", port=8001, reload=True)
