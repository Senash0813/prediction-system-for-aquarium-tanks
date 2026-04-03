def clean_sensor_data(data, last_good_values):
    """
    Clean one sensor record using in-memory last good numeric values.

    If a value is invalid, replace it with the last known good value from memory.
    If there is no last good value yet, use a safe default.
    After cleaning, update memory with the current cleaned values.
    """

    # Temperature validation (-10°C to 80°C)
    if data["temperature"] < -10 or data["temperature"] > 80:
        data["temperature"] = last_good_values.get("temperature", 25.0)

    # pH validation (0 to 14)
    if data["ph"] < 0 or data["ph"] > 14:
        data["ph"] = last_good_values.get("ph", 7.2)

    # Turbidity validation (must be non-negative)
    if data["turbidity"] < 0:
        data["turbidity"] = last_good_values.get("turbidity", 2800.0)

    # TDS validation (0 to 5000 ppm)
    if data["tds"] < 0 or data["tds"] > 5000:
        data["tds"] = last_good_values.get("tds", 400.0)

    # Light validation (must be non-negative)
    if data["light"] < 0:
        data["light"] = last_good_values.get("light", 500.0)

    # Update in-memory last good values after cleaning
    last_good_values["temperature"] = data["temperature"]
    last_good_values["ph"] = data["ph"]
    last_good_values["turbidity"] = data["turbidity"]
    last_good_values["tds"] = data["tds"]
    last_good_values["light"] = data["light"]

    return data