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
    from .rule_filterhealth import fetch_last_n_readings_from_mongo, get_filter_health_for_all_tanks
    from .train_filter_health_model import MODEL_PATH, predict_filter_health_from_history
except ImportError:
    # Script import (used when file is run directly).
    from rule_filterhealth import fetch_last_n_readings_from_mongo, get_filter_health_for_all_tanks
    from train_filter_health_model import MODEL_PATH, predict_filter_health_from_history


_insights_thread_lock = threading.Lock()
_insights_thread_started = False
_client = None


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

    global _client

    if _client is None:
        _client = MongoClient(uri)

    return _client[insights_db_name]


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


def _current_situation_sentence(health: str) -> str:
    if health == "OK":
        return "Water is clear and stable."
    if health == "Warning":
        return "Water is starting to cloud up."
    if health == "NeedsCleaning":
        return "Water is very cloudy and the filter likely needs cleaning."
    return "Water quality needs attention."


def _prediction_sentence(health: str, prediction: str) -> str:
    if prediction == "NeedsCleaningSoon":
        if health == "OK":
            return "Water is stable now, but early signs suggest cleaning may be needed soon."
        if health == "Warning":
            return "Cleaning should be scheduled soon."
        return "Cleaning is recommended soon."

    if prediction == "OK":
        if health == "NeedsCleaning":
            return "The filter still needs attention, so monitor it closely."
        if health == "Warning":
            return "No immediate cleaning is needed, but keep monitoring the trend."
        return "No cleaning is needed right now."

    return "Keep monitoring for changes in turbidity."


def _build_hybrid_message(health: str, prediction: str) -> str:
    return f"{_current_situation_sentence(health)} {_prediction_sentence(health, prediction)}"


def _predict_filter_health_for_tank(tank_id: str, n: int = 10) -> str:
    try:
        df = fetch_last_n_readings_from_mongo(n=n, collection_name=tank_id)
        history_docs = df.to_dict(orient="records")
        predictions = predict_filter_health_from_history(history_docs, model_path=MODEL_PATH)
        return predictions.get(tank_id, "Unknown")
    except Exception:
        return "Unknown"


def _build_filter_health_insight(tank_id: str, info: Dict[str, Any], prediction: str) -> Dict[str, Any]:
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

    # Compute simple statistics for the turbidity window.
    if window_turbidity:
        try:
            avg_turbidity = sum(window_turbidity) / len(window_turbidity)
        except TypeError:
            avg_turbidity = None
    else:
        avg_turbidity = None

    message = _build_hybrid_message(health, prediction)

    insight: Dict[str, Any] = {
        "insight_type": "filter_health",
        "generated_at": now,
        "status": status,
        "message": message,
        "prediction": prediction,
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


def generate_filter_health_insights() -> Dict[str, Any]:
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

    inserted_count = 0
    inserted_tanks: list[str] = []

    for tank_id, info in all_tanks_info.items():
        prediction = _predict_filter_health_for_tank(tank_id, n=10)
        insight_doc = _build_filter_health_insight(tank_id, info, prediction)

        # In the generated_insights DB we also keep collections per tank
        # (tank_1, tank_2, ...), matching your example layout.
        coll = insights_db[tank_id]
        coll.insert_one(insight_doc)
        inserted_count += 1
        inserted_tanks.append(tank_id)

    return {
        "inserted_count": inserted_count,
        "tanks": inserted_tanks,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


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
                summary = generate_filter_health_insights()
                print(
                    "[filter_health] insights pushed: "
                    f"count={summary['inserted_count']} "
                    f"tanks={summary['tanks']} "
                    f"at={summary['generated_at']}"
                )
            except Exception as exc:
                # Keep scheduler alive even if one run fails.
                print(f"[filter_health] insight generation failed: {exc}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_worker, name="filter-health-insights", daemon=True)
    thread.start()
    print(
        "[filter_health] insight generation has started "
        f"(interval={interval_minutes} min, thread={thread.name})"
    )


def close_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


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
