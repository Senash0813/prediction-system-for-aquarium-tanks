from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

# Add backend root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_NAME, RAW_COLLECTION_TANK1, PROCESSED_COLLECTION_TANK1
from cleaning import clean_sensor_data
from transform import transform_sensor_data

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in environment variables")

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

raw_collection = db[RAW_COLLECTION_TANK1]
processed_collection = db[PROCESSED_COLLECTION_TANK1]


def process_one_document(raw_doc: dict, last_good_values: dict) -> dict:
    """
    Take one raw doc, clean it using in-memory last good values,
    transform it, and return final processed doc.
    """

    # Copy document and remove raw-only fields
    working_doc = dict(raw_doc)
    working_doc.pop("_id", None)
    working_doc.pop("processed", None)

    # Clean using in-memory last good numeric values
    cleaned_doc = clean_sensor_data(working_doc, last_good_values)

    # Transform cleaned numeric data
    transformed_doc = transform_sensor_data(cleaned_doc)

    return transformed_doc


def main():
    raw_docs = list(
        raw_collection.find({"processed": False}).sort("timestamp", 1)
    )

    if not raw_docs:
        print(f"No unprocessed raw documents found in {RAW_COLLECTION_TANK1}")
        return

    # In-memory storage for latest valid numeric values
    last_good_values = {}

    processed_count = 0

    for raw_doc in raw_docs:
        final_doc = process_one_document(raw_doc, last_good_values)

        processed_collection.insert_one(final_doc)

        raw_collection.update_one(
            {"_id": raw_doc["_id"]},
            {"$set": {"processed": True}}
        )

        processed_count += 1

    print(
        f"Processed {processed_count} documents from "
        f"{RAW_COLLECTION_TANK1} into {PROCESSED_COLLECTION_TANK1}"
    )


if __name__ == "__main__":
    main()