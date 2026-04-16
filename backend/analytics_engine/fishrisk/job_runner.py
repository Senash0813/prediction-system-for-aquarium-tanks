import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

try:
    # Package import (used when loaded by FastAPI app)
    from .settings import SCHEDULER_INTERVAL_SECONDS
    from .mongo_client import (
        fetch_recent_readings,
        get_all_tank_ids,
        save_fish_risk_insight,
        close_connection,
    )
    from .insight_4_fish_risk import generate_insight
except ImportError:
    # Script import (used when file is run directly)
    from settings import SCHEDULER_INTERVAL_SECONDS
    from mongo_client import (
        fetch_recent_readings,
        get_all_tank_ids,
        save_fish_risk_insight,
        close_connection,
    )
    from insight_4_fish_risk import generate_insight


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_fish_risk_job() -> None:
    logger.info("=== Fish stress risk job started ===")

    try:
        tank_ids = get_all_tank_ids()
    except Exception as e:
        logger.error(f"Job failed — could not reach MongoDB: {e}")
        return

    if not tank_ids:
        logger.warning("No tank collections found.")
        return

    for tank_id in tank_ids:
        try:
            readings = fetch_recent_readings(tank_id)
            if not readings:
                logger.warning(f"[{tank_id}] No readings found.")
                continue

            insight = generate_insight(tank_id, readings)
            save_fish_risk_insight(tank_id, insight)

            message = insight.get("message")
            if message:
                logger.info(f"[{tank_id}] {message}")

        except Exception as e:
            logger.error(f"[{tank_id}] Failed: {e}", exc_info=True)


def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_fish_risk_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="fish_risk_job",
        name="Fish Stress Risk Rule-Based Insight",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    logger.info(f"Scheduler started — every {SCHEDULER_INTERVAL_SECONDS}s")

    try:
        run_fish_risk_job()
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        close_connection()
        logger.info("Scheduler stopped cleanly.")


def start_background_scheduler() -> BackgroundScheduler:
    """Starts a non-blocking BackgroundScheduler for use inside FastAPI."""

    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_fish_risk_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="fish_risk_job",
        name="Fish Stress Risk Rule-Based Insight",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    # Run once immediately so the first insight isn't delayed.
    run_fish_risk_job()
    scheduler.start()

    logger.info(f"Fish risk background scheduler started — every {SCHEDULER_INTERVAL_SECONDS}s")

    return scheduler