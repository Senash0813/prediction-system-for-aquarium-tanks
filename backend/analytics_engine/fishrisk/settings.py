from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = "aqua_gaurd_db"
INSIGHTS_DB_NAME = "generated_insights"
INSIGHTS_TTL_SECONDS = 7 * 24 * 60 * 60

SCHEDULER_INTERVAL_SECONDS = 180
TREND_WINDOW_SIZE = 10

TEMP_SAFE_MIN = 24.0
TEMP_SAFE_MAX = 30.0

PH_SAFE_MIN = 6.5
PH_SAFE_MAX = 7.5
PH_DANGER_MIN = 6.0
PH_DANGER_MAX = 8.0

TURBIDITY_MODERATE = 20.0
TURBIDITY_HIGH = 30.0

def get_tank_collection_name(tank_id: str) -> str:
    return tank_id