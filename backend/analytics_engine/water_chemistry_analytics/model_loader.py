import joblib
from functools import lru_cache

from .settings import (
    PH_FORECAST_MODEL_PATH,
    TDS_FORECAST_MODEL_PATH,
    TEMP_FORECAST_MODEL_PATH,
    FUTURE_RISK_MODEL_PATH,
    ANOMALY_MODEL_PATH,
)


@lru_cache(maxsize=1)
def load_ph_model():
    return joblib.load(PH_FORECAST_MODEL_PATH)


@lru_cache(maxsize=1)
def load_tds_model():
    return joblib.load(TDS_FORECAST_MODEL_PATH)


@lru_cache(maxsize=1)
def load_temp_model():
    return joblib.load(TEMP_FORECAST_MODEL_PATH)


@lru_cache(maxsize=1)
def load_future_risk_model():
    return joblib.load(FUTURE_RISK_MODEL_PATH)


@lru_cache(maxsize=1)
def load_anomaly_model():
    return joblib.load(ANOMALY_MODEL_PATH)