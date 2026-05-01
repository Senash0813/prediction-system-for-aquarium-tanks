import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

try:
    # Package imports (used when loaded by FastAPI app).
    from .insight_4_fish_risk import generate_insight
    from .mongo_client import (
        close_connection,
        fetch_recent_readings,
        get_all_tank_ids,
        save_fish_risk_insight,
    )
    from .settings import SCHEDULER_INTERVAL_SECONDS
except ImportError:
    # Script imports (used when run directly).
    from insight_4_fish_risk import generate_insight
    from mongo_client import (
        close_connection,
        fetch_recent_readings,
        get_all_tank_ids,
        save_fish_risk_insight,
    )
    from settings import SCHEDULER_INTERVAL_SECONDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_fish_risk_job():
    logger.info("=== Fish stress risk job started ===")

    tank_ids = get_all_tank_ids()
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
            logger.info(f"[{tank_id}] {insight['message']}")

        except Exception as e:
            logger.error(f"[{tank_id}] Failed: {e}", exc_info=True)


def start_scheduler():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        func=run_fish_risk_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="fish_risk_job",
        name="Fish Stress Risk Combined Insight",
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
    """Start a non-blocking scheduler for use inside FastAPI.

    Runs run_fish_risk_job() once immediately, then on an interval in a
    background thread.

    Returns the scheduler instance so FastAPI can shut it down cleanly.
    """

    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_fish_risk_job,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="fish_risk_job",
        name="Fish Stress Risk Combined Insight",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    # Run once immediately so the first insight isn't delayed.
    run_fish_risk_job()
    scheduler.start()

    logger.info(
        f"Fish risk background scheduler started — running every {SCHEDULER_INTERVAL_SECONDS}s "
        f"({SCHEDULER_INTERVAL_SECONDS // 60} min)"
    )

    return scheduler