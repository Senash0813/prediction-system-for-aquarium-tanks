# live_filter_health_rules.py

import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd


def _get_mongo_collection(collection_name: str = "tank_1"):
    """Get MongoDB collection using env vars for a specific tank collection."""

    this_dir = Path(__file__).resolve().parent
    backend_dir = this_dir.parent.parent
    load_dotenv(backend_dir / ".env", override=False)
    load_dotenv(this_dir / ".env", override=False)
    load_dotenv()

    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("MONGO_DB") or os.getenv("MONGODB_DB") or "aqua_gaurd_db"

    client = MongoClient(uri)
    coll = client[db_name][collection_name]
    return coll


def list_tank_collections(prefix: str = "tank_") -> list[str]:
    """List all MongoDB collections whose name starts with the given prefix.

    This assumes a per-tank collection naming convention like 'tank_1',
    'tank_2', etc., and treats the collection name as the tank identifier.
    """

    this_dir = Path(__file__).resolve().parent
    backend_dir = this_dir.parent.parent
    load_dotenv(backend_dir / ".env", override=False)
    load_dotenv(this_dir / ".env", override=False)
    load_dotenv()

    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("MONGO_DB") or os.getenv("MONGODB_DB") or "aqua_gaurd_db"

    client = MongoClient(uri)
    db = client[db_name]
    names = db.list_collection_names()
    return [name for name in names if name.startswith(prefix)]


def _flatten_timestamp(doc: Dict[str, Any]) -> None:
    """
    In-place conversion of MongoDB ISODate dicts into Python datetime.
    Expects field: timestamp: {"$date": "...Z"}
    """
    ts = doc.get("timestamp")
    if isinstance(ts, dict) and "$date" in ts:
        doc["timestamp"] = datetime.fromisoformat(ts["$date"].replace("Z", "+00:00"))


