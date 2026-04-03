def clean_sensor_data(data, last_good_values):
    """
    Clean one sensor record using in-memory last good numeric values.

    Uses real-world ranges for aquarium sensors.
    """

    # Temperature (°C) — realistic aquarium range
    if data["temperature"] < 0 or data["temperature"] > 40:
        data["temperature"] = last_good_values.get("temperature", 25.0)

    # pH (0–14 valid range)
    if data["ph"] < 0 or data["ph"] > 14:
        data["ph"] = last_good_values.get("ph", 7.2)

    # Turbidity (NTU) — must be >= 0
    if data["turbidity"] < 0:
        data["turbidity"] = last_good_values.get("turbidity", 3.0)

    # TDS (ppm) — realistic upper safe bound
    if data["tds"] < 0 or data["tds"] > 2000:
        data["tds"] = last_good_values.get("tds", 300.0)

    # Light (lux) — must be >= 0
    if data["light"] < 0:
        data["light"] = last_good_values.get("light", 200.0)

    # Update in-memory last good values after cleaning
    last_good_values["temperature"] = data["temperature"]
    last_good_values["ph"] = data["ph"]
    last_good_values["turbidity"] = data["turbidity"]
    last_good_values["tds"] = data["tds"]
    last_good_values["light"] = data["light"]

    return data