import os
from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "aqua_gaurd_db"


def load_tank_data(collection_name: str) -> pd.DataFrame:
    """
    Load all documents from a processed tank collection into a pandas DataFrame.
    """
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI not found in environment variables")

    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db[collection_name]

    docs = list(collection.find({}, {"_id": 0}))

    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df