def _to_datetime_or_none(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None


def fetch_last_n_readings_from_mongo(
    n: int = 10,
    collection_name: str = "tank_1",
) -> pd.DataFrame:
    """
    Fetch the last n readings (by timestamp) from a given tank collection.

    Returns a pandas DataFrame sorted in chronological order.
    """
    coll = _get_mongo_collection(collection_name)

    cursor = coll.find(
        {},
        {
            "_id": 0,
            "tank_id": 1,
            "temperature": 1,
            "ph": 1,
            "turbidity": 1,
            "tds": 1,
            "light": 1,
            "timestamp": 1,
        },
    ).sort("timestamp", -1).limit(n)

    docs = list(cursor)
    if not docs:
        raise RuntimeError(f"No documents found in collection '{collection_name}'")

    # Flatten timestamps and ensure a tank_id exists
    for d in docs:
        _flatten_timestamp(d)
        d["timestamp"] = _to_datetime_or_none(d.get("timestamp"))
        if "tank_id" not in d or d["tank_id"] is None:
            d["tank_id"] = collection_name  # e.g. "tank_1"

    # Keep only rows usable by downstream trend logic.
    docs = [
        d for d in docs
        if d.get("timestamp") is not None and d.get("turbidity") is not None
    ]
    if not docs:
        raise RuntimeError(
            f"No valid readings with timestamp+turbidity in collection '{collection_name}'"
        )

    # We queried in descending order; reverse to chronological order
    docs.reverse()

    df = pd.DataFrame(docs)
    if "timestamp" not in df.columns:
        raise RuntimeError(f"Missing 'timestamp' column in collection '{collection_name}'")
    df = df.sort_values(["tank_id", "timestamp"]).reset_index(drop=True)
    return df


def compute_filter_health_for_window(df: pd.DataFrame) -> Tuple[str, pd.Series]:
    """
    Apply the same rule-based logic as in add_trend_features_and_labels
    on the provided window of readings (one tank), and return:

    - filter_health for the latest reading in this window
    - the full row (pandas Series) of that latest reading
    """
    if df.empty:
        raise ValueError("DataFrame is empty")
    required_cols = {"tank_id", "timestamp", "turbidity"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError("DataFrame is missing required columns for filter-health rules")

    # Apply local rule-based labeling logic (independent of training code)
    df_labeled = df.copy()

    # Compute per-tank turbidity deltas
    df_labeled["turbidity_delta"] = (
        df_labeled.groupby("tank_id")["turbidity"].diff()
    )
    df_labeled["turbidity_prev"] = (
        df_labeled.groupby("tank_id")["turbidity"].shift(1)
    )

    # Rule parameters – kept in sync with your intent for the
    # labeling logic in extract_and_label_turbidity.
    min_delta_for_increase = 0.05  # NTU
    long_trend_window = 10  # number of recent samples to look at
    min_increasing_count = 6  # how many of them must be increasing
    high_turbidity_threshold = 50.0  # NTU

    # Extremely high turbidity should never be treated as "OK",
    # even if the long-term trend is not strictly rising.
    very_high_turbidity_threshold = 100.0  # NTU
    sharp_drop_threshold = -5.0  # NTU drop considered "cleaning event"

    df_labeled["sharp_drop"] = (
        df_labeled["turbidity_delta"] <= sharp_drop_threshold
    )
    df_labeled["is_increasing"] = (
        df_labeled["turbidity_delta"] >= min_delta_for_increase
    )

    df_labeled["increasing_count_window"] = (
        df_labeled.groupby("tank_id")["is_increasing"]
        .rolling(window=long_trend_window, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )

    # Start with all readings as OK
    df_labeled["filter_health"] = "OK"

    # Warning: high turbidity + sustained upward trend over last 10 samples
    warning_mask = (
        (df_labeled["turbidity"] > high_turbidity_threshold)
        & (df_labeled["increasing_count_window"] >= min_increasing_count)
    )
    df_labeled.loc[warning_mask, "filter_health"] = "Warning"

    # Additionally, if turbidity is extremely high, treat it as at
    # least a Warning even if the long-term trend condition above
    # is not met. This avoids reporting obviously dirty water as OK.
    extreme_mask = (
        (df_labeled["turbidity"] >= very_high_turbidity_threshold)
        & (df_labeled["filter_health"] == "OK")
    )
    df_labeled.loc[extreme_mask, "filter_health"] = "Warning"

    # NeedsCleaning: sharp drop from already high turbidity.
    for tank_id, group in df_labeled.groupby("tank_id"):
        idx = group.index
        sharp_idxs = group.index[
            group["sharp_drop"]
            & (group["turbidity_prev"] > high_turbidity_threshold)
        ]

        for i in sharp_idxs:
            df_labeled.at[i, "filter_health"] = "NeedsCleaning"
            start = max(idx.min(), i - 5)
            df_labeled.loc[start:i, "filter_health"] = "NeedsCleaning"

    # Take the last (most recent) row as the current state
    last_row = df_labeled.iloc[-1]
    health = last_row["filter_health"]
    return str(health), last_row


def build_trend_message(health: str, last_row: pd.Series) -> str:
    """Generate a human-readable message about recent turbidity trend.

    Uses the same features computed in compute_filter_health_for_window.
    """

    turbidity = float(last_row.get("turbidity", float("nan")))
    inc_count = float(last_row.get("increasing_count_window", 0.0))
    delta = float(last_row.get("turbidity_delta", 0.0))

    long_trend_window = 10.0
    high_turbidity_threshold = 50.0
    very_high_turbidity_threshold = 100.0

    # Fraction of the last window where turbidity was increasing
    trend_fraction = inc_count / long_trend_window if long_trend_window > 0 else 0.0

    if health == "NeedsCleaning":
        return (
            "Recent sharp drop from very cloudy water – a cleaning or water "
            "change likely happened. Monitor if turbidity starts rising again."
        )

    if health == "Warning":
        # For extremely high turbidity, emphasise that the level itself
        # is unsafe, even if the long-term trend isn't strictly rising.
        if turbidity >= very_high_turbidity_threshold:
            return (
                "Turbidity is extremely high – water is much dirtier than "
                "the safe limit. Perform a water change and inspect the "
                "filter as soon as possible."
            )

        return (
            "Water is very cloudy (turbidity above 50) and has been rising "
            "for most of the last readings – filter performance is "
            "degrading, schedule a cleaning soon."
        )

    # health == "OK" cases
    if turbidity <= 10:
        return "Water is clear and stable – no cleaning needed now."

    if turbidity <= high_turbidity_threshold:
        if trend_fraction > 0.5:
            return (
                "Turbidity is in a moderate range and slowly rising, but still "
                "below the cloudy threshold – keep an eye on it."
            )
        return (
            "Turbidity is in a moderate range and not rising strongly – filter "
            "appears to be keeping up."
        )

    # turbidity > high_turbidity_threshold but not enough long-term rise
    # to trigger Warning.
    if delta > 0:
        return (
            "Water is very cloudy but the recent rise has not been long "
            "enough to trigger an alert – treat this as an early warning and "
            "consider checking the filter."
        )

    if delta < 0:
        return (
            "Water is very cloudy but turbidity is starting to decrease – "
            "conditions may be improving after cleaning or filter recovery."
        )

    return (
        "Water is very cloudy but the trend is flat – consider inspecting "
        "the filter if this persists."
    )


def get_filter_health_from_mongo_window(
    n: int = 10,
    collection_name: str = "tank_1",
) -> Dict[str, Any]:
    """
    High-level helper:

    1. Fetch last n readings from the given collection.
    2. Apply the same turbidity-based rule logic.
    3. Return a small dict with:
       - filter_health
       - latest turbidity
       - latest timestamp
       - (optionally) other sensor values for debugging.
    """
    df = fetch_last_n_readings_from_mongo(n=n, collection_name=collection_name)
    health, last_row = compute_filter_health_for_window(df)
    trend_msg = build_trend_message(health, last_row)

    result = {
        "collection": collection_name,
        "filter_health": health,
        "turbidity": float(last_row["turbidity"]),
        "timestamp": last_row["timestamp"],  # datetime object
        "window_size": len(df),
        "window_timestamps": df["timestamp"].tolist(),
        "window_turbidity": [float(x) for x in df["turbidity"].tolist()],
        "trend_message": trend_msg,
        # Expose basic trend features for downstream insight generation
        "turbidity_delta": float(last_row.get("turbidity_delta", 0.0))
        if pd.notna(last_row.get("turbidity_delta"))
        else None,
        "increasing_count_window": float(
            last_row.get("increasing_count_window", 0.0)
        ),
        "temperature": float(last_row.get("temperature", float("nan"))),
        "ph": float(last_row.get("ph", float("nan"))),
        "tds": float(last_row.get("tds", float("nan"))) if pd.notna(last_row.get("tds")) else None,
        # "light" can be numeric or a string like "Night Mode"; keep raw value
        "light": last_row.get("light"),
    }
    return result


def get_filter_health_for_all_tanks(
    n: int = 10,
    collection_prefix: str = "tank_",
) -> Dict[str, Dict[str, Any]]:
    """Compute rule-based filter health for all available tank collections.

    - Discovers all collections whose name starts with collection_prefix.
    - For each, fetches the last n readings and computes filter_health.
    - Returns a mapping: tank_id (collection name) -> result dict.
    """

    results: Dict[str, Dict[str, Any]] = {}
    for coll_name in list_tank_collections(prefix=collection_prefix):
        try:
            results[coll_name] = get_filter_health_from_mongo_window(
                n=n, collection_name=coll_name
            )
        except (RuntimeError, ValueError, KeyError, TypeError):
            # Skip tanks with missing or invalid data shape.
            continue
    return results


if __name__ == "__main__":
    all_results = get_filter_health_for_all_tanks(n=10, collection_prefix="tank_")
    for tank_id, info in all_results.items():
        print(f"Tank {tank_id} -> filter health: {info['filter_health']}, window_size: {info['window_size']}")
        print("  Latest turbidity:", info["turbidity"], "at", info["timestamp"])
        trend_msg = info.get("trend_message")
        if trend_msg:
            print("  Trend:", trend_msg)