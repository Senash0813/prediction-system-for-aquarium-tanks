def clean_sensor_data(data, last_good_values):
    """
    Clean one sensor record using in-memory last good numeric values.
    Uses realistic aquarium sensor bounds.
    """

    # Temperature (°C)
    if data["temperature"] < 0 or data["temperature"] > 40:
        data["temperature"] = last_good_values.get("temperature", 25.5)

    # pH
    if data["ph"] < 0 or data["ph"] > 14:
        data["ph"] = last_good_values.get("ph", 7.2)

    # Turbidity (NTU)
    if data["turbidity"] < 0:
        data["turbidity"] = last_good_values.get("turbidity", 2.5)

    # TDS (ppm)
    if data["tds"] < 0 or data["tds"] > 2000:
        data["tds"] = last_good_values.get("tds", 290.0)

    # Light (lux)
    if data["light"] < 0:
        data["light"] = last_good_values.get("light", 150.0)

    # Update memory
    last_good_values["temperature"] = data["temperature"]
    last_good_values["ph"] = data["ph"]
    last_good_values["turbidity"] = data["turbidity"]
    last_good_values["tds"] = data["tds"]
    last_good_values["light"] = data["light"]

    return data