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
    return tank_id


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCHEDULER_INTERVAL_SECONDS = 180  # 3 minutes


# ---------------------------------------------------------------------------
# Trend window / ML window
# ---------------------------------------------------------------------------
TREND_WINDOW_SIZE = 10            # last 10 readings used for current rule analysis
ML_INPUT_WINDOW_SIZE = 10         # input window for ML features
ML_FORECAST_HORIZON_STEPS = 10    # predict ~30 minutes ahead if sampling interval is 3 min

# ---------------------------------------------------------------------------
# Aquarium water chemistry thresholds
# ---------------------------------------------------------------------------
PH_SAFE_MIN = 6.5
PH_SAFE_MAX = 7.8
PH_CRITICAL_LOW = 6.0
PH_CRITICAL_HIGH = 8.5

TDS_SAFE_MIN = 150
TDS_SAFE_MAX = 400
TDS_WARNING_MAX = 500
TDS_CRITICAL_MAX = 700

TEMPERATURE_SAFE_MIN = 24.0
TEMPERATURE_SAFE_MAX = 30.0

# ---------------------------------------------------------------------------
# Trend sensitivity thresholds
# ---------------------------------------------------------------------------
PH_CHANGE_RATE_THRESHOLD = 0.01
TDS_CHANGE_RATE_THRESHOLD = 2.0
TEMP_CHANGE_RATE_THRESHOLD = 0.02

# ---------------------------------------------------------------------------
# ML model paths
# ---------------------------------------------------------------------------
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

PH_FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "ph_forecast_model.joblib")
TDS_FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "tds_forecast_model.joblib")
TEMP_FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "temp_forecast_model.joblib")
FUTURE_RISK_MODEL_PATH = os.path.join(MODEL_DIR, "future_risk_classifier.joblib")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_detector.joblib")

# ---------------------------------------------------------------------------
# ML settings
# ---------------------------------------------------------------------------
ANOMALY_SCORE_THRESHOLD = 0.60
MIN_TRAINING_ROWS = 50
RANDOM_STATE = 42