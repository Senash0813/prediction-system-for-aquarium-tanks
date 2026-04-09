# scheduler/job_runner.py

import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from settings import SCHEDULER_INTERVAL_SECONDS
from mongo_client import fetch_recent_readings, get_all_tank_ids, close_connection, save_temperature_insight
from insight_1_temperature import generate_insight

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core job — runs on every scheduler tick
# ---------------------------------------------------------------------------

def run_temperature_insight_job():
    """
    Scheduled job that:
    1. Discovers all active tanks in MongoDB
    2. Fetches recent readings for each tank
    3. Runs Insight 1 (temperature stability & heater failure prediction)
    4. Saves the insight to generated_insights.<tank_id> and logs the result
    """
    logger.info("=== Temperature insight job started ===")
    IST = timezone(timedelta(hours=5, minutes=30))
    run_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")

    try:
        tank_ids = get_all_tank_ids()

        if not tank_ids:
            logger.warning("No tank collections found in database. Skipping job.")
            return

        logger.info(f"Found {len(tank_ids)} tank(s): {tank_ids}")

        for tank_id in tank_ids:
            _process_tank(tank_id)

    except RuntimeError as e:
        logger.error(f"Job failed — could not reach MongoDB: {e}")

    logger.info(f"=== Job complete at {run_time} ===\n")


def _process_tank(tank_id: str):
    """
    Runs the full insight pipeline for a single tank, saves the result to
    MongoDB, and logs it. Isolated so one tank's failure doesn't stop others.
    """
    try:
        logger.info(f"[{tank_id}] Fetching readings...")
        readings = fetch_recent_readings(tank_id)

        if not readings:
            logger.warning(f"[{tank_id}] No readings found. Skipping.")
            return

        logger.info(f"[{tank_id}] Running temperature insight on {len(readings)} reading(s)...")
        insight = generate_insight(tank_id, readings)

        save_temperature_insight(tank_id, insight)
        _log_insight(tank_id, insight)

        # ----------------------------------------------------------------
        # TODO (next steps):
        #   - Push alert/warning to frontend via WebSocket or REST API
        # ----------------------------------------------------------------

    except RuntimeError as e:
        logger.error(f"[{tank_id}] Failed to process: {e}")
    except Exception as e:
        logger.error(f"[{tank_id}] Unexpected error: {e}", exc_info=True)


def _log_insight(tank_id: str, insight: dict):
    """Logs the insight result at the appropriate log level."""
    status = insight.get("status")
    message = insight.get("message")

    if status == "alert":
        logger.error(f"[{tank_id}] {message}")
    elif status == "warning":
        logger.warning(f"[{tank_id}] {message}")
    elif status == "normal":
        logger.info(f"[{tank_id}] {message}")
    elif status == "insufficient_data":
        logger.info(f"[{tank_id}] {message}")
    else:
        logger.debug(f"[{tank_id}] Unknown status — raw insight: {insight}")


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

def start_scheduler():
    """
    Initialises and starts the APScheduler blocking scheduler.
    Runs run_temperature_insight_job() every SCHEDULER_INTERVAL_SECONDS.
    Shuts down cleanly on KeyboardInterrupt (Ctrl+C).
    """
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_temperature_insight_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="temperature_insight_job",
        name="Temperature Stability & Heater Failure Prediction",
        replace_existing=True,
        max_instances=1,         # Prevents overlap if a job run takes too long
        misfire_grace_time=60,   # Allows up to 60s delay before treating as missed
    )

    logger.info(
        f"Scheduler started — running every {SCHEDULER_INTERVAL_SECONDS}s "
        f"({SCHEDULER_INTERVAL_SECONDS // 60} min)"
    )
    logger.info("Press Ctrl+C to stop.\n")

    try:
        # Run once immediately on startup so you don't wait 3 minutes for first result
        run_temperature_insight_job()
        scheduler.start()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        close_connection()
        logger.info("Scheduler and MongoDB connection closed cleanly.")