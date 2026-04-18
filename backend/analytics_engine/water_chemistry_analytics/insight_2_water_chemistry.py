from datetime import datetime, timezone

from .settings import (
    PH_CRITICAL_LOW,
    PH_CRITICAL_HIGH,
    TDS_WARNING_MAX,
    TDS_CRITICAL_MAX,
    PH_CHANGE_RATE_THRESHOLD,
    TDS_CHANGE_RATE_THRESHOLD,
    TEMP_CHANGE_RATE_THRESHOLD,
)
from .ml_predictor import predict_future
from .anomaly_detector import detect_anomaly
from .hybrid_decision import combine_rule_and_ml


# ============================================================
# SECTION 1 — Data Preparation
# ============================================================

def prepare_readings(raw_readings: list[dict]) -> list[dict]:
    cleaned = []

    for r in raw_readings:
        ph = r.get("ph")
        tds = r.get("tds")
        temperature = r.get("temperature")
        ts = r.get("timestamp")

        if ph is None or tds is None or temperature is None or ts is None:
            continue

        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        cleaned.append({
            "ph": float(ph),
            "tds": float(tds),
            "temperature": float(temperature),
            "timestamp": ts,
        })

    return cleaned


# ============================================================
# SECTION 2 — Shared Trend Analysis
# ============================================================

def calculate_numeric_trend(readings: list[dict], field: str, threshold: float) -> dict:
    if not readings:
        return {
            "field": field,
            "current": None,
            "rate_per_minute": 0.0,
            "total_change": 0.0,
            "direction": "stable",
            "window_minutes": 0.0,
            "values": [],
        }

    values = [float(r[field]) for r in readings]
    timestamps = [r["timestamp"] for r in readings]

    if len(readings) < 2:
        return {
            "field": field,
            "current": round(values[-1], 3),
            "rate_per_minute": 0.0,
            "total_change": 0.0,
            "direction": "stable",
            "window_minutes": 0.0,
            "values": values,
        }

    t0 = timestamps[0]
    elapsed = [(ts - t0).total_seconds() / 60.0 for ts in timestamps]

    n = len(elapsed)
    sum_x = sum(elapsed)
    sum_y = sum(values)
    sum_xy = sum(elapsed[i] * values[i] for i in range(n))
    sum_x2 = sum(x ** 2 for x in elapsed)

    denominator = (n * sum_x2) - (sum_x ** 2)
    rate = 0.0 if denominator == 0 else (n * sum_xy - sum_x * sum_y) / denominator

    total_change = values[-1] - values[0]
    window_minutes = elapsed[-1]

    if rate > threshold:
        direction = "rising"
    elif rate < -threshold:
        direction = "dropping"
    else:
        direction = "stable"

    return {
        "field": field,
        "current": round(values[-1], 3),
        "rate_per_minute": round(rate, 4),
        "total_change": round(total_change, 3),
        "direction": direction,
        "window_minutes": round(window_minutes, 1),
        "values": values,
    }


# ============================================================
# SECTION 3 — Individual Parameter Evaluation
# ============================================================

def analyze_ph(readings: list[dict], *, safe_min: float, safe_max: float) -> dict:
    trend = calculate_numeric_trend(readings, "ph", PH_CHANGE_RATE_THRESHOLD)
    current = trend["current"]

    if current is None:
        return {**trend, "status": "unknown", "severity": 0}

    if current < PH_CRITICAL_LOW:
        status = "critically_low"
        severity = 3
    elif current < safe_min:
        status = "low"
        severity = 2
    elif current > PH_CRITICAL_HIGH:
        status = "critically_high"
        severity = 3
    elif current > safe_max:
        status = "high"
        severity = 2
    else:
        if trend["direction"] in {"rising", "dropping"}:
            status = "normal_but_drifting"
            severity = 1
        else:
            status = "normal"
            severity = 0

    return {
        **trend,
        "status": status,
        "severity": severity,
    }


