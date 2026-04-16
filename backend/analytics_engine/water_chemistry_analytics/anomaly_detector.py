from .feature_builder import build_feature_dict, feature_dict_to_row
from .model_loader import load_anomaly_model


def detect_anomaly(readings: list[dict]) -> dict:
    """
    Uses Isolation Forest to detect unusual behavior.
    """
    features = build_feature_dict(readings)
    row = [feature_dict_to_row(features)]

    model = load_anomaly_model()

    prediction = int(model.predict(row)[0])  # -1 anomaly, 1 normal
    raw_score = float(model.decision_function(row)[0])

    # Convert to a more user-friendly anomaly score:
    # smaller / negative decision function => more anomalous
    anomaly_score = round(max(0.0, min(1.0, (0.5 - raw_score))), 3)

    return {
        "is_anomalous": prediction == -1,
        "score": anomaly_score,
    }