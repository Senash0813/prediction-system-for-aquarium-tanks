from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from dotenv import load_dotenv
import os

from config import DATABASE_NAME, RAW_COLLECTION_TANK1, DEFAULT_DAYS, DEFAULT_INTERVAL_MINUTES
from tank1_profile import generate_tank1_sensor_reading

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in environment variables")

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
raw_collection = db[RAW_COLLECTION_TANK1]

# Sri Lanka Time Zone
SL_TIMEZONE = ZoneInfo("Asia/Colombo")


def generate_time_series(days: int, interval_minutes: int):
    """
    Generate timestamps for past N days until now (Sri Lanka time)
    """
    end_time = datetime.now(SL_TIMEZONE)
    start_time = end_time - timedelta(days=days)

    current = start_time
    while current <= end_time:
        yield current
        current += timedelta(minutes=interval_minutes)


def main():
    days = DEFAULT_DAYS
    interval_minutes = DEFAULT_INTERVAL_MINUTES

    print("Generating raw sensor data for tank_1 (Sri Lanka time)...")
    print(f"Days: {days}")
    print(f"Interval: {interval_minutes} minutes")
    print("-" * 50)

    timestamps = list(generate_time_series(days, interval_minutes))
    documents = []

    for ts in timestamps:
        doc = generate_tank1_sensor_reading(ts)
        documents.append(doc)

    if not documents:
        print("No documents generated.")
        return

    result = raw_collection.insert_many(documents)

    print(f"Inserted {len(result.inserted_ids)} documents into '{RAW_COLLECTION_TANK1}'")
    print("Done ✅")


if __name__ == "__main__":
    main()