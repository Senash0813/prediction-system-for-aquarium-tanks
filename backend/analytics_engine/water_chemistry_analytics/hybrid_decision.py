def combine_rule_and_ml(
    rule_status: str,
    rule_label: str,
    rule_severity: int,
    ml_prediction: dict,
    ml_anomaly: dict,
) -> dict:
    """
    Combines current rule-based output with ML future prediction and anomaly result.

    Rule engine remains source of truth for current state.
    ML can strengthen monitoring/warning but not downgrade obvious danger.
    """
    final_status = rule_status
    final_label = rule_label
    notes = []

    predicted_future_status = ml_prediction.get("predicted_future_status", "normal")
    is_anomalous = ml_anomaly.get("is_anomalous", False)

    # Never downgrade an alert from the rule engine
    if rule_status == "alert":
        notes.append("Current readings already look critical.")
        if is_anomalous:
            notes.append("Recent pattern also appears unusual.")
        return {
            "final_status": final_status,
            "final_label": final_label,
            "notes": notes,
        }

    # Upgrade normal -> warning-lite if future prediction looks risky
    if rule_status == "normal" and predicted_future_status in {"warning", "alert"}:
        final_status = "warning"
        final_label = "Predicted Water Chemistry Risk"
        notes.append("Current readings are acceptable, but conditions may worsen soon.")

    # Upgrade normal -> warning if anomaly seen
    if rule_status == "normal" and is_anomalous:
        final_status = "warning"
        final_label = "Unusual Water Chemistry Behavior"
        notes.append("The recent reading pattern looks unusual compared to normal tank behavior.")

    # Keep warning as warning, but enrich explanation
    if rule_status == "warning":
        if predicted_future_status in {"warning", "alert"}:
            notes.append("This chemistry stress may continue for a while.")
        if is_anomalous:
            notes.append("The recent pattern also appears unusual.")

    # Stable future note
    if rule_status == "normal" and predicted_future_status == "normal" and not is_anomalous:
        notes.append("Near-term water chemistry is likely to remain stable.")

    return {
        "final_status": final_status,
        "final_label": final_label,
        "notes": notes,
    }