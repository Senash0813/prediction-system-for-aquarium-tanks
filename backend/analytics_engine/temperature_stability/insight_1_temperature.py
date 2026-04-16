# insights/insight_1_temperature.py

from datetime import datetime, timezone
from .settings import (
    TEMP_CHANGE_RATE_THRESHOLD,
    PREDICTION_ALERT_WINDOW_MINUTES,
    TREND_WINDOW_SIZE,
)
from .light_mapper import assess_light_window
from .anomaly_detector import detect_anomaly


# ============================================================
# SECTION 1 — Data Preparation
# ============================================================

def prepare_readings(raw_readings: list[dict]) -> list[dict]:
    """
    Validates and normalises raw readings from MongoDB.
    Discards any reading missing temperature, light, or timestamp.

    Args:
        raw_readings: List of dicts from mongo_client.fetch_recent_readings()

    Returns:
        Cleaned list of dicts with guaranteed keys:
        { 'temperature': float, 'light': str, 'timestamp': datetime }
    """
    cleaned = []

    for r in raw_readings:
        temp = r.get("temperature")
        light = r.get("light")
        ts = r.get("timestamp")

        # Skip incomplete readings
        if temp is None or light is None or ts is None:
            continue

        # Ensure timestamp is a timezone-aware datetime
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        cleaned.append({
            "temperature": float(temp),
            "light": str(light),
            "timestamp": ts,
        })

    return cleaned


# ============================================================
# SECTION 2 — Trend Analysis
# ============================================================

def calculate_trend(readings: list[dict]) -> dict:
    """
    Calculates the temperature trend across the reading window using
    simple linear regression (least squares slope).

    Why linear regression instead of just first-vs-last?
    A single noisy reading at either end would skew a simple delta.
    Regression uses ALL readings, giving a more reliable rate.

    Args:
        readings: Prepared list of reading dicts (oldest → newest)

    Returns a dict with:
        - rate_per_minute   : °C change per minute (negative = cooling)
        - total_change      : total °C change across the window
        - direction         : 'dropping', 'rising', or 'stable'
        - window_minutes    : time span of the window in minutes
        - temps             : raw temp list (for downstream use)
    """
    if len(readings) < 2:
        return {
            "rate_per_minute": 0.0,
            "total_change": 0.0,
            "direction": "stable",
            "window_minutes": 0.0,
            "temps": [r["temperature"] for r in readings],
        }

    temps = [r["temperature"] for r in readings]
    timestamps = [r["timestamp"] for r in readings]

    # Convert timestamps to elapsed minutes from the first reading
    t0 = timestamps[0]
    elapsed = [(ts - t0).total_seconds() / 60.0 for ts in timestamps]

    # --- Linear regression (least squares slope) ---
    n = len(elapsed)
    sum_x  = sum(elapsed)
    sum_y  = sum(temps)
    sum_xy = sum(elapsed[i] * temps[i] for i in range(n))
    sum_x2 = sum(x ** 2 for x in elapsed)

    denominator = (n * sum_x2) - (sum_x ** 2)

    if denominator == 0:
        rate = 0.0
    else:
        rate = (n * sum_xy - sum_x * sum_y) / denominator  # °C per minute

    total_change = temps[-1] - temps[0]
    window_minutes = elapsed[-1]

    if rate < -TEMP_CHANGE_RATE_THRESHOLD:
        direction = "dropping"
    elif rate > TEMP_CHANGE_RATE_THRESHOLD:
        direction = "rising"
    else:
        direction = "stable"
 
    return {
        "rate_per_minute": round(rate, 4),
        "total_change": round(total_change, 3),
        "direction": direction,
        "window_minutes": round(window_minutes, 1),
        "temps": temps,
    }


# ============================================================
# SECTION 3 — Prediction Engine
# ============================================================

