def clean_sensor_data(data):

    # Temperature validation
    if data["temperature"] < -10 or data["temperature"] > 80:
        data["temperature"] = None

    # pH validation
    if data["ph"] < 0 or data["ph"] > 14:
        data["ph"] = None

    # Turbidity validation
    if data["turbidity"] < 0:
        data["turbidity"] = None

    # TDS validation
    if data["tds"] < 0 or data["tds"] > 5000:
        data["tds"] = None

    # Light validation
    if data["light"] < 0:
        data["light"] = None

    return data