def analyze_tds(readings: list[dict], *, safe_min: float, safe_max: float) -> dict:
    trend = calculate_numeric_trend(readings, "tds", TDS_CHANGE_RATE_THRESHOLD)
    current = trend["current"]

    if current is None:
        return {**trend, "status": "unknown", "severity": 0}

    if current > TDS_CRITICAL_MAX:
        status = "critically_high"
        severity = 3
    elif current > TDS_WARNING_MAX:
        status = "very_high"
        severity = 2
    elif current > safe_max:
        status = "high"
        severity = 2
    elif current < safe_min:
        status = "low"
        severity = 1
    else:
        if trend["direction"] == "rising":
            status = "normal_but_rising"
            severity = 1
        else:
            status = "normal"
            severity = 0

    return {
        **trend,
        "status": status,
        "severity": severity,
    }


def analyze_temperature(readings: list[dict], *, safe_min: float, safe_max: float) -> dict:
    trend = calculate_numeric_trend(readings, "temperature", TEMP_CHANGE_RATE_THRESHOLD)
    current = trend["current"]

    if current is None:
        return {**trend, "status": "unknown", "severity": 0}

    if current < safe_min:
        status = "too_cold"
        severity = 2
    elif current > safe_max:
        status = "too_hot"
        severity = 2
    else:
        if trend["direction"] in {"rising", "dropping"}:
            status = "normal_but_shifting"
            severity = 1
        else:
            status = "normal"
            severity = 0

    return {
        **trend,
        "status": status,
        "severity": severity,
    }


# ============================================================
# SECTION 4 — Combined Water Chemistry Rule Engine
# ============================================================

def evaluate_water_chemistry(ph_analysis: dict, tds_analysis: dict, temp_analysis: dict) -> dict:
    triggered_rules = []

    severity = max(
        ph_analysis["severity"],
        tds_analysis["severity"],
        temp_analysis["severity"],
    )

    ph_status = ph_analysis["status"]
    tds_status = tds_analysis["status"]
    temp_status = temp_analysis["status"]

    if (
        ph_analysis["severity"] >= 2
        and tds_analysis["severity"] >= 2
        and temp_analysis["severity"] >= 2
    ):
        triggered_rules.append("severe_water_quality_degradation")
        severity = max(severity, 3)

    if ph_status in {"normal", "normal_but_drifting"} and tds_analysis["severity"] >= 2:
        triggered_rules.append("hidden_dissolved_solids_issue")
        severity = max(severity, 2)

    if ph_status in {"low", "critically_low"} and tds_analysis["severity"] >= 2:
        triggered_rules.append("acidic_stress_with_dissolved_buildup")
        severity = max(severity, 2)

    if ph_status in {"high", "critically_high"} and tds_analysis["severity"] >= 2:
        triggered_rules.append("alkaline_mineral_rich_water")
        severity = max(severity, 2)

    if temp_status == "too_hot" and (ph_analysis["severity"] >= 2 or tds_analysis["severity"] >= 2):
        triggered_rules.append("temperature_amplified_chemistry_stress")
        severity = max(severity, 2)

    abnormal_count = sum([
        1 if ph_analysis["severity"] >= 2 else 0,
        1 if tds_analysis["severity"] >= 2 else 0,
        1 if temp_analysis["severity"] >= 2 else 0,
    ])
    if abnormal_count >= 2:
        triggered_rules.append("combined_chemistry_instability")
        severity = max(severity, 2)

    if tds_analysis["direction"] == "rising" and ph_analysis["direction"] == "dropping":
        triggered_rules.append("waste_buildup_pattern")
        severity = max(severity, 2)

    if (
        ph_status in {"normal", "normal_but_drifting"}
        and tds_status in {"normal", "normal_but_rising"}
        and temp_status in {"normal", "normal_but_shifting"}
        and (
            ph_analysis["direction"] != "stable"
            or tds_analysis["direction"] != "stable"
            or temp_analysis["direction"] != "stable"
        )
    ):
        triggered_rules.append("stable_but_drifting")

    if severity >= 3:
        status = "alert"
        overall_label = "Critical Water Chemistry Risk"
    elif severity == 2:
        status = "warning"
        overall_label = "Water Chemistry Stress"
    else:
        status = "normal"
        overall_label = (
            "Water Stable but Drifting"
            if "stable_but_drifting" in triggered_rules
            else "Water Chemistry Stable"
        )

    return {
        "status": status,
        "overall_label": overall_label,
        "severity": severity,
        "triggered_rules": triggered_rules,
    }


# ============================================================
# SECTION 5 — User-Friendly Diagnosis & Recommendation
# ============================================================

