from datetime import datetime
from zoneinfo import ZoneInfo

SL_TIMEZONE = ZoneInfo("Asia/Colombo")


def categorize_light(lux):
    if lux is None:
        return None
    if lux < 50:
        return "Night Mode"
    elif lux < 500:
        return "Dim Light"
    elif lux < 2000:
        return "Low Light"
    elif lux < 5000:
        return "Ideal for Fish"
    elif lux < 10000:
        return "Great for Plants"
    else:
        return "Too Bright"


def categorize_turbidity(raw):
    if raw is None:
        return None
    if raw <= 1:
        return "Crystal Clear"
    elif raw <= 5:
        return "Very Clear"
    elif raw <= 10:
        return "Clear"
    elif raw <= 25:
        return "Slightly Cloudy"
    elif raw <= 50:
        return "Cloudy"
    elif raw <= 100:
        return "Very Cloudy"
    else:
        return "Dirty"


def categorize_tds(tds):
    if tds is None:
        return None
    if tds < 150:
        return "Very Low"
    elif tds < 300:
        return "Ideal"
    elif tds < 500:
        return "Slightly High"
    elif tds < 800:
        return "High"
    else:
        return "Very High"


def transform_sensor_data(data, sampling_interval_minutes):
    data["ingestion_time"] = datetime.now(SL_TIMEZONE)
    data["sampling_interval"] = sampling_interval_minutes

    # Replace numeric values with category labels
    data["light"] = categorize_light(data["light"])
    data["turbidity"] = categorize_turbidity(data["turbidity"])
    data["tds"] = categorize_tds(data["tds"])

    return data