from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "aqua_gaurd_db"
COLLECTION_NAME = "tank_config"

router = APIRouter(prefix="/api/tank-config", tags=["Tank Config"])


class SafeRange(BaseModel):
    min: float
    max: float


class TankConfigRequest(BaseModel):
    tank_id: str
    mac_address: str = ""
    safe_ranges: dict[str, SafeRange]


@router.get("/{tank_id}")
def get_tank_config(tank_id: str):
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        doc = collection.find_one({"tank_id": tank_id}, {"_id": 0, "safe_ranges": 1})
        if not doc:
            raise HTTPException(status_code=404, detail=f"No config found for tank '{tank_id}'")

        return {"tank_id": tank_id, "safe_ranges": doc.get("safe_ranges", {})}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def save_tank_config(config: TankConfigRequest):
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        if collection.find_one({"tank_id": config.tank_id}):
            raise HTTPException(
                status_code=409,
                detail=f"Config for tank '{config.tank_id}' already exists"
            )

        document = {
            "tank_id": config.tank_id,
            "mac_address": config.mac_address,
            "safe_ranges": {
                param: {"min": r.min, "max": r.max}
                for param, r in config.safe_ranges.items()
            },
            "created_at": datetime.now(timezone.utc),
        }

        collection.insert_one(document)
        return {"message": f"Config for '{config.tank_id}' saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
