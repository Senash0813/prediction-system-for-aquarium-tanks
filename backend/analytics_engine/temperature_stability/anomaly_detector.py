# anomaly_detector.py
#
# Isolation Forest-based anomaly detector for temperature readings.
#
# How it works:
#   1. Takes 7 days of historical readings → builds a "what normal looks like" model
#   2. Scores the current window of readings against that model
#   3. Returns whether anything in the current window looks unusual
#
# Features used per reading:
#   - temperature     : the raw value
#   - hour_of_day     : hour + fractional minutes (e.g. 14.5 = 14:30)
#                       This lets the model understand daily temperature cycles
#                       (tanks naturally run cooler at night, warmer midday)

import numpy as np
from sklearn.ensemble import IsolationForest

from .settings import ANOMALY_CONTAMINATION, ANOMALY_MIN_HISTORY


# ============================================================
# SECTION 1 — Feature Extraction
# ============================================================

def build_features(readings: list[dict]) -> np.ndarray:
    """
    Converts a list of reading dicts into a 2D numpy array for the model.

    Each row represents one reading with two features:
        [ temperature,  hour_of_day ]

    hour_of_day is expressed as a float (e.g. 14.5 = 14:30) so the model
    can learn that 26°C at 2am is unusual even if 26°C at 2pm is normal.

    Args:
        readings: List of dicts with at least 'temperature' and 'timestamp' keys.

    Returns:
        numpy array of shape (n_readings, 2)
    """
    features = []
    for r in readings:
        temp = float(r["temperature"])
        ts = r["timestamp"]
        hour_of_day = ts.hour + ts.minute / 60.0
        features.append([temp, hour_of_day])

    return np.array(features)


# ============================================================
# SECTION 2 — Anomaly Detection
# ============================================================

def detect_anomaly(current_readings: list[dict], historical_readings: list[dict]) -> dict:
    """
    Trains an Isolation Forest on historical_readings and scores the
    current_readings to determine whether they look anomalous.

    The model is trained fresh on every call — at this scale (~3000 samples,
    2 features) training takes under 100ms, so no model persistence is needed.

    Args:
        current_readings    : the recent window of readings (prepared dicts)
        historical_readings : 7-day baseline of readings from MongoDB

    Returns a dict with:
        - is_anomaly    : True if any current reading is flagged as anomalous
        - anomaly_score : average decision score across current readings
                          (more negative = more anomalous; normal readings score > 0)
        - anomaly_count : number of current readings flagged as anomalous
        - reason        : short string explaining the flag, or None if normal
    """
    # Guard — not enough history to build a reliable baseline
    if len(historical_readings) < ANOMALY_MIN_HISTORY:
        return {
            "is_anomaly": False,
            "anomaly_score": None,
            "anomaly_count": 0,
            "reason": "insufficient_history",
        }

    # Guard — no current readings to score
    if not current_readings:
        return {
            "is_anomaly": False,
            "anomaly_score": None,
            "anomaly_count": 0,
            "reason": "no_current_readings",
        }

    # Build feature matrices
    X_train   = build_features(historical_readings)
    X_current = build_features(current_readings)

    # Train the model on the historical baseline
    model = IsolationForest(
        contamination=ANOMALY_CONTAMINATION,
        random_state=42,
        n_estimators=100,
    )
    model.fit(X_train)

    # Score the current readings
    # predict() returns: -1 = anomaly, 1 = normal
    # decision_function() returns: negative = anomalous, positive = normal
    predictions    = model.predict(X_current)
    scores         = model.decision_function(X_current)
    anomaly_count  = int(np.sum(predictions == -1))
    avg_score      = float(np.mean(scores))

    is_anomaly = anomaly_count > 0

    reason = None
    if is_anomaly:
        # Give a human-readable hint about what kind of anomaly was detected
        anomalous_temps = [
            current_readings[i]["temperature"]
            for i in range(len(predictions))
            if predictions[i] == -1
        ]
        hist_temps  = [r["temperature"] for r in historical_readings]
        hist_mean   = float(np.mean(hist_temps))

        if any(t > hist_mean for t in anomalous_temps):
            reason = "unusually_high_temperature_for_time_of_day"
        else:
            reason = "unusually_low_temperature_for_time_of_day"

    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": round(avg_score, 4),
        "anomaly_count": anomaly_count,
        "reason": reason,
    }
