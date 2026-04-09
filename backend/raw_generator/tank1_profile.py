import random
from datetime import datetime, timedelta


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def get_hour_fraction(timestamp: datetime) -> float:
    return timestamp.hour + (timestamp.minute / 60)


class Tank1Simulator:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)

        # Core sensor state
        self.temperature = 25.6
        self.ph = 7.3
        self.turbidity = 1.8   # NTU
        self.tds = 275.0       # ppm

        # Internal tank state
        self.filter_efficiency = 1.0
        self.organic_load = 0.10

        self.day_weather = {}
        self.day_light_mode = {}

        # Device states
        self.heater_on = True
        self.filter_on = True

        # Failure windows
        self.heater_failure_start = None
        self.heater_failure_end = None
        self.filter_failure_start = None
        self.filter_failure_end = None

        # Power cut windows
        self.power_cut_windows = []

        self.start_timestamp = None

    def _choose_daily_weather(self, date_key):
        if date_key not in self.day_weather:
            roll = self.rng.random()
            if roll < 0.50:
                self.day_weather[date_key] = "sunny"
            elif roll < 0.82:
                self.day_weather[date_key] = "cloudy"
            else:
                self.day_weather[date_key] = "rainy"
        return self.day_weather[date_key]

    def _choose_daily_light_mode(self, date_key):
        """
        normal      -> regular aquarium lighting
        extended    -> light remains on longer at night
        dim_night   -> decorative dim night lighting
        """
        if date_key not in self.day_light_mode:
            roll = self.rng.random()
            if roll < 0.65:
                self.day_light_mode[date_key] = "normal"
            elif roll < 0.88:
                self.day_light_mode[date_key] = "extended"
            else:
                self.day_light_mode[date_key] = "dim_night"
        return self.day_light_mode[date_key]

    def _schedule_events_if_needed(self, timestamp: datetime):
        if self.start_timestamp is None:
            self.start_timestamp = timestamp

            # Heater failure in week 2
            heater_day_offset = self.rng.randint(7, 13)
            heater_hour = self.rng.randint(1, 5)
            heater_duration_hours = self.rng.randint(8, 16)

            self.heater_failure_start = (
                self.start_timestamp + timedelta(days=heater_day_offset)
            ).replace(hour=heater_hour, minute=0, second=0, microsecond=0)
            self.heater_failure_end = self.heater_failure_start + timedelta(
                hours=heater_duration_hours
            )

            # Filter failure in later period so dirt becomes visible
            filter_day_offset = self.rng.randint(13, 19)
            filter_hour = self.rng.randint(8, 14)
            filter_duration_hours = self.rng.randint(18, 42)

            self.filter_failure_start = (
                self.start_timestamp + timedelta(days=filter_day_offset)
            ).replace(hour=filter_hour, minute=0, second=0, microsecond=0)
            self.filter_failure_end = self.filter_failure_start + timedelta(
                hours=filter_duration_hours
            )

            # 3 to 6 power cuts across 3 weeks
            power_cut_count = self.rng.randint(3, 6)
            for _ in range(power_cut_count):
                day_offset = self.rng.randint(0, 20)
                if self.rng.random() < 0.6:
                    start_hour = self.rng.randint(18, 23)
                else:
                    start_hour = self.rng.randint(6, 16)

                duration_minutes = self.rng.randint(30, 240)

                start_dt = (
                    self.start_timestamp + timedelta(days=day_offset)
                ).replace(hour=start_hour, minute=0, second=0, microsecond=0)
                end_dt = start_dt + timedelta(minutes=duration_minutes)
                self.power_cut_windows.append((start_dt, end_dt))

    def _is_power_cut(self, timestamp: datetime):
        for start_dt, end_dt in self.power_cut_windows:
            if start_dt <= timestamp < end_dt:
                return True
        return False

    def _update_device_status(self, timestamp: datetime):
        power_cut = self._is_power_cut(timestamp)

        self.heater_on = (not power_cut) and not (
            self.heater_failure_start <= timestamp < self.heater_failure_end
        )
        self.filter_on = (not power_cut) and not (
            self.filter_failure_start <= timestamp < self.filter_failure_end
        )

    def _light_profile(self, timestamp: datetime, weather: str):
        """
        Total light = ambient daylight + artificial tank light.
        Includes some nights with strong tank light and some low-light nights.
        """
        hour = get_hour_fraction(timestamp)
        light_mode = self._choose_daily_light_mode(timestamp.date())
        power_cut = self._is_power_cut(timestamp)

        # Ambient environmental light
        if 0 <= hour < 5:
            ambient_light = self.rng.uniform(0, 5)
        elif 5 <= hour < 7:
            ambient_light = self.rng.uniform(15, 120)
        elif 7 <= hour < 17:
            ambient_light = self.rng.uniform(120, 850)
        elif 17 <= hour < 19:
            ambient_light = self.rng.uniform(30, 180)
        else:
            ambient_light = self.rng.uniform(0, 20)

        if 7 <= hour <= 18:
            if weather == "sunny":
                ambient_light *= self.rng.uniform(1.00, 1.18)
            elif weather == "cloudy":
                ambient_light *= self.rng.uniform(0.70, 0.92)
            else:
                ambient_light *= self.rng.uniform(0.45, 0.75)

        # Artificial tank light
        tank_light = 0.0

        if not power_cut:
            if 8 <= hour < 18:
                tank_light = self.rng.uniform(1000, 2400)
            elif light_mode == "extended" and 18 <= hour < 23:
                tank_light = self.rng.uniform(500, 1600)
            elif light_mode == "dim_night" and (19 <= hour < 23 or 5 <= hour < 6):
                tank_light = self.rng.uniform(80, 350)
            elif light_mode == "normal" and 19 <= hour < 21 and self.rng.random() < 0.30:
                tank_light = self.rng.uniform(60, 260)

        total_light = ambient_light + tank_light
        return round(clamp(total_light, 0, 5000), 2)

    def _is_feeding_time(self, timestamp: datetime):
        hour = timestamp.hour
        minute = timestamp.minute
        return (
            (hour == 8 and minute <= 30) or
            (hour == 18 and minute <= 30)
        )

    def _is_water_change_time(self, timestamp: datetime):
        """
        Less frequent maintenance so the tank can get visibly dirty.
        Every 10 days around 10 AM.
        """
        days_since_start = (timestamp.date() - self.start_timestamp.date()).days
        return days_since_start > 0 and days_since_start % 10 == 0 and timestamp.hour == 10

    def generate_reading(self, timestamp: datetime) -> dict:
        self._schedule_events_if_needed(timestamp)
        self._update_device_status(timestamp)

        weather = self._choose_daily_weather(timestamp.date())
        feeding_event = self._is_feeding_time(timestamp)
        water_change_event = self._is_water_change_time(timestamp)
        power_cut = self._is_power_cut(timestamp)

        hour = get_hour_fraction(timestamp)
        days_since_start = (timestamp.date() - self.start_timestamp.date()).days

        # -----------------------------------
        # LIGHT (lux)
        # -----------------------------------
        light = self._light_profile(timestamp, weather)

        # -----------------------------------
        # ORGANIC LOAD
        # -----------------------------------
        # Stronger buildup over the 3 weeks
        if days_since_start < 7:
            self.organic_load += self.rng.uniform(0.0008, 0.0018)
        elif days_since_start < 14:
            self.organic_load += self.rng.uniform(0.0018, 0.0035)
        else:
            self.organic_load += self.rng.uniform(0.0030, 0.0055)

        if feeding_event:
            self.organic_load += self.rng.uniform(0.04, 0.09)

        # Filter degrades over time
        self.filter_efficiency -= self.rng.uniform(0.0005, 0.0011)
        self.filter_efficiency = clamp(self.filter_efficiency, 0.25, 1.0)

        # Cleanup effect if filter works
        if self.filter_on:
            cleanup = 0.004 + (0.009 * self.filter_efficiency)
            self.organic_load = max(0.08, self.organic_load - cleanup)
        else:
            self.organic_load += self.rng.uniform(0.020, 0.045)

        # Water change reduces load, but not to perfect condition
        if water_change_event:
            self.organic_load *= self.rng.uniform(0.50, 0.72)
            self.tds *= self.rng.uniform(0.86, 0.94)
            self.ph += self.rng.uniform(0.05, 0.12)
            self.filter_efficiency = min(1.0, self.filter_efficiency + self.rng.uniform(0.08, 0.16))

        self.organic_load = clamp(self.organic_load, 0.08, 3.0)

        # -----------------------------------
        # TEMPERATURE (°C)
        # -----------------------------------
        ambient_base = 26.1 if 10 <= hour <= 17 else 24.6

        if weather == "sunny":
            ambient_base += 0.45
        elif weather == "rainy":
            ambient_base -= 0.35

        if self.heater_on:
            heater_correction = (25.8 - self.temperature) * 0.42
            ambient_influence = (ambient_base - self.temperature) * 0.09
            noise = self.rng.gauss(0, 0.06)
            self.temperature += heater_correction + ambient_influence + noise
        else:
            # Stronger visible cooling when heater fails / power cut occurs
            ambient_influence = (ambient_base - 1.8 - self.temperature) * 0.24
            noise = self.rng.gauss(0, 0.10)
            self.temperature += ambient_influence + noise

        # Recovery spike after heater returns
        if self.heater_failure_end and self.heater_failure_end <= timestamp < self.heater_failure_end + timedelta(hours=3):
            self.temperature += self.rng.uniform(0.08, 0.25)

        if power_cut and not self.heater_on:
            self.temperature -= self.rng.uniform(0.01, 0.05)

        self.temperature = round(clamp(self.temperature, 20.0, 31.0), 2)

        # -----------------------------------
        # TURBIDITY (NTU)
        # -----------------------------------
        turbidity_base = 0.8 + (self.organic_load * 11.5)

        if feeding_event:
            turbidity_base += self.rng.uniform(5.0, 12.0)

        turbidity_base += (1.0 - self.filter_efficiency) * 24.0

        if not self.filter_on:
            turbidity_base += self.rng.uniform(18.0, 40.0)

        if days_since_start >= 14:
            turbidity_base += self.rng.uniform(6.0, 15.0)

        turbidity_noise = self.rng.gauss(0, 1.5)
        self.turbidity = round(clamp(turbidity_base + turbidity_noise, 0.2, 140.0), 2)

        # -----------------------------------
        # TDS (ppm)
        # -----------------------------------
        self.tds += self.rng.uniform(0.05, 0.18)

        if feeding_event:
            self.tds += self.rng.uniform(2.0, 5.0)

        if not self.filter_on:
            self.tds += self.rng.uniform(0.5, 1.5)

        if days_since_start >= 14:
            self.tds += self.rng.uniform(0.25, 0.80)

        self.tds += self.rng.gauss(0, 0.8)
        self.tds = round(clamp(self.tds, 180.0, 800.0), 2)

        # -----------------------------------
        # pH
        # -----------------------------------
        ph_drift_down = self.organic_load * self.rng.uniform(0.004, 0.012)
        self.ph -= ph_drift_down

        if water_change_event:
            self.ph += self.rng.uniform(0.05, 0.12)

        if not self.filter_on:
            self.ph -= self.rng.uniform(0.005, 0.018)

        if days_since_start >= 14:
            self.ph -= self.rng.uniform(0.000, 0.012)

        self.ph += self.rng.gauss(0, 0.015)
        self.ph = round(clamp(self.ph, 6.0, 7.9), 2)

        raw_doc = {
            "tank_id": "tank_1",
            "temperature": self.temperature,
            "ph": self.ph,
            "turbidity": self.turbidity,
            "tds": self.tds,
            "light": light,
            "timestamp": timestamp,
            "processed": False
        }

        # Sensor anomalies for cleaning tests only
        anomaly_roll = self.rng.random()
        if anomaly_roll < 0.003:
            raw_doc["temperature"] = 120.0
        elif anomaly_roll < 0.006:
            raw_doc["ph"] = 20.0
        elif anomaly_roll < 0.009:
            raw_doc["turbidity"] = -5.0
        elif anomaly_roll < 0.012:
            raw_doc["tds"] = 7000.0
        elif anomaly_roll < 0.015:
            raw_doc["light"] = -100.0

        return raw_doc