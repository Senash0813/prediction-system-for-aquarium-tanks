import os
import time
import threading
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure


@dataclass
class OxygenEstimate:
    estimated_do_mg_l: float
    oxygen_status: str
    oxygen_risk_score: float


INSIGHTS_TTL_SECONDS = 7 * 24 * 60 * 60
MODERATE_RISK_LABEL = "Moderate Risk"
MONGO_READY_RETRIES = 3
MONGO_READY_DELAY_SECONDS = 2.0

_client = None
_oxygen_thread_lock = threading.Lock()
_oxygen_thread_started = False


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

def classify_oxygen_status(estimated_do_mg_l: float) -> str:
    """Classify oxygen level into discrete status labels.

    >= 6 mg/L  -> "Normal"
    4–6 mg/L   -> "Moderate Risk"
    < 4 mg/L   -> "Low Oxygen Risk"
    """

    if estimated_do_mg_l >= 6.0:
        return "Normal"
    elif estimated_do_mg_l >= 4.0:
        return MODERATE_RISK_LABEL
    else:
        return "Low Oxygen Risk"


# STEP 6 — Optional risk score ------------------------------------------------------------------

def oxygen_risk_score(estimated_do_mg_l: float) -> float:
    """Compute a normalized risk score (0–100).

    0 mg/L  -> 100% risk
    8 mg/L+ -> 0% risk

    Linearly interpolated in between and clamped to [0, 100].
    Higher oxygen => lower risk.
    """

    max_safe_do = 8.0
    # Risk fraction: 1.0 at 0 mg/L, 0.0 at >= max_safe_do
    frac = max(0.0, min(1.0, (max_safe_do - estimated_do_mg_l) / max_safe_do))
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
        estimated_do_mg_l=est_do,
        oxygen_status=status,
        oxygen_risk_score=risk,
    )


# MongoDB integration ---------------------------------------------------------------------------

def _load_environment() -> None:
    this_dir = Path(__file__).resolve().parent
    backend_dir = this_dir.parent.parent
    load_dotenv(backend_dir / ".env", override=False)
    load_dotenv(this_dir / ".env", override=False)
    load_dotenv()


def _get_client() -> MongoClient:
    global _client

    if _client is None:
        _load_environment()
        uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            retryWrites=True,
        )

    return _client


def _wait_for_mongo_ready() -> None:
    client = _get_client()

    last_error: Exception | None = None
    for attempt in range(1, MONGO_READY_RETRIES + 1):
        try:
            client.admin.command("ping")
            return
        except ConnectionFailure as exc:
            last_error = exc
            if attempt < MONGO_READY_RETRIES:
                time.sleep(MONGO_READY_DELAY_SECONDS)

    if last_error is not None:
        raise last_error


def _get_readings_db():
    _load_environment()
    db_name = os.getenv("MONGO_DB") or os.getenv("MONGODB_DB") or "aqua_gaurd_db"
    return _get_client()[db_name]


def _get_insights_db():
    _load_environment()
    insights_db_name = os.getenv("MONGO_INSIGHTS_DB", "generated_insights")
    return _get_client()[insights_db_name]


def _get_all_tank_ids(prefix: str = "tank_") -> list[str]:
    _wait_for_mongo_ready()

    db = _get_readings_db()
    collection_names = db.list_collection_names()
    return [name for name in collection_names if name.startswith(prefix) and name != "tank_config"]


def _get_latest_reading_collection(tank_id: Optional[str] = None):
    if tank_id is None:
        return _get_readings_db()[os.getenv("MONGO_COLLECTION", "measurements")]

    return _get_readings_db()[tank_id]


def _oxygen_status_key(oxygen_status: str) -> str:
    if oxygen_status == "Normal":
        return "normal"
    if oxygen_status == "Moderate Risk":
        return "moderate_risk"
    return "low_oxygen_risk"


def _oxygen_message(oxygen_status: str, estimated_do_mg_l: float, risk_score: float) -> str:
    value_text = f"{estimated_do_mg_l:.2f} mg/L"

    if oxygen_status == "Normal":
        return (
            f"Oxygen level is healthy. Estimated dissolved oxygen is {value_text}, "
            f"with a low risk score of {risk_score:.1f}."
        )

    if oxygen_status == MODERATE_RISK_LABEL:
        return (
            f"Moderate oxygen risk detected. Estimated dissolved oxygen is {value_text}, "
            f"so aeration and turbidity should be monitored. Risk score is {risk_score:.1f}."
        )

    return (
        f"Low oxygen risk detected. Estimated dissolved oxygen is {value_text}, "
        f"which may stress fish. Increase aeration or check water quality soon. "
        f"Risk score is {risk_score:.1f}."
    )


