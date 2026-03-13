def get_last_good_value(collection, field):
    """
    Queries MongoDB for the most recent document where the given field is not None.
    Returns the value if found, otherwise returns None.
    """
    last_doc = collection.find_one(
        {field: {"$ne": None}},
        sort=[("timestamp", -1)]
    )
    if last_doc:
        return last_doc.get(field)
    return None


def clean_sensor_data(data, collection):

    # Temperature validation (-10°C to 80°C)
    if data["temperature"] < -10 or data["temperature"] > 80:
        data["temperature"] = get_last_good_value(collection, "temperature")

    # pH validation (0 to 14)
    if data["ph"] < 0 or data["ph"] > 14:
        data["ph"] = get_last_good_value(collection, "ph")

    # Turbidity validation (must be non-negative)
    if data["turbidity"] < 0:
        data["turbidity"] = get_last_good_value(collection, "turbidity")

    # TDS validation (0 to 5000 ppm)
    if data["tds"] < 0 or data["tds"] > 5000:
        data["tds"] = get_last_good_value(collection, "tds")

    # Light validation (must be non-negative)
    if data["light"] < 0:
        data["light"] = get_last_good_value(collection, "light")

    return data

