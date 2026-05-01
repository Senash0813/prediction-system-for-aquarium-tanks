import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .settings import SCHEDULER_INTERVAL_SECONDS
from .mongo_client import (
    fetch_recent_readings,
    fetch_tank_config,
    get_all_tank_ids,
    close_connection,
    save_water_chemistry_insight,
)
from .insight_2_water_chemistry import generate_insight

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_water_chemistry_insight_job():
    logger.info("=== Water chemistry insight job started ===")
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
    try:
        logger.info(f"[{tank_id}] Fetching readings...")
        readings = fetch_recent_readings(tank_id)

        if not readings:
            logger.warning(f"[{tank_id}] No readings found. Skipping.")
            return

        tank_config = fetch_tank_config(tank_id)

        logger.info(f"[{tank_id}] Running hybrid water chemistry insight on {len(readings)} reading(s)...")
        insight = generate_insight(tank_id, readings, tank_config)

        save_water_chemistry_insight(tank_id, insight)
        _log_insight(tank_id, insight)

    except RuntimeError as e:
        logger.error(f"[{tank_id}] Failed to process: {e}")
    except Exception as e:
        logger.error(f"[{tank_id}] Unexpected error: {e}", exc_info=True)


def _log_insight(tank_id: str, insight: dict):
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


def start_scheduler():
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_water_chemistry_insight_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="water_chemistry_insight_job",
        name="Hybrid Water Chemistry Insight Generation",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    logger.info(
        f"Scheduler started — running every {SCHEDULER_INTERVAL_SECONDS}s "
        f"({SCHEDULER_INTERVAL_SECONDS // 60} min)"
    )
    logger.info("Press Ctrl+C to stop.\n")

    try:
        run_water_chemistry_insight_job()
        scheduler.start()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        close_connection()
        logger.info("Scheduler and MongoDB connection closed cleanly.")


def start_background_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_water_chemistry_insight_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="water_chemistry_insight_job",
        name="Hybrid Water Chemistry Insight Generation",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    run_water_chemistry_insight_job()
    scheduler.start()

    logger.info(
        f"Water chemistry background scheduler started — running every {SCHEDULER_INTERVAL_SECONDS}s "
        f"({SCHEDULER_INTERVAL_SECONDS // 60} min)"
    )

    return scheduler