import random
from datetime import datetime


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def get_hour_fraction(timestamp: datetime) -> float:
    return timestamp.hour + (timestamp.minute / 60)


def generate_tank1_sensor_reading(timestamp: datetime) -> dict:
    """
    Generate realistic RAW sensor data for tank_1.
    These values are inserted into raw_tank_1 first.
    Then your processing script will clean + transform them and store in tank_1.
    """

    hour = get_hour_fraction(timestamp)

    # Temperature: tropical aquarium range
    base_temp = 25.5
    if 10 <= hour <= 18:
        temp_shift = 0.6
    else:
        temp_shift = -0.2

    temperature = random.gauss(base_temp + temp_shift, 0.35)
    temperature = round(clamp(temperature, 24.0, 28.0), 2)

    # pH: slight natural fluctuation
    ph = random.gauss(7.4, 0.15)
    ph = round(clamp(ph, 6.9, 8.0), 2)

    # Turbidity: use higher raw scale because your transform.py expects big values
    # >=3000 -> Crystal Clear, >=2500 -> Very Clear, etc.
    turbidity = random.gauss(2800, 180)

    # around feeding times water gets slightly disturbed
    if 8 <= hour <= 9 or 18 <= hour <= 19:
        turbidity -= random.uniform(80, 220)

    turbidity = round(clamp(turbidity, 1600, 3300), 2)

    # TDS
    tds = random.gauss(420, 20)
    tds = round(clamp(tds, 360, 500), 2)

    # Light by time of day
    if 0 <= hour < 6:
        light = random.uniform(0, 25)
    elif 6 <= hour < 8:
        light = random.uniform(80, 350)
    elif 8 <= hour < 17:
        light = random.uniform(1000, 4500)
    elif 17 <= hour < 20:
        light = random.uniform(250, 1200)
    else:
        light = random.uniform(20, 120)

    light = round(light, 2)

    raw_doc = {
        "tank_id": "tank_1",
        "temperature": temperature,
        "ph": ph,
        "turbidity": turbidity,
        "tds": tds,
        "light": light,
        "timestamp": timestamp,
        "processed": False
    }

    # Small anomaly rate to test your cleaning.py
    # These invalid values should be corrected during processing
    anomaly_roll = random.random()

    if anomaly_roll < 0.02:
        raw_doc["temperature"] = 120.0
    elif anomaly_roll < 0.04:
        raw_doc["ph"] = 20.0
    elif anomaly_roll < 0.06:
        raw_doc["turbidity"] = -40.0
    elif anomaly_roll < 0.08:
        raw_doc["tds"] = 6500.0
    elif anomaly_roll < 0.10:
        raw_doc["light"] = -200.0

    return raw_doc