import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest

from .settings import (
    MODEL_DIR,
    PH_FORECAST_MODEL_PATH,
    TDS_FORECAST_MODEL_PATH,
    TEMP_FORECAST_MODEL_PATH,
    FUTURE_RISK_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    ML_INPUT_WINDOW_SIZE,
    ML_FORECAST_HORIZON_STEPS,
    MIN_TRAINING_ROWS,
    RANDOM_STATE,
)
from .mongo_client import get_all_tank_ids, fetch_all_readings_for_tank
from .feature_builder import build_feature_dict, FEATURE_COLUMNS
from .insight_2_water_chemistry import (
    prepare_readings,
    analyze_ph,
    analyze_tds,
    analyze_temperature,
    evaluate_water_chemistry,
)


RISK_TO_CODE = {
    "normal": 0,
    "monitor": 1,
    "warning": 2,
    "alert": 3,
}


def _future_status_label(future_window: list[dict]) -> str:
    """
    Uses your own rule engine to label future condition.
    This makes training hybrid and explainable.
    """
    future_window = prepare_readings(future_window)
    if len(future_window) < 2:
        return "normal"

    ph_analysis = analyze_ph(future_window)
    tds_analysis = analyze_tds(future_window)
    temp_analysis = analyze_temperature(future_window)
    evaluation = evaluate_water_chemistry(ph_analysis, tds_analysis, temp_analysis)

    status = evaluation["status"]
    if status == "alert":
        return "alert"
    if status == "warning":
        return "warning"
    if evaluation["overall_label"] == "Water Stable but Drifting":
        return "monitor"
    return "normal"


def build_training_dataframe() -> pd.DataFrame:
    rows = []
    tank_ids = get_all_tank_ids()

    for tank_id in tank_ids:
        readings = prepare_readings(fetch_all_readings_for_tank(tank_id))
        n = len(readings)

        min_required = ML_INPUT_WINDOW_SIZE + ML_FORECAST_HORIZON_STEPS
        if n < min_required:
            continue

        for start_idx in range(0, n - ML_INPUT_WINDOW_SIZE - ML_FORECAST_HORIZON_STEPS + 1):
            input_window = readings[start_idx:start_idx + ML_INPUT_WINDOW_SIZE]
            target_idx = start_idx + ML_INPUT_WINDOW_SIZE + ML_FORECAST_HORIZON_STEPS - 1
            future_point = readings[target_idx]

            future_window_start = max(0, target_idx - ML_INPUT_WINDOW_SIZE + 1)
            future_window = readings[future_window_start:target_idx + 1]

            feature_dict = build_feature_dict(input_window)

            row = {
                **feature_dict,
                "target_future_ph": future_point["ph"],
                "target_future_tds": future_point["tds"],
                "target_future_temp": future_point["temperature"],
                "target_future_status": RISK_TO_CODE[_future_status_label(future_window)],
            }
            rows.append(row)

    return pd.DataFrame(rows)


def train_and_save_models():
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = build_training_dataframe()
    if len(df) < MIN_TRAINING_ROWS:
        raise RuntimeError(
            f"Not enough training rows to build models. Found {len(df)}, need at least {MIN_TRAINING_ROWS}."
        )

    X = df[FEATURE_COLUMNS]

    y_ph = df["target_future_ph"]
    y_tds = df["target_future_tds"]
    y_temp = df["target_future_temp"]
    y_risk = df["target_future_status"]

    ph_model = RandomForestRegressor(
        n_estimators=200,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    ph_model.fit(X, y_ph)

    tds_model = RandomForestRegressor(
        n_estimators=200,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    tds_model.fit(X, y_tds)

    temp_model = RandomForestRegressor(
        n_estimators=200,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    temp_model.fit(X, y_temp)

    risk_model = RandomForestClassifier(
        n_estimators=200,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    risk_model.fit(X, y_risk)

    anomaly_model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=RANDOM_STATE,
    )
    anomaly_model.fit(X)

    joblib.dump(ph_model, PH_FORECAST_MODEL_PATH)
    joblib.dump(tds_model, TDS_FORECAST_MODEL_PATH)
    joblib.dump(temp_model, TEMP_FORECAST_MODEL_PATH)
    joblib.dump(risk_model, FUTURE_RISK_MODEL_PATH)
    joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)

    print("Training complete.")
    print(f"Rows used: {len(df)}")
    print(f"Models saved in: {MODEL_DIR}")


if __name__ == "__main__":
    train_and_save_models()