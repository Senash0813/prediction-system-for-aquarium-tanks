import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from settings import SCHEDULER_INTERVAL_SECONDS
from mongo_client import (
    fetch_recent_readings,
    get_all_tank_ids,
    save_fish_risk_insight,
    close_connection,
)
from insight_4_fish_risk import generate_insight

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