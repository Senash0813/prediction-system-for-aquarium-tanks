import random
from datetime import datetime


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def get_hour_fraction(timestamp: datetime) -> float:
    return timestamp.hour + (timestamp.minute / 60)


def generate_tank1_sensor_reading(timestamp: datetime) -> dict:
    """
    Generate realistic RAW sensor data for tank_1 using real-world units.

    Units:
    - temperature: Celsius
    - ph: pH scale
    - turbidity: NTU
    - tds: ppm
    - light: lux
    """

    hour = get_hour_fraction(timestamp)

    # Temperature (°C) - tropical freshwater aquarium
    base_temp = 25.5
    temp_shift = 0.4 if 10 <= hour <= 18 else -0.2
    temperature = random.gauss(base_temp + temp_shift, 0.3)
    temperature = round(clamp(temperature, 24.0, 27.5), 2)

    # pH - typical freshwater tropical aquarium
    ph = random.gauss(7.2, 0.15)
    ph = round(clamp(ph, 6.8, 7.8), 2)

    # Turbidity (NTU) - lower means clearer
    turbidity = random.gauss(3.0, 1.2)

    # Slight disturbance around feeding times
    if 8 <= hour <= 9 or 18 <= hour <= 19:
        turbidity += random.uniform(1.0, 4.0)

    turbidity = round(clamp(turbidity, 0.2, 20.0), 2)

    # TDS (ppm) - realistic freshwater aquarium range
    tds = random.gauss(320, 30)
    tds = round(clamp(tds, 200, 450), 2)

    # Light (lux) - simulate daily aquarium lighting
    if 0 <= hour < 6:
        light = random.uniform(0, 10)
    elif 6 <= hour < 8:
        light = random.uniform(50, 300)
    elif 8 <= hour < 17:
        light = random.uniform(800, 2500)
    elif 17 <= hour < 20:
        light = random.uniform(150, 800)
    else:
        light = random.uniform(0, 50)

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

    # Small anomaly rate to test cleaning.py
    anomaly_roll = random.random()

    if anomaly_roll < 0.02:
        raw_doc["temperature"] = 120.0   # invalid Celsius
    elif anomaly_roll < 0.04:
        raw_doc["ph"] = 20.0             # invalid pH
    elif anomaly_roll < 0.06:
        raw_doc["turbidity"] = -5.0      # invalid NTU
    elif anomaly_roll < 0.08:
        raw_doc["tds"] = 7000.0          # invalid ppm
    elif anomaly_roll < 0.10:
        raw_doc["light"] = -100.0        # invalid lux

    return raw_doc