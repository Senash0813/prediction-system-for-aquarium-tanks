import pandas as pd

from .feature_builder import build_feature_dict, FEATURE_COLUMNS
from .model_loader import load_anomaly_model


def detect_anomaly(readings: list[dict]) -> dict:
    """
    Uses Isolation Forest to detect unusual behavior.
    """
    features = build_feature_dict(readings)

    # Create DataFrame with same feature names used in training
    X_input = pd.DataFrame([features], columns=FEATURE_COLUMNS)

    model = load_anomaly_model()

    prediction = int(model.predict(X_input)[0])  # -1 anomaly, 1 normal
    raw_score = float(model.decision_function(X_input)[0])

    anomaly_score = round(max(0.0, min(1.0, (0.5 - raw_score))), 3)

    return {
        "is_anomalous": prediction == -1,
        "score": anomaly_score,
    }