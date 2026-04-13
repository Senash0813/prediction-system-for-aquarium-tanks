import os
import time
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

from dotenv import load_dotenv
from pymongo import MongoClient

try:
    # Package import (used when loaded by FastAPI app).
    from .rule_filterhealth import get_filter_health_for_all_tanks
except ImportError:
    # Script import (used when file is run directly).
    from rule_filterhealth import get_filter_health_for_all_tanks


_insights_thread_lock = threading.Lock()
_insights_thread_started = False


def _get_insights_db():
    """Return a handle to the generated_insights database.

    Uses the same MONGO_URI as the main aquarium DB, but a separate
    database name so we don't mix raw sensor readings with insights.
    """

    this_dir = Path(__file__).resolve().parent
    backend_dir = this_dir.parent.parent
    load_dotenv(backend_dir / ".env", override=False)
    load_dotenv(this_dir / ".env", override=False)
    load_dotenv()

    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
    insights_db_name = os.getenv("MONGO_INSIGHTS_DB", "generated_insights")

    client = MongoClient(uri)
    return client[insights_db_name]


def _trend_direction_from_delta(turbidity_delta: Any) -> str:
    try:
        delta_value = float(turbidity_delta)
    except (TypeError, ValueError):
        return "unknown"

    if delta_value > 0.1:
        return "rising"
    if delta_value < -0.1:
        return "falling"
    return "stable"


def _filter_health_message(health: str, trend_msg: Any) -> str:
    if health == "OK":
        return f"Filter appears OK. {trend_msg}" if trend_msg else "Filter appears OK."

    if health == "Warning":
        return f"Filter warning: {trend_msg}" if trend_msg else "Filter warning: check the filter soon."

    return (
        f"Filter likely needs cleaning: {trend_msg}"
        if trend_msg
        else "Filter likely needs cleaning based on turbidity pattern."
    )


def _build_filter_health_insight(tank_id: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single insight document for a tank's filter health.

    The shape is similar in spirit to your temperature_stability insight,
    but focused on turbidity and filter state.
    """

    now = datetime.now(timezone.utc)

    health = info.get("filter_health", "OK")
    status_map = {
        "OK": "normal",
        "Warning": "warning",
        "NeedsCleaning": "needs_cleaning",
    }
    status = status_map.get(health, "unknown")

    turbidity_delta = info.get("turbidity_delta")
    inc_count = float(info.get("increasing_count_window", 0.0) or 0.0)
    window_size = int(info.get("window_size", 0))
    window_turbidity = info.get("window_turbidity") or []

    trend_direction = _trend_direction_from_delta(turbidity_delta)

    # Fraction of recent readings that were increasing (0..1 range).
    long_trend_window = 10.0
    increasing_fraction = inc_count / long_trend_window if long_trend_window > 0 else 0.0

    trend_msg = info.get("trend_message")

    # Compute simple statistics for the turbidity window.
    if window_turbidity:
        try:
            avg_turbidity = sum(window_turbidity) / len(window_turbidity)
        except TypeError:
            avg_turbidity = None
    else:
        avg_turbidity = None

    message = _filter_health_message(health, trend_msg)

    insight: Dict[str, Any] = {
        "insight_type": "filter_health",
        "generated_at": now,
        "status": status,
        "message": message,
        "trend": {
            "trend_direction": trend_direction,
            "turbidity_delta_last": turbidity_delta,
            "increasing_fraction": increasing_fraction,
            "window_size": window_size,
        },
        "turbidity_window": {
            "values": window_turbidity,
            "average": avg_turbidity,
        },
        "source": {
            "tank_collection": info.get("collection", tank_id),
            "rule_version": "v1",
        },
    }

    return insight


def generate_filter_health_insights() -> None:
    """Generate filter-health insights for all tanks and write to MongoDB.

    This runs once: it reads the latest window for each tank_*
    collection from the main DB, computes rule-based filter health,
    then writes one insight document per tank into the corresponding
    collection within the generated_insights database.
    """

    insights_db = _get_insights_db()

    # This call reads from the main aquarium DB using the existing
    # environment variables (MONGO_URI, MONGO_DB) and your tank_*
    # collections.
    all_tanks_info = get_filter_health_for_all_tanks(n=10, collection_prefix="tank_")

    for tank_id, info in all_tanks_info.items():
        insight_doc = _build_filter_health_insight(tank_id, info)

        # In the generated_insights DB we also keep collections per tank
        # (tank_1, tank_2, ...), matching your example layout.
        coll = insights_db[tank_id]
        coll.insert_one(insight_doc)


def start_periodic_filter_health_insights(interval_minutes: float = 30.0) -> None:
    """Start a daemon thread that generates insights periodically.

    The worker starts immediately and then repeats every interval_minutes.
    Calling this function multiple times in the same process is safe.
    """

    global _insights_thread_started

    with _insights_thread_lock:
        if _insights_thread_started:
            return
        _insights_thread_started = True

    interval_seconds = max(1.0, float(interval_minutes) * 60.0)

    def _worker() -> None:
        while True:
            try:
                generate_filter_health_insights()
            except Exception as exc:
                # Keep scheduler alive even if one run fails.
                print(f"[filter_health] insight generation failed: {exc}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_worker, name="filter-health-insights", daemon=True)
    thread.start()


def main() -> None:
    """Entry point for both manual and periodic insight generation.

    - Manual (one-off): simply run `python generate_filter_insights.py`
    - Automated: run with the environment variable INSIGHT_INTERVAL_MINUTES
      set to a positive number, or pass an interval via command line.
    """

    import argparse

    parser = argparse.ArgumentParser(description="Generate filter-health insights per tank.")
    parser.add_argument(
        "--interval-minutes",
        type=float,
        default=None,
        help=(
            "If provided, run in a loop and generate insights every this many "
            "minutes. If omitted, run only once (manual mode)."
        ),
    )

    args = parser.parse_args()

    if args.interval_minutes is None:
        # Manual, single run.
        generate_filter_health_insights()
        return

    # Periodic / automated mode.
    interval_seconds = max(1.0, args.interval_minutes * 60.0)
    while True:
        generate_filter_health_insights()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
