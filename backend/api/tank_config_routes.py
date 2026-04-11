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
    safe_ranges: dict[str, SafeRange]


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