def _build_oxygen_insight(tank_id: str, estimate: OxygenEstimate, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    source_timestamp = raw_doc.get("timestamp")

    return {
        "insight_type": "oxygen_estimate",
        "generated_at": generated_at,
        "tank_id": tank_id,
        "status": _oxygen_status_key(estimate.oxygen_status),
        "message": _oxygen_message(
            estimate.oxygen_status,
            estimate.estimated_do_mg_l,
            estimate.oxygen_risk_score,
        ),
        "oxygen": {
            "estimated_do_mgL": estimate.estimated_do_mg_l,
            "oxygen_status": estimate.oxygen_status,
            "oxygen_risk_score": estimate.oxygen_risk_score,
        },
        "source": {
            "tank_collection": tank_id,
            "temperature": raw_doc.get("temperature"),
            "turbidity": raw_doc.get("turbidity"),
            "tds": raw_doc.get("tds"),
            "reading_timestamp": source_timestamp,
        },
    }


def _save_oxygen_insight(tank_id: str, insight: Dict[str, Any]) -> None:
    collection = _get_insights_db()[tank_id]

    collection.create_index(
        [("generated_at", ASCENDING)],
        expireAfterSeconds=INSIGHTS_TTL_SECONDS,
        name="ttl_7_days",
    )

    collection.insert_one(insight)


def _fetch_latest_reading(tank_id: Optional[str] = None) -> Dict[str, Any]:
    coll = _get_latest_reading_collection(tank_id)
    query: Dict[str, Any] = {}

    doc = coll.find_one(query, sort=[("timestamp", -1)])
    if not doc:
        if tank_id is None:
            raise RuntimeError("No readings found in MongoDB measurements collection")
        raise RuntimeError(f"No readings found in MongoDB for tank '{tank_id}'")

    return doc


def estimate_oxygen_for_latest_reading(
    tank_id: Optional[str] = None,
) -> tuple[OxygenEstimate, Dict[str, Any]]:
    """Fetch the latest reading from MongoDB and compute oxygen estimate.

    Returns a tuple of (OxygenEstimate, raw_document_used).
    If tank_id is provided, it filters for that tank; otherwise uses all tanks.
    """

    doc = _fetch_latest_reading(tank_id)

    temperature = float(doc.get("temperature"))
    turbidity = float(doc.get("turbidity"))
    tds_value = doc.get("tds")
    tds = float(tds_value) if tds_value is not None else None

    estimate = estimate_oxygen_from_values(temperature, turbidity, tds)
    return estimate, doc


def generate_oxygen_insights() -> Dict[str, Any]:
    """Generate oxygen insights for all tanks and store them in MongoDB."""

    try:
        tank_ids = _get_all_tank_ids(prefix="tank_")
    except ConnectionFailure as exc:
        return {
            "inserted_count": 0,
            "tanks": [],
            "skipped_tanks": [],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": f"MongoDB not ready: {exc}",
        }

    inserted_count = 0
    inserted_tanks: list[str] = []
    skipped_tanks: list[str] = []

    for tank_id in tank_ids:
        try:
            estimate, raw_doc = estimate_oxygen_for_latest_reading(tank_id)
            insight_doc = _build_oxygen_insight(tank_id, estimate, raw_doc)
            _save_oxygen_insight(tank_id, insight_doc)
            inserted_count += 1
            inserted_tanks.append(tank_id)
        except RuntimeError as exc:
            if "No readings found in MongoDB" in str(exc):
                skipped_tanks.append(tank_id)
                continue
            raise
        except (TypeError, ValueError) as exc:
            # Skip tanks with incomplete/invalid numeric fields (e.g., None values).
            if "float() argument must be a string or a real number" in str(exc):
                skipped_tanks.append(tank_id)
                continue
            raise

    return {
        "inserted_count": inserted_count,
        "tanks": inserted_tanks,
        "skipped_tanks": skipped_tanks,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def start_periodic_oxygen_insights(interval_seconds: float = 30.0) -> None:
    """Start a daemon thread that writes oxygen insights every interval_seconds."""

    global _oxygen_thread_started

    with _oxygen_thread_lock:
        if _oxygen_thread_started:
            return
        _oxygen_thread_started = True

    interval_seconds = max(1.0, float(interval_seconds))

    def _worker() -> None:
        while True:
            try:
                summary = generate_oxygen_insights()
                if summary.get("error"):
                    print(f"[oxygen] insight generation deferred: {summary['error']}")
                else:
                    print(
                        "[oxygen] insights pushed: "
                        f"count={summary['inserted_count']} "
                        f"tanks={summary['tanks']} "
                        f"at={summary['generated_at']}")
            except Exception as exc:
                if "float() argument must be a string or a real number" not in str(exc):
                    print(f"[oxygen] insight generation failed: {exc}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_worker, name="oxygen-insights", daemon=True)
    thread.start()
    print(
        "[oxygen] insight generation has started "
        f"(interval={interval_seconds}s, thread={thread.name})"
    )


def close_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


if __name__ == "__main__":
    summary = generate_oxygen_insights()
    print(summary)
