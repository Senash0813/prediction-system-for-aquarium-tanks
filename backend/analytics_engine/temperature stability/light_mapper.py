# utils/light_mapper.py

from settings import LIGHT_STABLE_CATEGORIES, LIGHT_SHIFT_CATEGORIES


# Maps each category to a numeric stability score used in diagnosis logic.
# 1.0 = fully stable (no environmental stress)
# 0.0 = significant environmental shift
LIGHT_STABILITY_SCORE = {
    "Night Mode":       0.0,
    "Dim Light":        0.3,
    "Low Light":        0.8,
    "Ideal for Fish":   1.0,
    "Great for Plants": 1.0,
    "Too Bright":       0.2,
}


def is_light_stable(light_category: str) -> bool:
    """Returns True if light indicates a stable environment."""
    return light_category in LIGHT_STABLE_CATEGORIES


def is_light_shifting(light_category: str) -> bool:
    """Returns True if light suggests environmental change (evening, AC, etc.)"""
    return light_category in LIGHT_SHIFT_CATEGORIES


def get_stability_score(light_category: str) -> float:
    """
    Returns a numeric stability score (0.0 - 1.0) for a light category.
    Used to detect gradual environmental drift across a window of readings.
    Returns 0.5 as a neutral default for unknown categories.
    """
    return LIGHT_STABILITY_SCORE.get(light_category, 0.5)


def assess_light_window(light_readings: list[str]) -> dict:
    """
    Analyses a window of light category readings and returns a summary.

    Args:
        light_readings: Ordered list of light category strings (oldest → newest)

    Returns a dict with:
        - dominant_category : most frequent category in the window
        - is_stable         : True if the window is predominantly stable
        - avg_stability     : average stability score across the window
        - is_shifting       : True if a meaningful shift is detected
    """
    if not light_readings:
        return {
            "dominant_category": None,
            "is_stable": False,
            "avg_stability": 0.5,
            "is_shifting": False,
        }

    scores = [get_stability_score(r) for r in light_readings]
    avg_stability = sum(scores) / len(scores)
    dominant_category = max(set(light_readings), key=light_readings.count)

    # Stable if average score is above 0.7
    is_stable = avg_stability >= 0.7

    # Shifting if the last 5 readings are all in shift categories
    # (catches gradual evening transitions, not just one-off readings)
    recent = light_readings[-5:] if len(light_readings) >= 5 else light_readings
    is_shifting = all(is_light_shifting(r) for r in recent)

    return {
        "dominant_category": dominant_category,
        "is_stable": is_stable,
        "avg_stability": round(avg_stability, 3),
        "is_shifting": is_shifting,
    }