def predict_time_to_unsafe(
    current_temp: float,
    rate_per_minute: float,
    safe_min: float,
    safe_max: float,
) -> dict:
    """
    Given the current temperature and rate of change, predicts
    how many minutes until the temperature exits the safe range.

    Args:
        current_temp    : latest temperature reading (°C)
        rate_per_minute : °C change per minute from trend analysis
        safe_min        : tank-specific minimum safe temperature (°C)
        safe_max        : tank-specific maximum safe temperature (°C)

    Returns a dict with:
        - is_already_unsafe     : True if current temp is already outside range
        - predicted_breach_min  : minutes until unsafe (None if not predicted)
        - breach_direction      : 'too_cold', 'too_hot', or None
        - current_temp          : passed through for convenience
    """
    # Already outside safe range?
    if current_temp < safe_min:
        return {
            "is_already_unsafe": True,
            "predicted_breach_min": 0,
            "breach_direction": "too_cold",
            "current_temp": current_temp,
        }
    if current_temp > safe_max:
        return {
            "is_already_unsafe": True,
            "predicted_breach_min": 0,
            "breach_direction": "too_hot",
            "current_temp": current_temp,
        }

    # Temperature is stable — no prediction needed
    if abs(rate_per_minute) <= TEMP_CHANGE_RATE_THRESHOLD:
        return {
            "is_already_unsafe": False,
            "predicted_breach_min": None,
            "breach_direction": None,
            "current_temp": current_temp,
        }

    # Cooling → predict time to hit safe_min
    if rate_per_minute < 0:
        degrees_to_breach = current_temp - safe_min
        minutes = degrees_to_breach / abs(rate_per_minute)
        return {
            "is_already_unsafe": False,
            "predicted_breach_min": round(minutes, 1),
            "breach_direction": "too_cold",
            "current_temp": current_temp,
        }

    # Heating → predict time to hit safe_max
    if rate_per_minute > 0:
        degrees_to_breach = safe_max - current_temp
        minutes = degrees_to_breach / rate_per_minute
        return {
            "is_already_unsafe": False,
            "predicted_breach_min": round(minutes, 1),
            "breach_direction": "too_hot",
            "current_temp": current_temp,
        }

    # Fallback (should never reach here)
    return {
        "is_already_unsafe": False,
        "predicted_breach_min": None,
        "breach_direction": None,
        "current_temp": current_temp,
    }


# ============================================================
# SECTION 4 — Diagnosis & Output
# ============================================================

def diagnose_cause(trend: dict, light_assessment: dict) -> str:
    """
    Cross-references temperature trend with light window assessment
    to determine the most likely cause of abnormal temperature change.

    Logic:
        Temp dropping + light stable   → heater likely failing
        Temp dropping + light shifting → environmental cooling (evening/AC)
        Temp rising   + light stable   → possible heater malfunction (overheating)
        Temp rising   + light shifting → environmental warming (direct sunlight etc.)
        Stable                         → no issue

    Returns a human-readable cause string.
    """
    direction = trend["direction"]
    is_stable = light_assessment["is_stable"]
    is_shifting = light_assessment["is_shifting"]
    dominant = light_assessment["dominant_category"]

    if direction == "stable":
        return "Temperature is stable. No action needed."

    if direction == "dropping":
        if is_stable:
            return (
                f"Temperature is dropping despite stable lighting ({dominant}) — "
                "possible heater malfunction."
            )
        if is_shifting:
            return (
                f"Temperature is dropping alongside a light shift ({dominant}) — "
                "likely environmental cooling (evening cycle or room temperature drop)."
            )
        return (
            f"Temperature is dropping. Light conditions are mixed ({dominant}) — "
            "cause unclear; monitor closely."
        )

    if direction == "rising":
        if is_stable:
            return (
                f"Temperature is rising despite stable lighting ({dominant}) — "
                "possible heater overheating or thermostat fault."
            )
        if is_shifting:
            return (
                f"Temperature is rising alongside a light shift ({dominant}) — "
                "likely environmental warming (direct sunlight or room heat)."
            )
        return (
            f"Temperature is rising. Light conditions are mixed ({dominant}) — "
            "cause unclear; monitor closely."
        )

    return "Unable to determine cause."


