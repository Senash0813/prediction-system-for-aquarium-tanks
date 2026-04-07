import pandas as pd


def classify_trend(rate_of_change: float, stable_threshold: float = 0.001) -> str:
    """
    Convert a numeric slope/rate into Rising / Falling / Stable.
    """
    if rate_of_change > stable_threshold:
        return "Rising"
    if rate_of_change < -stable_threshold:
        return "Falling"
    return "Stable"


def calculate_rate_of_change(series: pd.Series) -> float:
    """
    Simple rate of change using first and last values in the selected window.
    """
    clean_series = series.dropna()
    if len(clean_series) < 2:
        return 0.0

    first_value = clean_series.iloc[0]
    last_value = clean_series.iloc[-1]
    steps = len(clean_series) - 1

    if steps == 0:
        return 0.0

    return float((last_value - first_value) / steps)


def analyze_metric(df: pd.DataFrame, metric: str) -> dict:
    """
    Compute summary analytics for one numeric metric.
    """
    if df.empty:
        return {
            "metric": metric,
            "current": None,
            "average": None,
            "min": None,
            "max": None,
            "trend": "Unknown",
            "rate_of_change": None,
            "message": "No data available."
        }

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in DataFrame")

    series = pd.to_numeric(df[metric], errors="coerce").dropna()

    if series.empty:
        return {
            "metric": metric,
            "current": None,
            "average": None,
            "min": None,
            "max": None,
            "trend": "Unknown",
            "rate_of_change": None,
            "message": f"No valid numeric data for {metric}."
        }

    current = round(float(series.iloc[-1]), 2)
    average = round(float(series.mean()), 2)
    min_value = round(float(series.min()), 2)
    max_value = round(float(series.max()), 2)

    rate_of_change = round(calculate_rate_of_change(series), 4)
    trend = classify_trend(rate_of_change)

    message = (
        f"{metric} is currently {current}, with a {trend.lower()} trend "
        f"over the selected period."
    )

    return {
        "metric": metric,
        "current": current,
        "average": average,
        "min": min_value,
        "max": max_value,
        "trend": trend,
        "rate_of_change": rate_of_change,
        "message": message
    }