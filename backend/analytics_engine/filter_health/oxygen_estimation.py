import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from pymongo import MongoClient


@dataclass
class OxygenEstimate:
    estimated_do_mgL: float
    oxygen_status: str
    oxygen_risk_score: float


# STEP 1 — Baseline oxygen from temperature -----------------------------------------------------

def baseline_oxygen_from_temperature(temperature_c: float) -> float:
    """Estimate dissolved oxygen saturation (mg/L) from temperature.

    Uses a polynomial approximation for DO saturation at 1 atm.
    Colder water holds more oxygen, hotter water holds less.
    """

    # Polynomial approximation: DO_sat(T) ≈ a + bT + cT^2 + dT^3
    # Coefficients chosen to be realistic for 0–35 °C range.
    t = temperature_c
    do_sat = (
        14.652
        - 0.41022 * t
        + 0.007991 * t * t
        - 0.000077774 * t * t * t
    )
    return max(do_sat, 0.0)


# STEP 2 — Turbidity-based oxygen penalty -------------------------------------------------------

def turbidity_penalty(turbidity: float) -> float:
    """Map turbidity to an oxygen reduction penalty (mg/L).

    Higher turbidity => more organic matter / particles => higher oxygen demand.
    """

    if turbidity is None:
        return 0.0

    # Simple piecewise mapping; adjust thresholds based on your real data.
    if turbidity <= 5:
        return 0.0  # crystal / very clear
    elif turbidity <= 25:
        return 0.5  # slightly cloudy
    elif turbidity <= 50:
        return 1.0  # cloudy
    elif turbidity <= 100:
        return 1.8  # very cloudy
    else:
        return 2.5  # dirty


# STEP 3 — Optional TDS-based adjustment --------------------------------------------------------

def tds_penalty(tds: Optional[float]) -> float:
    """Small correction factor based on TDS.

    Higher TDS => slightly less oxygen availability.
    This effect is intentionally small compared to turbidity.
    """

    if tds is None:
        return 0.0

    # Use the provided TDS categories to define small penalties.
    # Very Low / Ideal: no penalty
    # Slightly High: small penalty
    # High: moderate penalty
    # Very High: highest (still smaller than turbidity effect)

    if tds < 150:
        return 0.0  # Very Low
    elif tds < 300:
        return 0.0  # Ideal
    elif tds < 500:
        return 0.2  # Slightly High
    elif tds < 800:
        return 0.5  # High
    else:
        return 1.0  # Very High


# STEP 4 — Combine into final oxygen estimate ---------------------------------------------------

def combine_oxygen_estimate(
    temperature_c: float,
    turbidity: float,
    tds: Optional[float] = None,
) -> float:
    """Combine baseline oxygen with turbidity and TDS penalties.

    estimated_do = baseline - turbidity_penalty - tds_penalty
    Value is clamped to >= 0.
    """

    base_do = baseline_oxygen_from_temperature(temperature_c)
    turb_pen = turbidity_penalty(turbidity)
    tds_pen = tds_penalty(tds)

    estimated_do = base_do - turb_pen - tds_pen
    return max(estimated_do, 0.0)


# STEP 5 — Oxygen status classification ---------------------------------------------------------

def classify_oxygen_status(estimated_do_mgL: float) -> str:
    """Classify oxygen level into discrete status labels.

    >= 6 mg/L  -> "Normal"
    4–6 mg/L   -> "Moderate Risk"
    < 4 mg/L   -> "Low Oxygen Risk"
    """

    if estimated_do_mgL >= 6.0:
        return "Normal"
    elif estimated_do_mgL >= 4.0:
        return "Moderate Risk"
    else:
        return "Low Oxygen Risk"


# STEP 6 — Optional risk score ------------------------------------------------------------------

def oxygen_risk_score(estimated_do_mgL: float) -> float:
    """Compute a normalized risk score (0–100).

    0 mg/L  -> 100% risk
    8 mg/L+ -> 0% risk

    Linearly interpolated in between and clamped to [0, 100].
    Higher oxygen => lower risk.
    """

    max_safe_do = 8.0
    # Risk fraction: 1.0 at 0 mg/L, 0.0 at >= max_safe_do
    frac = max(0.0, min(1.0, (max_safe_do - estimated_do_mgL) / max_safe_do))
    return frac * 100.0


# Convenience wrapper ---------------------------------------------------------------------------

def estimate_oxygen_from_values(
    temperature_c: float,
    turbidity: float,
    tds: Optional[float] = None,
) -> OxygenEstimate:
    """High-level helper to compute all oxygen outputs from raw sensor values."""

    est_do = combine_oxygen_estimate(temperature_c, turbidity, tds)
    status = classify_oxygen_status(est_do)
    risk = oxygen_risk_score(est_do)

    return OxygenEstimate(
        estimated_do_mgL=est_do,
        oxygen_status=status,
        oxygen_risk_score=risk,
    )


# MongoDB integration ---------------------------------------------------------------------------

def _get_mongo_collection():
    """Get MongoDB collection using the same env-based config as other modules."""

    load_dotenv()

    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "aquarium_db")
    coll_name = os.getenv("MONGO_COLLECTION", "measurements")

    client = MongoClient(uri)
    coll = client[db_name][coll_name]
    return coll


def estimate_oxygen_for_latest_reading(
    tank_id: Optional[str] = None,
) -> tuple[OxygenEstimate, Dict[str, Any]]:
    """Fetch the latest reading from MongoDB and compute oxygen estimate.

    Returns a tuple of (OxygenEstimate, raw_document_used).
    If tank_id is provided, it filters for that tank; otherwise uses all tanks.
    """

    coll = _get_mongo_collection()

    query: Dict[str, Any] = {}
    if tank_id is not None:
        query["tank_id"] = tank_id

    doc = coll.find_one(query, sort=[("timestamp", -1)])
    if not doc:
        raise RuntimeError("No readings found in MongoDB for the given query")

    temperature = float(doc.get("temperature"))
    turbidity = float(doc.get("turbidity"))
    tds_value = doc.get("tds")
    tds = float(tds_value) if tds_value is not None else None

    estimate = estimate_oxygen_from_values(temperature, turbidity, tds)
    return estimate, doc


if __name__ == "__main__":
    # Simple manual test: compute oxygen for the latest reading in the DB.
    est, raw = estimate_oxygen_for_latest_reading()
    print("Latest reading:", raw)
    print("Oxygen estimate:", est)
