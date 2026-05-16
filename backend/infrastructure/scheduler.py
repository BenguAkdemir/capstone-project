"""Background jobs — weekly employee data refresh."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.application.employee_service import EmployeeService
from backend.infrastructure.db.session import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _weekly_refresh_job() -> None:
    session = SessionLocal()
    try:
        result = EmployeeService(session).run_weekly_refresh()
        logger.info("Weekly employee refresh completed: %s", result)
    except Exception:
        logger.exception("Weekly employee refresh failed")
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.weekly_refresh_enabled:
        logger.info("Weekly refresh scheduler disabled")
        return None

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _weekly_refresh_job,
        trigger=CronTrigger(
            day_of_week=settings.weekly_refresh_day,
            hour=settings.weekly_refresh_hour,
            minute=0,
        ),
        id="weekly_employee_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Weekly refresh scheduled: every %s at %02d:00",
        settings.weekly_refresh_day,
        settings.weekly_refresh_hour,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