def generate_insight(tank_id: str, readings: list[dict], historical_readings: list[dict], safe_min: float, safe_max: float) -> dict:
    """
    Master function — orchestrates all sections and produces
    the final structured insight for Insight 1.

    Args:
        tank_id             : e.g. 'tank_1'
        readings            : raw readings list from mongo_client.fetch_recent_readings()
        historical_readings : 7-day baseline from mongo_client.fetch_historical_readings()
        safe_min            : tank-specific minimum safe temperature (°C) from tank_config
        safe_max            : tank-specific maximum safe temperature (°C) from tank_config

    Returns a dict with:
        - tank_id
        - status        : 'alert' | 'warning' | 'anomaly' | 'normal' | 'insufficient_data'
        - message       : human-readable insight string (the main output)
        - trend         : trend analysis dict
        - prediction    : prediction dict
        - light         : light assessment dict
        - anomaly       : anomaly detection result dict
        - generated_at  : UTC timestamp of when insight was generated
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    # --- Prepare ---
    readings = prepare_readings(readings)

    if len(readings) < 2:
        return {
            "tank_id": tank_id,
            "status": "insufficient_data",
            "message": "Not enough readings to generate a temperature insight. Waiting for more data.",
            "trend": None,
            "prediction": None,
            "light": None,
            "generated_at": generated_at,
        }

    # --- Analyse ---
    trend = calculate_trend(readings)
    light_readings = [r["light"] for r in readings]
    light_assessment = assess_light_window(light_readings)
    current_temp = readings[-1]["temperature"]
    prediction = predict_time_to_unsafe(current_temp, trend["rate_per_minute"], safe_min, safe_max)
    cause = diagnose_cause(trend, light_assessment)
    anomaly = detect_anomaly(readings, historical_readings)

    # --- Determine status ---
    # Priority: alert > warning > anomaly > normal
    if prediction["is_already_unsafe"]:
        status = "alert"
    elif (
        prediction["predicted_breach_min"] is not None
        and prediction["predicted_breach_min"] <= PREDICTION_ALERT_WINDOW_MINUTES
    ):
        status = "warning"
    elif anomaly["is_anomaly"]:
        status = "anomaly"
    else:
        status = "normal"

    # --- Build human-readable message ---
    message = _build_message(status, current_temp, trend, prediction, cause, anomaly)

    return {
        "tank_id": tank_id,
        "status": status,
        "message": message,
        "trend": trend,
        "prediction": prediction,
        "light": light_assessment,
        "anomaly": anomaly,
        "generated_at": generated_at,
    }


def _build_message(
    status: str,
    current_temp: float,
    trend: dict,
    prediction: dict,
    cause: str,
    anomaly: dict,
) -> str:
    """
    Constructs the final natural-language insight message.

    Examples:
        "Temperature will drop below the safe level in 35 minutes
         despite stable lighting — possible heater malfunction."

        "Temperature is currently 23.1°C — already below the safe minimum.
         Stable lighting suggests heater failure."

        "Temperature is stable at 26.2°C. No issues detected."

        "Temperature (26.2°C) is within the safe range but behaving unusually
         for this time of day. Monitor closely."
    """
    temp_str = f"{current_temp:.1f}°C"
    rate_str = f"{abs(trend['rate_per_minute']):.3f}°C/min"

    if status == "alert":
        direction_word = "below the safe minimum" if prediction["breach_direction"] == "too_cold" else "above the safe maximum"
        return (
            f"⚠️  ALERT: Tank temperature is currently {temp_str} — already {direction_word}. "
            f"{cause}"
        )

    if status == "warning":
        mins = prediction["predicted_breach_min"]
        direction_word = "drop below" if prediction["breach_direction"] == "too_cold" else "rise above"
        return (
            f"⚠️  WARNING: Temperature ({temp_str}) will {direction_word} the safe level "
            f"in approximately {mins:.0f} minutes at current rate ({rate_str}). "
            f"{cause}"
        )

    if status == "anomaly":
        reason_text = (
            anomaly["reason"].replace("_", " ")
            if anomaly.get("reason")
            else "unusual behaviour detected"
        )
        flagged = anomaly.get("anomaly_count", 0)
        return (
            f"🔍  ANOMALY: Temperature ({temp_str}) is within the safe range but "
            f"{reason_text} ({flagged} of {len(trend['temps'])} readings flagged). "
            f"Monitor closely — this may be an early sign of a developing issue."
        )

    if status == "normal" and trend["direction"] != "stable":
        return (
            f"Temperature is {temp_str} and {trend['direction']} at {rate_str}, "
            f"but remains within the safe range. {cause}"
        )

    return f"✅  Temperature is stable at {temp_str}. No issues detected."