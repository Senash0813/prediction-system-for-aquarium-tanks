from dotenv import load_dotenv
import os

# Load .env from backend root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGODB_URI")

# Main cleaned readings database
MONGO_DB_NAME = "aqua_gaurd_db"

# Database for generated insights
INSIGHTS_DB_NAME = "generated_insights"

# Auto-delete insight documents after 7 days
INSIGHTS_TTL_SECONDS = 7 * 24 * 60 * 60


def get_tank_collection_name(tank_id: str) -> str:
    """
    Returns the collection name for a given tank.
    Example: tank_1 -> tank_1
    """
    return tank_id


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
# Runs every 3 minutes
SCHEDULER_INTERVAL_SECONDS = 180


# ---------------------------------------------------------------------------
# Trend window
# ---------------------------------------------------------------------------
# 10 readings at 3-minute intervals = about 30 minutes of history
TREND_WINDOW_SIZE = 10


# ---------------------------------------------------------------------------
# Aquarium water chemistry thresholds
# These are general freshwater aquarium defaults
# ---------------------------------------------------------------------------

# pH thresholds
PH_SAFE_MIN = 6.5
PH_SAFE_MAX = 7.8
PH_CRITICAL_LOW = 6.0
PH_CRITICAL_HIGH = 8.5

# TDS thresholds (ppm)
TDS_SAFE_MIN = 150
TDS_SAFE_MAX = 400
TDS_WARNING_MAX = 500
TDS_CRITICAL_MAX = 700

# Temperature thresholds (°C)
TEMPERATURE_SAFE_MIN = 24.0
TEMPERATURE_SAFE_MAX = 30.0

# ---------------------------------------------------------------------------
# Trend sensitivity thresholds
# Minimum slope per minute to consider a real upward/downward trend
# ---------------------------------------------------------------------------
PH_CHANGE_RATE_THRESHOLD = 0.01
TDS_CHANGE_RATE_THRESHOLD = 2.0
TEMP_CHANGE_RATE_THRESHOLD = 0.02