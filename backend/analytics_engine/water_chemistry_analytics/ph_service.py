import pandas as pd
from backend.analytics_engine.water_chemistry_analytics.mongo_loader import load_tank_data
from backend.analytics_engine.water_chemistry_analytics.metric_analytics import analyze_metric


def filter_last_hours(df: pd.DataFrame, hours: int) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df

    latest_time = df["timestamp"].max()
    cutoff = latest_time - pd.Timedelta(hours=hours)
    return df[df["timestamp"] >= cutoff].copy()


def filter_last_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df

    latest_time = df["timestamp"].max()
    cutoff = latest_time - pd.Timedelta(days=days)
    return df[df["timestamp"] >= cutoff].copy()


def get_ph_analysis(collection_name: str, range_type: str = "24h") -> dict:
    """
    Return pH analytics for a selected time window.
    range_type: 24h, 7d, 30d
    """
    df = load_tank_data(collection_name)

    if df.empty:
        return {
            "metric": "ph",
            "range": range_type,
            "message": "No data available."
        }

    if range_type == "24h":
        filtered_df = filter_last_hours(df, 24)
    elif range_type == "7d":
        filtered_df = filter_last_days(df, 7)
    elif range_type == "30d":
        filtered_df = filter_last_days(df, 30)
    else:
        raise ValueError("range_type must be one of: 24h, 7d, 30d")

    result = analyze_metric(filtered_df, "ph")
    result["range"] = range_type

    # Add chart-friendly points
    chart_df = filtered_df[["timestamp", "ph"]].copy()
    chart_df["timestamp"] = chart_df["timestamp"].dt.strftime("%H:%M")
    result["chart_points"] = chart_df.to_dict(orient="records")

    return result