def diagnose_chemistry_cause(ph_analysis: dict, tds_analysis: dict, temp_analysis: dict, evaluation: dict) -> str:
    rules = set(evaluation["triggered_rules"])

    if "severe_water_quality_degradation" in rules:
        return (
            "Several water conditions are outside the safe range at the same time. "
            "This means the tank water may be unsafe for fish if not addressed quickly."
        )

    if "acidic_stress_with_dissolved_buildup" in rules:
        return (
            "The water is becoming more acidic while dissolved solids are also high. "
            "This often happens when waste or other dissolved material starts building up in the tank."
        )

    if "alkaline_mineral_rich_water" in rules:
        return (
            "The water is more alkaline than expected and also has a high dissolved solid level. "
            "This suggests mineral-rich water that may not suit every fish type."
        )

    if "hidden_dissolved_solids_issue" in rules:
        return (
            "The pH looks acceptable, but dissolved solids are high. "
            "So the tank may seem fine at first glance while extra material is still building up in the water."
        )

    if "temperature_amplified_chemistry_stress" in rules:
        return (
            "The water is warmer than ideal, which can make other water quality issues harder on the fish."
        )

    if "waste_buildup_pattern" in rules:
        return (
            "Dissolved solids are rising while pH is falling. "
            "This pattern often suggests waste buildup or declining water freshness."
        )

    if "stable_but_drifting" in rules:
        return (
            "The tank is still within an acceptable range, but the readings are slowly moving away from the ideal condition."
        )

    return "The tank water is currently stable, and no major chemistry issue is detected."


def recommend_action(
    evaluation: dict,
    ph_analysis: dict,
    tds_analysis: dict,
    temp_analysis: dict,
    hybrid_decision: dict | None = None,
    ml_prediction: dict | None = None,
    ml_anomaly: dict | None = None,
) -> str:
    rules = set(evaluation["triggered_rules"])
    status = hybrid_decision["final_status"] if hybrid_decision else evaluation["status"]

    if status == "alert":
        return (
            "Please check the tank as soon as possible. "
            "Look at fish behavior, confirm the sensor readings, and consider a partial water change if the values stay abnormal."
        )

    if "acidic_stress_with_dissolved_buildup" in rules or "waste_buildup_pattern" in rules:
        return (
            "Check the tank maintenance condition and monitor the readings closely. "
            "A partial water change may help improve the water quality."
        )

    if "hidden_dissolved_solids_issue" in rules:
        return (
            "Review feeding, evaporation, and your recent water change routine. "
            "The tank may need attention even though the pH still looks normal."
        )

    if "temperature_amplified_chemistry_stress" in rules:
        return (
            "Check the heater setting, room temperature, and aeration. "
            "Keeping the tank closer to the ideal temperature may reduce stress on the fish."
        )

    if hybrid_decision and hybrid_decision["final_status"] == "warning":
        return (
            "The tank is acceptable right now, but the recent pattern suggests it should be watched closely over the next few readings."
        )

    if "stable_but_drifting" in rules:
        return (
            "No immediate action is needed, but continue monitoring the tank because the readings are gradually drifting."
        )

    return "No immediate action is needed. Continue normal tank monitoring."


# ============================================================
# SECTION 6 — Final Output
# ============================================================

