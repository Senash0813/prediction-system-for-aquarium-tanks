from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get Mongo URI from .env
MONGO_URI = os.getenv("MONGODB_URI")

if not MONGO_URI:
    raise ValueError("MONGODB_URI not found in .env file")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["aqua_gaurd_db"]

# ⚠️ FIXED collection name (use same format as trigger)
collection = db["raw_tank_6"]

tank_id = "tank_6"

# -------------------------------
# Insert VALID data
# -------------------------------
collection.insert_one({
    "tank_id": tank_id,
    "timestamp": datetime.utcnow(),
    "temperature": 26.5,
    "ph": 7.3,
    "turbidity": 3.0,
    "tds": 300,
    "light": 1200,
    "processed": False
})

print("✅ Valid data inserted")

# -------------------------------
# Insert INVALID data (test fallback)
# -------------------------------
collection.insert_one({
    "tank_id": tank_id,
    "timestamp": datetime.utcnow(),
    "temperature": 999,
    "ph": -10,
    "turbidity": -5,
    "tds": 9999,
    "light": -100,
    "processed": False
})

print("⚠️ Invalid data inserted (should fallback)")

print("🚀 Test data inserted successfully")