# config/settings.py
from dotenv import load_dotenv
import os

# Load .env from the backend/ folder (one level up from config/)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = "aqua_gaurd_db"
INSIGHTS_DB_NAME = "generated_insights"
INSIGHTS_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

def get_tank_collection_name(tank_id: str) -> str:
    """Returns the MongoDB collection name for a given tank.
    e.g. 'tank_1' → 'tank_1'
    Centralised here so naming convention is changed in one place only.
    """
    return tank_id

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
# Runs every 3 minutes, matching the IoT sampling interval
SCHEDULER_INTERVAL_SECONDS = 180

# ---------------------------------------------------------------------------
# How many recent readings to pull for trend analysis
# A window of 10 readings = 30 minutes of history (at 3-min intervals)
# ---------------------------------------------------------------------------
TREND_WINDOW_SIZE = 10

# ---------------------------------------------------------------------------
# Temperature thresholds (°C)
# TODO: Replace with per-tank user-defined values fetched from DB/frontend
# ---------------------------------------------------------------------------
TEMPERATURE_SAFE_MIN = 24.0   # Below this → danger (too cold)
TEMPERATURE_SAFE_MAX = 30.0   # Above this → danger (too hot)

# ---------------------------------------------------------------------------
# Light intensity categorical thresholds (lux)
# Mirrors the categorize_light() function from the data pipeline
# ---------------------------------------------------------------------------
LIGHT_CATEGORIES = {
    "Night Mode":        (0,     50),
    "Dim Light":         (50,    500),
    "Low Light":         (500,   2000),
    "Ideal for Fish":    (2000,  5000),
    "Great for Plants":  (5000,  10000),
    "Too Bright":        (10000, float("inf")),
}

# Categories considered "environmentally stable" (no external cooling stress)
LIGHT_STABLE_CATEGORIES = {"Ideal for Fish", "Great for Plants", "Low Light"}

# Categories that suggest environmental shift (evening, room cooling, etc.)
LIGHT_SHIFT_CATEGORIES = {"Night Mode", "Dim Light", "Too Bright"}

# ---------------------------------------------------------------------------
# Prediction thresholds
# ---------------------------------------------------------------------------
# Minimum rate of change (°C/min) to be considered an active drop/rise
TEMP_CHANGE_RATE_THRESHOLD = 0.02

# If predicted time-to-unsafe is within this many minutes → raise alert
PREDICTION_ALERT_WINDOW_MINUTES = 60