def generate_insight(tank_id: str, readings: list[dict], safe_ranges: dict) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    readings = prepare_readings(readings)

    if len(readings) < 2:
        return {
            "tank_id": tank_id,
            "insight_type": "water_chemistry",
            "status": "insufficient_data",
            "message": "Not enough readings yet to generate a water chemistry insight.",
            "overall": None,
            "ph": None,
            "tds": None,
            "temperature": None,
            "diagnosis": None,
            "recommendation": None,
            "ml_prediction": None,
            "ml_anomaly": None,
            "hybrid_decision": None,
            "generated_at": generated_at,
        }

    ph_safe = safe_ranges.get("ph", {})
    tds_safe = safe_ranges.get("tds", {})
    temp_safe = safe_ranges.get("temperature", {})

    ph_analysis = analyze_ph(readings, safe_min=float(ph_safe.get("min")), safe_max=float(ph_safe.get("max")))
    tds_analysis = analyze_tds(readings, safe_min=float(tds_safe.get("min")), safe_max=float(tds_safe.get("max")))
    temp_analysis = analyze_temperature(readings, safe_min=float(temp_safe.get("min")), safe_max=float(temp_safe.get("max")))

    evaluation = evaluate_water_chemistry(ph_analysis, tds_analysis, temp_analysis)

    ml_prediction = None
    ml_anomaly = None
    hybrid_decision = None

    try:
        ml_prediction = predict_future(readings)
    except Exception:
        ml_prediction = {
            "predicted_ph": None,
            "predicted_tds": None,
            "predicted_temperature": None,
            "predicted_future_status": None,
        }

    try:
        ml_anomaly = detect_anomaly(readings)
    except Exception:
        ml_anomaly = {
            "is_anomalous": False,
            "score": 0.0,
        }

    if ml_prediction and ml_prediction.get("predicted_future_status"):
        hybrid_decision = combine_rule_and_ml(
            rule_status=evaluation["status"],
            rule_label=evaluation["overall_label"],
            rule_severity=evaluation["severity"],
            ml_prediction=ml_prediction,
            ml_anomaly=ml_anomaly,
        )
    else:
        hybrid_decision = {
            "final_status": evaluation["status"],
            "final_label": evaluation["overall_label"],
            "notes": [],
        }

    diagnosis = diagnose_chemistry_cause(ph_analysis, tds_analysis, temp_analysis, evaluation)
    diagnosis = _append_ml_context(diagnosis, ml_prediction, ml_anomaly, hybrid_decision)

    recommendation = recommend_action(
        evaluation,
        ph_analysis,
        tds_analysis,
        temp_analysis,
        hybrid_decision=hybrid_decision,
        ml_prediction=ml_prediction,
        ml_anomaly=ml_anomaly,
    )

    message = _build_message(
        evaluation,
        ph_analysis,
        tds_analysis,
        temp_analysis,
        diagnosis,
        hybrid_decision,
    )

    return {
        "tank_id": tank_id,
        "insight_type": "water_chemistry",
        "status": hybrid_decision["final_status"],
        "message": message,
        "overall": {
            "label": hybrid_decision["final_label"],
            "severity": evaluation["severity"],
            "triggered_rules": evaluation["triggered_rules"],
        },
        "ph": ph_analysis,
        "tds": tds_analysis,
        "temperature": temp_analysis,
        "diagnosis": diagnosis,
        "recommendation": recommendation,
        "ml_prediction": ml_prediction,
        "ml_anomaly": ml_anomaly,
        "hybrid_decision": hybrid_decision,
        "generated_at": generated_at,
    }


def _append_ml_context(
    diagnosis: str,
    ml_prediction: dict | None,
    ml_anomaly: dict | None,
    hybrid_decision: dict | None,
) -> str:
    parts = [diagnosis]

    if ml_prediction and ml_prediction.get("predicted_future_status"):
        pred_status = ml_prediction["predicted_future_status"]
        pred_ph = ml_prediction.get("predicted_ph")
        pred_tds = ml_prediction.get("predicted_tds")
        pred_temp = ml_prediction.get("predicted_temperature")

        parts.append(
            f"The ML model predicts near-future readings around pH {pred_ph}, "
            f"TDS {pred_tds} ppm, and temperature {pred_temp}°C, "
            f"with an expected future status of {pred_status}."
        )

    if ml_anomaly and ml_anomaly.get("is_anomalous"):
        parts.append("The recent pattern also looks unusual compared to normal tank behavior.")

    if hybrid_decision and hybrid_decision.get("notes"):
        parts.append(" ".join(hybrid_decision["notes"]))

    return " ".join(parts)


def _build_message(
    evaluation: dict,
    ph_analysis: dict,
    tds_analysis: dict,
    temp_analysis: dict,
    diagnosis: str,
    hybrid_decision: dict,
) -> str:
    ph_str = f"{ph_analysis['current']:.2f}"
    tds_str = f"{tds_analysis['current']:.1f}"
    temp_str = f"{temp_analysis['current']:.1f}°C"

    final_status = hybrid_decision["final_status"]
    final_label = hybrid_decision["final_label"]

    if final_status == "alert":
        prefix = "🚨 Alert"
    elif final_status == "warning":
        prefix = "⚠️ Warning"
    else:
        prefix = "✅ Status"

    return (
        f"{prefix}: {final_label}. "
        f"Current readings are pH {ph_str}, TDS {tds_str} ppm, and temperature {temp_str}. "
        f"{diagnosis}"
    )