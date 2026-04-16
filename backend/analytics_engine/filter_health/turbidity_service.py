import os
import copy
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

try:
    from .rule_filterhealth import get_filter_health_from_mongo_window
except ImportError:
    from rule_filterhealth import get_filter_health_from_mongo_window


_ANALYSIS_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def _cache_ttl_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("TURBIDITY_CACHE_TTL_SECONDS", "180")))
    except ValueError:
        return 180.0


def _get_cached_analysis(cache_key: tuple[str, str]) -> dict[str, Any] | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _ANALYSIS_CACHE.get(cache_key)
        if not cached:
            return None

        expires_at, payload = cached
        if now >= expires_at:
            _ANALYSIS_CACHE.pop(cache_key, None)
            return None

        return copy.deepcopy(payload)


def _store_cached_analysis(cache_key: tuple[str, str], payload: dict[str, Any]) -> None:
    expires_at = time.monotonic() + _cache_ttl_seconds()
    with _CACHE_LOCK:
        _ANALYSIS_CACHE[cache_key] = (expires_at, copy.deepcopy(payload))


def invalidate_turbidity_cache(collection_name: str | None = None) -> None:
    """Clear cached turbidity analysis results.

    If collection_name is provided, only entries for that collection are removed.
    """

    with _CACHE_LOCK:
        if collection_name is None:
            _ANALYSIS_CACHE.clear()
            return

        keys_to_remove = [key for key in _ANALYSIS_CACHE if key[0] == collection_name]
        for key in keys_to_remove:
            _ANALYSIS_CACHE.pop(key, None)


def _get_collection(collection_name: str):
    # Ensure env vars are available regardless of process working directory.
    this_dir = Path(__file__).resolve().parent
    backend_dir = this_dir.parent.parent
    load_dotenv(backend_dir / ".env", override=False)
    load_dotenv(this_dir / ".env", override=False)
    load_dotenv(override=False)

    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "aqua_gaurd_db")

    client = MongoClient(uri)
    return client[db_name][collection_name]


def _window_delta(range_type: str) -> timedelta:
    if range_type == "24h":
        return timedelta(hours=24)
    if range_type == "7d":
        return timedelta(days=7)
    if range_type == "30d":
        return timedelta(days=30)
    raise ValueError("range_type must be one of: 24h, 7d, 30d")


def _normalize_timestamp(ts: Any) -> datetime | None:
    if ts is None:
        return None

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    if isinstance(ts, str):
        normalized = ts.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    if isinstance(ts, dict) and "$date" in ts:
        return _normalize_timestamp(ts["$date"])

    return None


def _to_iso_utc(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _label_for_range(ts: datetime, range_type: str) -> str:
    if range_type == "24h":
        return ts.strftime("%H:%M")
    if range_type == "7d":
        return ts.strftime("%b %d %H:%M")
    return ts.strftime("%b %d")


def _classify_trend(rate_of_change: float, stable_threshold: float = 0.001) -> str:
    if rate_of_change > stable_threshold:
        return "Rising"
    if rate_of_change < -stable_threshold:
        return "Falling"
    return "Stable"


def _trend_from_filter_health(info: dict[str, Any]) -> str:
    delta = info.get("turbidity_delta")
    if delta is None:
        return "Unknown"

    try:
        delta_value = float(delta)
    except (TypeError, ValueError):
        return "Unknown"

    if delta_value > 0.05:
        return "Rising"
    if delta_value < -0.05:
        return "Falling"
    return "Stable"


def get_turbidity_analysis(collection_name: str, range_type: str = "24h") -> dict:
    cache_key = (collection_name, range_type)
    cached = _get_cached_analysis(cache_key)
    if cached is not None:
        return cached

    coll = _get_collection(collection_name)

    try:
        filter_health = get_filter_health_from_mongo_window(n=10, collection_name=collection_name)
    except Exception:
        filter_health = None

    latest_doc = coll.find_one({}, {"timestamp": 1}, sort=[("timestamp", -1)])
    if not latest_doc:
        result = {
            "metric": "turbidity",
            "range": range_type,
            "message": "No data available.",
            "filter_health": None,
            "chart_points": [],
            "current": None,
            "average": None,
            "min": None,
            "max": None,
            "trend": "Unknown",
            "rate_of_change": None,
        }
        _store_cached_analysis(cache_key, result)
        return copy.deepcopy(result)

    latest_ts = _normalize_timestamp(latest_doc.get("timestamp"))
    if latest_ts is None:
        result = {
            "metric": "turbidity",
            "range": range_type,
            "message": "Latest timestamp is invalid.",
            "filter_health": None,
            "chart_points": [],
            "current": None,
            "average": None,
            "min": None,
            "max": None,
            "trend": "Unknown",
            "rate_of_change": None,
        }
        _store_cached_analysis(cache_key, result)
        return copy.deepcopy(result)

    cutoff = latest_ts - _window_delta(range_type)

    cursor = coll.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0, "timestamp": 1, "turbidity": 1},
    ).sort("timestamp", 1)

    points: list[dict[str, Any]] = []
    values: list[float] = []
    for doc in cursor:
        ts = _normalize_timestamp(doc.get("timestamp"))
        if ts is None:
            continue

        try:
            turbidity_value = float(doc.get("turbidity"))
        except (TypeError, ValueError):
            continue

        values.append(turbidity_value)
        points.append(
            {
                "timestamp_iso": _to_iso_utc(ts),
                "label": _label_for_range(ts, range_type),
                "turbidity": round(turbidity_value, 2),
            }
        )

    if not values:
        result = {
            "metric": "turbidity",
            "range": range_type,
            "message": "No valid turbidity data in selected range.",
            "filter_health": None,
            "chart_points": [],
            "current": None,
            "average": None,
            "min": None,
            "max": None,
            "trend": "Unknown",
            "rate_of_change": None,
        }
        _store_cached_analysis(cache_key, result)
        return copy.deepcopy(result)

    steps = len(values) - 1
    rate_of_change = 0.0 if steps <= 0 else (values[-1] - values[0]) / steps
    trend = _trend_from_filter_health(filter_health) if filter_health else _classify_trend(rate_of_change)

    current = round(values[-1], 2)
    average = round(sum(values) / len(values), 2)
    min_value = round(min(values), 2)
    max_value = round(max(values), 2)

    result = {
        "metric": "turbidity",
        "range": range_type,
        "current": current,
        "average": average,
        "min": min_value,
        "max": max_value,
        "trend": trend,
        "filter_health": filter_health.get("filter_health") if filter_health else None,
        "rate_of_change": round(rate_of_change, 4),
        "message": (
            filter_health.get("trend_message")
            if filter_health and filter_health.get("trend_message")
            else f"Turbidity is currently {current}, with a {trend.lower()} trend over the selected period."
        ),
        "chart_points": points,
    }

    _store_cached_analysis(cache_key, result)
    return copy.deepcopy(result)
