from .feature_builder import build_feature_dict, feature_dict_to_row
from .model_loader import (
    load_ph_model,
    load_tds_model,
    load_temp_model,
    load_future_risk_model,
)


RISK_LABEL_MAP = {
    0: "normal",
    1: "monitor",
    2: "warning",
    3: "alert",
}


def predict_future(readings: list[dict]) -> dict:
    """
    Predicts future pH, TDS, temperature, and future risk class.
    """
    features = build_feature_dict(readings)
    row = [feature_dict_to_row(features)]

    ph_model = load_ph_model()
    tds_model = load_tds_model()
    temp_model = load_temp_model()
    risk_model = load_future_risk_model()

    predicted_ph = float(ph_model.predict(row)[0])
    predicted_tds = float(tds_model.predict(row)[0])
    predicted_temp = float(temp_model.predict(row)[0])
    predicted_risk_code = int(risk_model.predict(row)[0])

    return {
        "predicted_ph": round(predicted_ph, 3),
        "predicted_tds": round(predicted_tds, 3),
        "predicted_temperature": round(predicted_temp, 3),
        "predicted_future_status": RISK_LABEL_MAP.get(predicted_risk_code, "normal"),
        "feature_snapshot": features,
    }