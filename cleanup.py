"""
Cleanup: Deletes old DB entries (leads, email_log) past retention time.
Runs as background task in FastAPI or standalone via: python cleanup.py
"""

import asyncio
import logging
from database import init_db, get_db
from config import Config

logger = logging.getLogger(__name__)


def cleanup_old_entries():
    """Delete DB entries older than DATA_RETENTION_TIME."""
    db = get_db()

    deleted_leads = db.execute(
        "DELETE FROM leads WHERE phone IN (SELECT phone FROM email_log WHERE deletion_requested = 1)"
    ).rowcount

    deleted_logs = db.execute(
        "DELETE FROM email_log WHERE deletion_requested = 1 AND deletion_requested_at < datetime('now', ?)",
        (f"-{Config.DATA_RETENTION_SECONDS} seconds",)
    ).rowcount

    db.commit()

    if deleted_leads or deleted_logs:
        logger.info(f"Cleanup: {deleted_leads} leads, {deleted_logs} email_log entries deleted.")


async def run_scheduler():
    """Background scheduler: startup check + periodic cleanup."""
    interval = Config.CLEANUP_INTERVAL_SECONDS
    logger.info(f"Cleanup-Scheduler started (interval: {interval}s)")

    cleanup_old_entries()

    while True:
        await asyncio.sleep(interval)
        try:
            cleanup_old_entries()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    cleanup_old_entries()
