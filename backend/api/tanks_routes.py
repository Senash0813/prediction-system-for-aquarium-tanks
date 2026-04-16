from fastapi import APIRouter, HTTPException
from fastapi import Query
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pymongo import DESCENDING
from analytics_engine.water_chemistry_analytics.settings import INSIGHTS_DB_NAME
from datetime import datetime, timedelta, timezone

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "aqua_gaurd_db"

router = APIRouter(prefix="/api", tags=["Tanks"])


@router.get("/tanks")
def list_tanks():
    """Return collection names in the database that start with 'tank_'.

    The config collection (tank_config) is excluded.
    """
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        collections = db.list_collection_names()
        tanks = [name for name in collections if name.startswith("tank_") and name != "tank_config"]
        return {"tanks": tanks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/latest")
def get_latest_reading(collection: str):
    """Return the most recent document from the requested tank collection.

    Only collections with names like 'tank_<number>' are allowed.
    """
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]

        if collection not in db.list_collection_names():
            raise HTTPException(status_code=404, detail="Collection not found")

        doc = db[collection].find_one({}, {"_id": 0}, sort=[("timestamp", DESCENDING)])
        if not doc:
            raise HTTPException(status_code=404, detail="No readings in collection")

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/latest-insight")
def get_latest_insight(collection: str):
    """Return the most recent generated insight document for a tank from the insights DB."""
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        insights_db = client[INSIGHTS_DB_NAME]

        if collection not in insights_db.list_collection_names():
            raise HTTPException(status_code=404, detail="Insights collection not found")

        doc = insights_db[collection].find_one({}, {"_id": 0}, sort=[("generated_at", DESCENDING)])
        if not doc:
            raise HTTPException(status_code=404, detail="No insights in collection")

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/latest-risk")
def get_latest_risk_insight(collection: str):
    """Return the most recent insight document that contains a `risk_score`.

    This is used to drive the Fish Stress Risk circle value in the UI.
    """
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        insights_db = client[INSIGHTS_DB_NAME]

        if collection not in insights_db.list_collection_names():
            raise HTTPException(status_code=404, detail="Insights collection not found")

        doc = insights_db[collection].find_one(
            {"risk_score": {"$exists": True}},
            {"_id": 0},
            sort=[("generated_at", DESCENDING)],
        )
        if not doc:
            raise HTTPException(status_code=404, detail="No risk insights in collection")

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/latest-insights-by-type")
def get_latest_insights_by_type(collection: str):
    """Return the latest insight document for each `insight_type` for a tank.

    This powers the UI "Predictive Notifications" list so each insight type can show
    its most recent message/status.
    """
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        insights_db = client[INSIGHTS_DB_NAME]

        if collection not in insights_db.list_collection_names():
            raise HTTPException(status_code=404, detail="Insights collection not found")

        # Find all available insight types.
        insight_types = insights_db[collection].distinct(
            "insight_type",
            {"insight_type": {"$exists": True, "$ne": None}},
        )
        insight_types = [t for t in insight_types if isinstance(t, str) and t.strip()]

        results = []
        for itype in insight_types:
            doc = insights_db[collection].find_one(
                {"insight_type": itype},
                {"_id": 0},
                sort=[("generated_at", DESCENDING)],
            )
            if not doc:
                continue

            ga = doc.get("generated_at")
            if isinstance(ga, datetime):
                generated_at = (ga if ga.tzinfo else ga.replace(tzinfo=timezone.utc)).isoformat()
            else:
                generated_at = str(ga) if ga is not None else None

            msg = doc.get("message")
            if isinstance(msg, dict):
                msg = msg.get("message") or msg.get("text") or str(msg)
            elif msg is not None and not isinstance(msg, str):
                msg = str(msg)

            results.append(
                {
                    "insight_type": itype,
                    "generated_at": generated_at,
                    "status": doc.get("status"),
                    "message": msg,
                    # water_chemistry: nested per-metric detail
                    "ph": doc.get("ph"),
                    "tds": doc.get("tds"),
                    # fish_stress_risk: score and level
                    "risk_score": doc.get("risk_score"),
                    "risk_level": doc.get("risk_level"),
                    # temperature_stability: trend direction
                    "trend": doc.get("trend"),
                }
            )

        # Sort newest -> oldest, so frontend can display consistently.
        results.sort(key=lambda r: r.get("generated_at") or "", reverse=True)
        return {"tank": collection, "insights": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/risk-history")
def get_risk_history(
    collection: str,
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    limit: int | None = Query(None, ge=1, le=200000),
):
    """Return risk_score history points from generated insights.

    Only documents with `risk_score` are returned.
    Points are sorted oldest -> newest.
    """
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        insights_db = client[INSIGHTS_DB_NAME]

        if collection not in insights_db.list_collection_names():
            raise HTTPException(status_code=404, detail="Insights collection not found")

        def parse_ts(v):
            if isinstance(v, datetime):
                return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            if isinstance(v, str):
                try:
                    s = v.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(s)
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except Exception:
                    return None
            return None

        # Find the latest generated_at timestamp to anchor the window.
        latest_doc = insights_db[collection].find_one(
            {"risk_score": {"$exists": True}},
            {"_id": 0, "generated_at": 1},
            sort=[("generated_at", DESCENDING)],
        )
        if not latest_doc:
            return {"tank": collection, "range": range, "points": []}

        latest_ts = parse_ts(latest_doc.get("generated_at"))
        if latest_ts is None:
            return {"tank": collection, "range": range, "points": []}

        if range == "24h":
            since = latest_ts - timedelta(hours=24)
        elif range == "7d":
            since = latest_ts - timedelta(days=7)
        else:
            since = latest_ts - timedelta(days=30)

        # Dynamic default limits (avoid huge payloads for 24h, allow fuller 30d).
        if limit is None:
            if range == "24h":
                limit = 5000
            elif range == "7d":
                limit = 20000
            else:
                limit = 50000

        since_iso = since.astimezone(timezone.utc).isoformat()

        projection = {"_id": 0, "generated_at": 1, "risk_score": 1}

        window_query = {
            "risk_score": {"$exists": True},
            "$or": [
                {"$and": [{"generated_at": {"$type": "date"}}, {"generated_at": {"$gte": since}}]},
                {"$and": [{"generated_at": {"$type": "string"}}, {"generated_at": {"$gte": since_iso}}]},
            ],
        }

        docs = list(
            insights_db[collection]
            .find(window_query, projection)
            .sort("generated_at", DESCENDING)
            .limit(limit)
        )

        # Safety fallback: if window query yields nothing, return latest docs (still filtered to risk_score).
        if not docs:
            docs = list(
                insights_db[collection]
                .find({"risk_score": {"$exists": True}}, projection)
                .sort("generated_at", DESCENDING)
                .limit(limit)
            )

        points = []
        for d in docs:
            ga = parse_ts(d.get("generated_at"))
            if ga is None or ga < since:
                continue
            points.append({"timestamp": ga.isoformat(), "value": d.get("risk_score")})

        points.sort(key=lambda p: p["timestamp"])
        return {"tank": collection, "range": range, "points": points}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tanks/{collection}/readings-history")
def get_readings_history(
    collection: str,
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    limit: int | None = Query(None, ge=1, le=200000),
):
    """Return sensor readings history points from aqua_gaurd_db.<tank_n>.

    We anchor the time window to the latest reading timestamp in the collection.
    We query for docs in that window (works for both Mongo Date and ISO-string
    timestamps), then parse and sort in Python.

    Points are returned oldest -> newest.
    """
    try:
        if not collection.startswith("tank_"):
            raise HTTPException(status_code=400, detail="Invalid collection")

        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]

        if collection not in db.list_collection_names():
            raise HTTPException(status_code=404, detail="Collection not found")

        def parse_ts(v):
            if isinstance(v, datetime):
                return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            if isinstance(v, str):
                try:
                    # Handle trailing 'Z'
                    s = v.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(s)
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except Exception:
                    return None
            return None

        # Find the latest timestamp to anchor the window.
        latest_doc = db[collection].find_one(
            {},
            {"_id": 0, "timestamp": 1},
            sort=[("timestamp", DESCENDING)],
        )
        if not latest_doc:
            return {"tank": collection, "range": range, "points": []}

        latest_ts = parse_ts(latest_doc.get("timestamp"))
        if latest_ts is None:
            return {"tank": collection, "range": range, "points": []}

        if range == "24h":
            since = latest_ts - timedelta(hours=24)
        elif range == "7d":
            since = latest_ts - timedelta(days=7)
        else:
            since = latest_ts - timedelta(days=30)

        # Dynamic default limits (avoid huge payloads for 24h, but allow full 30d).
        if limit is None:
            if range == "24h":
                limit = 5000
            elif range == "7d":
                limit = 20000
            else:
                limit = 50000

        since_iso = since.astimezone(timezone.utc).isoformat()

        projection = {
            "_id": 0,
            "timestamp": 1,
            "temperature": 1,
            "ph": 1,
            "turbidity": 1,
            "tds": 1,
        }

        # Query both date and string timestamps.
        window_query = {
            "$or": [
                {"$and": [{"timestamp": {"$type": "date"}}, {"timestamp": {"$gte": since}}]},
                {"$and": [{"timestamp": {"$type": "string"}}, {"timestamp": {"$gte": since_iso}}]},
            ]
        }

        docs = list(
            db[collection]
            .find(window_query, projection)
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        # Safety fallback: if window query yields nothing (type mismatch, etc.), return latest docs.
        if not docs:
            docs = list(db[collection].find({}, projection).sort("timestamp", DESCENDING).limit(limit))

        points = []
        for d in docs:
            ts = parse_ts(d.get("timestamp"))
            if ts is None:
                continue
            if ts < since:
                continue

            # Prefer explicit turbidity field; fall back to tds only if turbidity missing
            turb = d.get("turbidity")
            if turb is None:
                turb = d.get("tds")

            points.append(
                {
                    "timestamp": ts.isoformat(),
                    "temperature": d.get("temperature"),
                    "ph": d.get("ph"),
                    "turbidity": turb,
                }
            )

        points.sort(key=lambda p: p["timestamp"])
        return {"tank": collection, "range": range, "points": points}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
