from datetime import datetime, timezone
from statistics import mean, pstdev

from .settings import (
    PH_CHANGE_RATE_THRESHOLD,
    TDS_CHANGE_RATE_THRESHOLD,
    TEMP_CHANGE_RATE_THRESHOLD,
)


def prepare_readings(raw_readings: list[dict]) -> list[dict]:
    """
    Shared lightweight preparation for ML feature building.
    """
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


def _safe_std(values: list[float]) -> float:
    return 0.0 if len(values) < 2 else float(pstdev(values))


def _calculate_numeric_trend(readings: list[dict], field: str, threshold: float) -> dict:
    """
    Same logic as your rule engine trend calculation, reused for ML features.
    """
    if not readings:
        return {
            "current": 0.0,
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
            "current": values[-1],
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
        "current": float(values[-1]),
        "rate_per_minute": float(rate),
        "total_change": float(total_change),
        "direction": direction,
        "window_minutes": float(window_minutes),
        "values": values,
    }


def build_feature_dict(readings: list[dict]) -> dict:
    """
    Converts a recent window of readings into one ML feature dictionary.
    """
    readings = prepare_readings(readings)
    if len(readings) < 2:
        raise ValueError("Need at least 2 readings to build features.")

    ph_values = [r["ph"] for r in readings]
    tds_values = [r["tds"] for r in readings]
    temp_values = [r["temperature"] for r in readings]

    ph_trend = _calculate_numeric_trend(readings, "ph", PH_CHANGE_RATE_THRESHOLD)
    tds_trend = _calculate_numeric_trend(readings, "tds", TDS_CHANGE_RATE_THRESHOLD)
    temp_trend = _calculate_numeric_trend(readings, "temperature", TEMP_CHANGE_RATE_THRESHOLD)

    current_ph = ph_values[-1]
    current_tds = tds_values[-1]
    current_temp = temp_values[-1]

    ph_mean = mean(ph_values)
    tds_mean = mean(tds_values)
    temp_mean = mean(temp_values)

    features = {
        "current_ph": current_ph,
        "current_tds": current_tds,
        "current_temp": current_temp,

        "ph_mean": ph_mean,
        "tds_mean": tds_mean,
        "temp_mean": temp_mean,

        "ph_std": _safe_std(ph_values),
        "tds_std": _safe_std(tds_values),
        "temp_std": _safe_std(temp_values),

        "ph_min": min(ph_values),
        "ph_max": max(ph_values),
        "tds_min": min(tds_values),
        "tds_max": max(tds_values),
        "temp_min": min(temp_values),
        "temp_max": max(temp_values),

        "ph_slope": ph_trend["rate_per_minute"],
        "tds_slope": tds_trend["rate_per_minute"],
        "temp_slope": temp_trend["rate_per_minute"],

        "ph_total_change": ph_trend["total_change"],
        "tds_total_change": tds_trend["total_change"],
        "temp_total_change": temp_trend["total_change"],

        "window_minutes": ph_trend["window_minutes"],

        "ph_tds_ratio": current_ph / current_tds if current_tds != 0 else 0.0,
        "temp_tds_interaction": current_temp * current_tds,
        "ph_temp_interaction": current_ph * current_temp,
    }

    return features


FEATURE_COLUMNS = [
    "current_ph",
    "current_tds",
    "current_temp",
    "ph_mean",
    "tds_mean",
    "temp_mean",
    "ph_std",
    "tds_std",
    "temp_std",
    "ph_min",
    "ph_max",
    "tds_min",
    "tds_max",
    "temp_min",
    "temp_max",
    "ph_slope",
    "tds_slope",
    "temp_slope",
    "ph_total_change",
    "tds_total_change",
    "temp_total_change",
    "window_minutes",
    "ph_tds_ratio",
    "temp_tds_interaction",
    "ph_temp_interaction",
]


def feature_dict_to_row(feature_dict: dict) -> list[float]:
    return [float(feature_dict[col]) for col in FEATURE_COLUMNS]