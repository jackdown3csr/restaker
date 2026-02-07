"""
Background scheduler for automatic restaking.

Uses APScheduler to run restake jobs at configured intervals.
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class RestakeScheduler:
    """Manages background scheduling of restake operations."""

    def __init__(self, on_restake: Callable[[], dict], on_error: Optional[Callable[[Exception], None]] = None):
        """
        Initialize scheduler.

        Args:
            on_restake: Callback function that performs the restake and returns result dict.
            on_error: Optional callback for error handling.
        """
        self.on_restake = on_restake
        self.on_error = on_error
        self.scheduler = BackgroundScheduler()
        self.job = None
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[dict] = None
        self.is_running = False

    def _execute_restake(self) -> None:
        """Execute restake and handle result/errors."""
        try:
            logger.info("Scheduler triggered restake")
            self.last_run = datetime.now()
            self.last_result = self.on_restake()
            logger.info(f"Restake completed: {self.last_result}")
        except Exception as e:
            logger.error(f"Restake failed: {e}")
            if self.on_error:
                self.on_error(e)

    def start(self, interval_hours: int = 1) -> None:
        """Start the scheduler with given interval."""
        if self.is_running:
            self.stop()

        self._ensure_scheduler()
        self.job = self.scheduler.add_job(
            self._execute_restake,
            trigger=IntervalTrigger(hours=interval_hours),
            id='restake_job',
            name='Auto-Restake',
            replace_existing=True,
            next_run_time=datetime.now()  # Run immediately on start
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started with {interval_hours}h interval")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.job = None
            logger.info("Scheduler stopped")

    def _ensure_scheduler(self) -> None:
        """Ensure a fresh scheduler instance exists for (re)starting."""
        if not self.is_running:
            self.scheduler = BackgroundScheduler()

    def run_now(self) -> None:
        """Trigger immediate restake (outside of schedule)."""
        self._execute_restake()

    def get_next_run(self) -> Optional[datetime]:
        """Get next scheduled run time."""
        if self.job:
            return self.job.next_run_time
        return None

    def get_status(self) -> dict:
        """Get current scheduler status."""
        return {
            'running': self.is_running,
            'last_run': self.last_run,
            'last_result': self.last_result,
            'next_run': self.get_next_run(),
        }
