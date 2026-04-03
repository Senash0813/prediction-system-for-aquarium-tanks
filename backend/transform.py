from datetime import datetime, timezone


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
    if raw >= 3000:
        return "Crystal Clear"
    elif raw >= 2500:
        return "Very Clear"
    elif raw >= 2000:
        return "Normal"
    elif raw >= 1500:
        return "Cloudy"
    else:
        return "Dirty"


def transform_sensor_data(data):
    data["ingestion_time"] = datetime.now(timezone.utc)
    data["sampling_interval"] = 1

    # Replace raw numerical values with categorical labels
    data["light"] = categorize_light(data["light"])
    data["turbidity"] = categorize_turbidity(data["turbidity"])

    return data