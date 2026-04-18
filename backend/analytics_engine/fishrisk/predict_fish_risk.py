import os
from functools import lru_cache

import joblib
import pandas as pd

try:
    # Package imports (used when loaded by FastAPI app).
    from .settings import (
        MODEL_FILENAME,
        PREDICTION_HORIZON_MINUTES,
        LIGHT_CATEGORY_TO_NUMERIC,
    )
except ImportError:
    # Script imports (used when run directly).
    from settings import (
        MODEL_FILENAME,
        PREDICTION_HORIZON_MINUTES,
        LIGHT_CATEGORY_TO_NUMERIC,
    )


@lru_cache(maxsize=1)
def load_model():
    """Load the trained ML model once and reuse it."""
    if not os.path.exists(MODEL_FILENAME):
        raise FileNotFoundError(
            f"Model file '{MODEL_FILENAME}' not found. Train and save the model first."
        )
    return joblib.load(MODEL_FILENAME)


def calculate_risk(temp, ph, turb):
    risk = 0

    if temp < 22 or temp > 30:
        risk += 40
    elif temp < 24 or temp > 28:
        risk += 20

    if ph < 6.0 or ph > 8.0:
        risk += 30
    elif ph < 6.5 or ph > 7.5:
        risk += 15

    if turb > 30:
        risk += 30
    elif turb > 20:
        risk += 15

    return risk


def risk_to_label(score):
    if score <= 30:
        return "SAFE"
    elif score <= 60:
        return "MODERATE"
    return "HIGH"


def light_to_numeric(light_value):
    """Convert DB light values into numeric form for the ML model."""
    if light_value is None:
        return 0.0

    if isinstance(light_value, (int, float)):
        return float(light_value)

    light_str = str(light_value).strip()
    if light_str in LIGHT_CATEGORY_TO_NUMERIC:
        return LIGHT_CATEGORY_TO_NUMERIC[light_str]

    try:
        return float(light_str)
    except ValueError:
        return 0.0


def detect_causes(row):
    causes = []

    if row["temperature"] < 22:
        causes.append("low temperature")
    elif row["temperature"] > 28:
        causes.append("high temperature")

    if row["ph"] < 6.5:
        causes.append("low pH")
    elif row["ph"] > 7.5:
        causes.append("high pH")

    if row["turbidity"] > 30:
        causes.append("high turbidity")
    elif row["turbidity"] > 20:
        causes.append("moderate turbidity")

    if row["temp_change"] > 0:
        causes.append("increasing temperature")
    elif row["temp_change"] < 0:
        causes.append("falling temperature")

    if row["ph_change"] > 0:
        causes.append("rising pH")
    elif row["ph_change"] < 0:
        causes.append("falling pH")

    if row["turb_change"] > 0:
        causes.append("rising turbidity")
    elif row["turb_change"] < 0:
        causes.append("falling turbidity")

    return causes


def suggest_actions(causes):
    actions = []

    if "high temperature" in causes or "increasing temperature" in causes:
        actions.append("cool the water and improve aeration")

    if "low temperature" in causes:
        actions.append("check heater and stabilize water temperature")

    if "high turbidity" in causes or "rising turbidity" in causes:
        actions.append("check filtration and reduce feeding")

    if "moderate turbidity" in causes:
        actions.append("monitor water clarity and clean tank if needed")

    if (
        "low pH" in causes
        or "high pH" in causes
        or "rising pH" in causes
        or "falling pH" in causes
    ):
        actions.append("adjust pH gradually to avoid shocking the fish")

    if not actions:
        actions.append("continue monitoring current tank conditions")

    return actions


def build_prediction_message(predicted_label, trend_label, causes):
    if causes:
        cause_text = ", ".join(causes)
        return (
            f"Predicted fish stress in the next {PREDICTION_HORIZON_MINUTES} minutes is "
            f"{predicted_label} and {trend_label.lower()} due to {cause_text}."
        )

    return (
        f"Predicted fish stress in the next {PREDICTION_HORIZON_MINUTES} minutes is "
        f"{predicted_label} and {trend_label.lower()}."
    )


