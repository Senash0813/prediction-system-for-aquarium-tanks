from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

from .settings import (
    MONGO_URI,
    MONGO_DB_NAME,
    INSIGHTS_DB_NAME,
    INSIGHTS_TTL_SECONDS,
    get_tank_collection_name,
    TREND_WINDOW_SIZE,
)

_client = None


def get_client() -> MongoClient:
    """Returns the shared MongoClient, creating it once if needed."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Returns the main aquarium readings database handle."""
    return get_client()[MONGO_DB_NAME]


def get_insights_db():
    """Returns the generated insights database handle."""
    return get_client()[INSIGHTS_DB_NAME]


def fetch_recent_readings(tank_id: str, limit: int = TREND_WINDOW_SIZE) -> list[dict]:
    """
    Fetches the most recent readings for a tank, ordered oldest -> newest.

    Only required fields are fetched:
    - tank_id
    - ph
    - tds
    - temperature
    - timestamp
    """
    try:
        collection = get_db()[get_tank_collection_name(tank_id)]

        cursor = (
            collection
            .find(
                {},
                {
                    "_id": 0,
                    "tank_id": 1,
                    "ph": 1,
                    "tds": 1,
                    "temperature": 1,
                    "timestamp": 1,
                }
            )
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


def get_all_tank_ids() -> list[str]:
    """
    Returns all tank collections from the cleaned readings database.
    """
    try:
        all_collections = get_db().list_collection_names()
        return [name for name in all_collections if name.startswith("tank_") and name != "tank_config"]
    except Exception as e:
        raise RuntimeError(f"[mongo_client] Could not list collections: {e}")


def save_water_chemistry_insight(tank_id: str, insight: dict) -> None:
    """
    Saves a generated water chemistry insight to generated_insights.<tank_id>
    """
    try:
        collection = get_insights_db()[tank_id]

        collection.create_index(
            [("generated_at", ASCENDING)],
            expireAfterSeconds=INSIGHTS_TTL_SECONDS,
            name="ttl_7_days",
        )

        generated_at = insight.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        document = {
            "insight_type": "water_chemistry",
            "generated_at": generated_at,
            "status": insight.get("status"),
            "message": insight.get("message"),
            "overall": insight.get("overall"),
            "ph": insight.get("ph"),
            "tds": insight.get("tds"),
            "temperature": insight.get("temperature"),
            "diagnosis": insight.get("diagnosis"),
            "recommendation": insight.get("recommendation"),
        }

        collection.insert_one(document)

    except ConnectionFailure as e:
        raise RuntimeError(f"[mongo_client] Could not connect to MongoDB: {e}")
    except OperationFailure as e:
        raise RuntimeError(f"[mongo_client] Failed to save insight for {tank_id}: {e}")


def close_connection():
    """Closes MongoDB connection cleanly."""
    global _client
    if _client is not None:
        _client.close()
        _client = None