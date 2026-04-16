from datetime import datetime

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

try:
    # Package import (used when loaded by FastAPI app)
    from .settings import (
        MONGO_URI,
        MONGO_DB_NAME,
        INSIGHTS_DB_NAME,
        INSIGHTS_TTL_SECONDS,
        TREND_WINDOW_SIZE,
        get_tank_collection_name,
    )
except ImportError:
    # Script import (used when file is run directly)
    from settings import (
        MONGO_URI,
        MONGO_DB_NAME,
        INSIGHTS_DB_NAME,
        INSIGHTS_TTL_SECONDS,
        TREND_WINDOW_SIZE,
        get_tank_collection_name,
    )

_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client

def get_db():
    return get_client()[MONGO_DB_NAME]

def get_insights_db():
    return get_client()[INSIGHTS_DB_NAME]

def get_all_tank_ids():
    all_collections = get_db().list_collection_names()
    return [name for name in all_collections if name.startswith("tank_") and name != "tank_config"]

def fetch_recent_readings(tank_id: str, limit: int = TREND_WINDOW_SIZE):
    collection = get_db()[get_tank_collection_name(tank_id)]
    cursor = (
        collection
        .find({}, {
            "_id": 0,
            "temperature": 1,
            "ph": 1,
            "turbidity": 1,
            "tds": 1,
            "light": 1,
            "timestamp": 1
        })
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    readings = list(cursor)
    readings.reverse()
    return readings

def save_fish_risk_insight(tank_id: str, insight: dict):
    collection = get_insights_db()[tank_id]

    collection.create_index(
        [("generated_at", ASCENDING)],
        expireAfterSeconds=INSIGHTS_TTL_SECONDS,
        name="ttl_7_days"
    )

    generated_at = insight.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at)

    document = {
        "insight_type": "fish_stress_risk",
        "generated_at": generated_at,
        "tank_id": tank_id,
        "risk_score": insight.get("risk_score"),
        "risk_level": insight.get("risk_level"),
        "stress_trend": insight.get("stress_trend"),
        "causes": insight.get("causes"),
        "actions": insight.get("actions"),
        "message": insight.get("message"),
    }

    collection.insert_one(document)

def close_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None