def _prepare_dataframe(raw_readings):
    df = pd.DataFrame(raw_readings)

    required_columns = ["temperature", "ph", "turbidity", "timestamp"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    if "tds" not in df.columns:
        df["tds"] = 0.0
    if "light" not in df.columns:
        df["light"] = 0.0

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["ph"] = pd.to_numeric(df["ph"], errors="coerce")
    df["turbidity"] = pd.to_numeric(df["turbidity"], errors="coerce")
    df["tds"] = pd.to_numeric(df["tds"], errors="coerce")
    df["light_numeric"] = df["light"].apply(light_to_numeric)

    df = df.dropna(subset=["temperature", "ph", "turbidity", "timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    # Fill optional values safely
    df["tds"] = df["tds"].ffill().bfill().fillna(0.0)

    return df


def predict_fish_risk(raw_readings):
    """
    Builds the same features used during training and returns the ML prediction.
    """
    try:
        df = _prepare_dataframe(raw_readings)

        if len(df) < 3:
            return {
                "enabled": True,
                "status": "insufficient_data",
                "predicted_risk_score": None,
                "predicted_risk_level": None,
                "predicted_trend": None,
                "predicted_causes": [],
                "recommended_actions": [],
                "message": "Not enough readings for ML prediction. Need at least 3 readings.",
            }

        df["risk_score"] = df.apply(
            lambda row: calculate_risk(row["temperature"], row["ph"], row["turbidity"]),
            axis=1,
        )

        df["temp_prev"] = df["temperature"].shift(1)
        df["ph_prev"] = df["ph"].shift(1)
        df["turb_prev"] = df["turbidity"].shift(1)
        df["risk_prev"] = df["risk_score"].shift(1)

        df["temp_change"] = df["temperature"] - df["temp_prev"]
        df["ph_change"] = df["ph"] - df["ph_prev"]
        df["turb_change"] = df["turbidity"] - df["turb_prev"]
        df["risk_change"] = df["risk_score"] - df["risk_prev"]

        df["time_diff_min"] = df["timestamp"].diff().dt.total_seconds() / 60.0
        df["time_diff_min"] = df["time_diff_min"].replace(0, pd.NA)

        df["temp_rate"] = df["temp_change"] / df["time_diff_min"]
        df["ph_rate"] = df["ph_change"] / df["time_diff_min"]
        df["turb_rate"] = df["turb_change"] / df["time_diff_min"]
        df["risk_rate"] = df["risk_change"] / df["time_diff_min"]

        df["temp_roll3"] = df["temperature"].rolling(window=3).mean()
        df["ph_roll3"] = df["ph"].rolling(window=3).mean()
        df["turb_roll3"] = df["turbidity"].rolling(window=3).mean()
        df["risk_roll3"] = df["risk_score"].rolling(window=3).mean()

        df["temp_std3"] = df["temperature"].rolling(window=3).std()
        df["ph_std3"] = df["ph"].rolling(window=3).std()
        df["turb_std3"] = df["turbidity"].rolling(window=3).std()

        df = df.dropna().reset_index(drop=True)

        if df.empty:
            return {
                "enabled": True,
                "status": "insufficient_data",
                "predicted_risk_score": None,
                "predicted_risk_level": None,
                "predicted_trend": None,
                "predicted_causes": [],
                "recommended_actions": [],
                "message": "Not enough valid rows after feature engineering for ML prediction.",
            }

        latest_row = df.iloc[-1]

        features = [
            "temperature",
            "ph",
            "turbidity",
            "tds",
            "light_numeric",
            "risk_score",
            "temp_change",
            "ph_change",
            "turb_change",
            "risk_change",
            "temp_rate",
            "ph_rate",
            "turb_rate",
            "risk_rate",
            "temp_roll3",
            "ph_roll3",
            "turb_roll3",
            "risk_roll3",
            "temp_std3",
            "ph_std3",
            "turb_std3",
        ]

        input_df = pd.DataFrame([latest_row[features]])
        input_df = input_df.rename(columns={"light_numeric": "light"})

        model = load_model()
        predicted_score = float(model.predict(input_df)[0])
        predicted_label = risk_to_label(predicted_score)

        current_risk_score = float(latest_row["risk_score"])
        predicted_change = predicted_score - current_risk_score

        if predicted_change > 5:
            predicted_trend = "Increasing"
        elif predicted_change < -5:
            predicted_trend = "Decreasing"
        else:
            predicted_trend = "Stable"

        predicted_causes = detect_causes(latest_row)
        recommended_actions = suggest_actions(predicted_causes)
        message = build_prediction_message(
            predicted_label,
            predicted_trend,
            predicted_causes,
        )

        return {
            "enabled": True,
            "status": "ok",
            "predicted_risk_score": round(predicted_score, 2),
            "predicted_risk_level": predicted_label,
            "predicted_trend": predicted_trend,
            "predicted_causes": predicted_causes,
            "recommended_actions": recommended_actions,
            "message": message,
        }

    except Exception as e:
        return {
            "enabled": True,
            "status": "error",
            "predicted_risk_score": None,
            "predicted_risk_level": None,
            "predicted_trend": None,
            "predicted_causes": [],
            "recommended_actions": [],
            "message": f"ML prediction failed: {e}",
        }