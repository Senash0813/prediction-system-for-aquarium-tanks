# db/mongo_client.py

from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from .settings import MONGO_URI, MONGO_DB_NAME, INSIGHTS_DB_NAME, INSIGHTS_TTL_SECONDS, get_tank_collection_name, TREND_WINDOW_SIZE, TEMPERATURE_SAFE_MIN, TEMPERATURE_SAFE_MAX


_client = None  # Module-level singleton — one connection reused across all calls


def get_client() -> MongoClient:
    """Returns the shared MongoClient, creating it once if needed."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Returns the aquarium database handle."""
    return get_client()[MONGO_DB_NAME]


def fetch_recent_readings(tank_id: str, limit: int = TREND_WINDOW_SIZE) -> list[dict]:
    """
    Fetches the most recent `limit` cleaned readings for a given tank,
    ordered oldest → newest (ready for trend analysis).

    Args:
        tank_id : e.g. 'tank_1'
        limit   : number of readings to fetch (default: TREND_WINDOW_SIZE)

    Returns:
        List of reading dicts, oldest first. Empty list if none found.

    Raises:
        RuntimeError on connection or query failure.
    """
    try:
        collection = get_db()[get_tank_collection_name(tank_id)]

        # Fetch newest N first, then reverse so trend math goes oldest → newest
        cursor = (
            collection
            .find({}, {"_id": 0, "temperature": 1, "light": 1, "timestamp": 1})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        readings = list(cursor)
        readings.reverse()
        return readings

    except ConnectionFailure as e:
        raise RuntimeError(f"[mongo_client] Could not connect to MongoDB: {e}")
    except OperationFailure as e:
        raise RuntimeError(f"[mongo_client] Query failed for {tank_id}: {e}")


def fetch_tank_config(tank_id: str) -> dict:
    """
    Fetches the safe temperature range for a given tank from tank_config.

    Returns a dict with:
        - safe_min : minimum safe temperature (°C)
        - safe_max : maximum safe temperature (°C)

    Falls back to settings defaults if no config document is found for the tank.
    """
    try:
        collection = get_db()["tank_config"]
        config = collection.find_one({"tank_id": tank_id}, {"_id": 0, "safe_ranges.temperature": 1})

        if config:
            temp_range = config.get("safe_ranges", {}).get("temperature", {})
            safe_min = temp_range.get("min", TEMPERATURE_SAFE_MIN)
            safe_max = temp_range.get("max", TEMPERATURE_SAFE_MAX)
        else:
            safe_min = TEMPERATURE_SAFE_MIN
            safe_max = TEMPERATURE_SAFE_MAX

        return {"safe_min": float(safe_min), "safe_max": float(safe_max)}

    except ConnectionFailure as e:
        raise RuntimeError(f"[mongo_client] Could not connect to MongoDB: {e}")
    except OperationFailure as e:
        raise RuntimeError(f"[mongo_client] Failed to fetch tank config for {tank_id}: {e}")


def get_all_tank_ids() -> list[str]:
    """
    Returns all tank collection names in the database.
    Used by the scheduler to run insights across every tank automatically.
    """
    try:
        all_collections = get_db().list_collection_names()
        # Filter to only tank collections (in case other collections exist)
        return [name for name in all_collections if name.startswith("tank_") and name != "tank_config"]
    except Exception as e:
        raise RuntimeError(f"[mongo_client] Could not list collections: {e}")


def get_insights_db():
    """Returns the generated_insights database handle."""
    return get_client()[INSIGHTS_DB_NAME]


def save_temperature_insight(tank_id: str, insight: dict) -> None:
    """
    Saves a temperature insight to generated_insights.<tank_id>.
    Creates the collection and TTL index automatically on first use.

    Args:
        tank_id : e.g. 'tank_1'
        insight : dict returned by generate_insight()

    Raises:
        RuntimeError on connection or write failure.
    """
    try:
        collection = get_insights_db()[tank_id]

        # Create TTL index if it doesn't already exist (idempotent)
        collection.create_index(
            [("generated_at", ASCENDING)],
            expireAfterSeconds=INSIGHTS_TTL_SECONDS,
            name="ttl_7_days",
        )

        # generated_at arrives as an ISO string — convert to datetime so TTL works
        generated_at = insight.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        document = {
            "insight_type": "temperature_stability",
            "generated_at": generated_at,
            "status": insight.get("status"),
            "message": insight.get("message"),
            "trend": insight.get("trend"),
            "prediction": insight.get("prediction"),
            "light": insight.get("light"),
        }

        collection.insert_one(document)

    except ConnectionFailure as e:
        raise RuntimeError(f"[mongo_client] Could not connect to MongoDB: {e}")
    except OperationFailure as e:
        raise RuntimeError(f"[mongo_client] Failed to save insight for {tank_id}: {e}")


def close_connection():
    """Cleanly closes the MongoDB connection. Call on scheduler shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None