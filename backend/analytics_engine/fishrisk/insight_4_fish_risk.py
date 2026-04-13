from datetime import datetime, timezone
from settings import (
    TEMP_SAFE_MIN, TEMP_SAFE_MAX,
    PH_SAFE_MIN, PH_SAFE_MAX, PH_DANGER_MIN, PH_DANGER_MAX,
    TURBIDITY_MODERATE, TURBIDITY_HIGH
)

def prepare_readings(raw_readings):
    cleaned = []
    for r in raw_readings:
        temp = r.get("temperature")
        ph = r.get("ph")
        turb = r.get("turbidity")
        tds = r.get("tds")
        light = r.get("light")
        ts = r.get("timestamp")

        if temp is None or ph is None or turb is None or ts is None:
            continue

        cleaned.append({
            "temperature": float(temp),
            "ph": float(ph),
            "turbidity": float(turb),
            "tds": float(tds) if tds is not None else None,
            "light": str(light) if light is not None else None,
            "timestamp": ts,
        })
    return cleaned

def calculate_risk(temp, ph, turb):
    risk = 0

    if temp < 22 or temp > 30:
        risk += 40
    elif temp < 24 or temp > 28:
        risk += 20

    if ph < PH_DANGER_MIN or ph > PH_DANGER_MAX:
        risk += 30
    elif ph < PH_SAFE_MIN or ph > PH_SAFE_MAX:
        risk += 15

    if turb > TURBIDITY_HIGH:
        risk += 30
    elif turb > TURBIDITY_MODERATE:
        risk += 15

    return risk

def risk_to_label(score):
    if score <= 30:
        return "SAFE"
    elif score <= 60:
        return "MODERATE"
    return "HIGH"

def calculate_trend_features(readings):
    if len(readings) < 2:
        return {
            "temp_change": 0.0,
            "ph_change": 0.0,
            "turb_change": 0.0,
            "risk_change": 0.0
        }

    current = readings[-1]
    previous = readings[-2]

    current_risk = calculate_risk(current["temperature"], current["ph"], current["turbidity"])
    prev_risk = calculate_risk(previous["temperature"], previous["ph"], previous["turbidity"])

    return {
        "temp_change": current["temperature"] - previous["temperature"],
        "ph_change": current["ph"] - previous["ph"],
        "turb_change": current["turbidity"] - previous["turbidity"],
        "risk_change": current_risk - prev_risk
    }

def detect_stress_trend(trend):
    trend_score = 0

    if trend["temp_change"] > 0.5:
        trend_score += 1
    if abs(trend["ph_change"]) > 0.1:
        trend_score += 1
    if trend["turb_change"] > 2:
        trend_score += 1
    if trend["risk_change"] > 0:
        trend_score += 1
    elif trend["risk_change"] < 0:
        trend_score -= 1

    if trend_score >= 2:
        return "Increasing"
    elif trend_score <= -1:
        return "Decreasing"
    return "Stable"

def detect_causes(current, trend):
    causes = []

    if current["temperature"] < 22:
        causes.append("low temperature")
    elif current["temperature"] > 28:
        causes.append("high temperature")

    if current["ph"] < PH_SAFE_MIN:
        causes.append("low pH")
    elif current["ph"] > PH_SAFE_MAX:
        causes.append("high pH")

    if current["turbidity"] > TURBIDITY_HIGH:
        causes.append("high turbidity")
    elif current["turbidity"] > TURBIDITY_MODERATE:
        causes.append("moderate turbidity")

    if trend["temp_change"] > 0:
        causes.append("increasing temperature")
    elif trend["temp_change"] < 0:
        causes.append("falling temperature")

    if trend["ph_change"] > 0:
        causes.append("rising pH")
    elif trend["ph_change"] < 0:
        causes.append("falling pH")

    if trend["turb_change"] > 0:
        causes.append("rising turbidity")
    elif trend["turb_change"] < 0:
        causes.append("falling turbidity")

    return causes

def suggest_actions(causes):
    actions = []

    if "high temperature" in causes or "increasing temperature" in causes:
        actions.append("cool the water and improve aeration")
    if "low temperature" in causes:
        actions.append("check the heater and stabilize water temperature")
    if "high turbidity" in causes or "rising turbidity" in causes:
        actions.append("check filtration and reduce feeding")
    if "moderate turbidity" in causes:
        actions.append("monitor tank cleanliness and water clarity")
    if "low pH" in causes or "high pH" in causes or "rising pH" in causes or "falling pH" in causes:
        actions.append("adjust pH gradually to avoid stressing the fish")

    if not actions:
        actions.append("continue monitoring current tank conditions")

    return actions

def build_message(risk_level, stress_trend, causes):
    if causes:
        cause_text = ", ".join(causes)
        return f"Fish stress risk is {risk_level} and {stress_trend.lower()} due to {cause_text}."
    return f"Fish stress risk is {risk_level} and {stress_trend.lower()}."

def generate_insight(tank_id, raw_readings):
    generated_at = datetime.now(timezone.utc).isoformat()
    readings = prepare_readings(raw_readings)

    if len(readings) < 2:
        return {
            "tank_id": tank_id,
            "status": "insufficient_data",
            "risk_score": None,
            "risk_level": None,
            "stress_trend": None,
            "causes": [],
            "actions": [],
            "message": "Not enough readings to generate fish stress insight.",
            "generated_at": generated_at,
        }

    current = readings[-1]
    risk_score = calculate_risk(current["temperature"], current["ph"], current["turbidity"])
    risk_level = risk_to_label(risk_score)
    trend = calculate_trend_features(readings)
    stress_trend = detect_stress_trend(trend)
    causes = detect_causes(current, trend)
    actions = suggest_actions(causes)
    message = build_message(risk_level, stress_trend, causes)

    status = "normal"
    if risk_level == "HIGH":
        status = "alert"
    elif risk_level == "MODERATE" or stress_trend == "Increasing":
        status = "warning"

    return {
        "tank_id": tank_id,
        "status": status,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "stress_trend": stress_trend,
        "causes": causes,
        "actions": actions,
        "message": message,
        "generated_at": generated_at,
    }