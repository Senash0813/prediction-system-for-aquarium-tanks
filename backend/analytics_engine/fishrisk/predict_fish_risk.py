import pandas as pd
import joblib

# -----------------------------
# Load trained model
# -----------------------------
model = joblib.load("fish_risk_model.pkl")

# -----------------------------
# Risk score function
# -----------------------------
def calculate_risk(temp, ph, turb):
    risk = 0

    # Temperature risk
    if temp < 22 or temp > 30:
        risk += 40
    elif temp < 24 or temp > 28:
        risk += 20

    # pH risk
    if ph < 6.0 or ph > 8.0:
        risk += 30
    elif ph < 6.5 or ph > 7.5:
        risk += 15

    # Turbidity risk
    if turb > 30:
        risk += 30
    elif turb > 20:
        risk += 15

    return risk

# -----------------------------
# Convert risk score to label
# -----------------------------
def risk_to_label(score):
    if score <= 30:
        return "SAFE"
    elif score <= 60:
        return "MODERATE"
    else:
        return "HIGH"

# -----------------------------
# Determine causes
# -----------------------------
def detect_causes(row):
    causes = []

    if row["temperature"] < 22:
        causes.append("low temperature")
    elif row["temperature"] > 28:
        causes.append("high temperature")

    if row["ph"] < 6.5:
        causes.append("low pH")
    elif row["ph"] > 7.5:
        causes.append("high pH")

    if row["turbidity"] > 30:
        causes.append("high turbidity")
    elif row["turbidity"] > 20:
        causes.append("moderate turbidity")

    if row["temp_change"] > 0:
        causes.append("increasing temperature")
    elif row["temp_change"] < 0:
        causes.append("falling temperature")

    if row["ph_change"] > 0:
        causes.append("rising pH")
    elif row["ph_change"] < 0:
        causes.append("falling pH")

    if row["turb_change"] > 0:
        causes.append("rising turbidity")
    elif row["turb_change"] < 0:
        causes.append("falling turbidity")

    return causes

# -----------------------------
# Suggest actions
# -----------------------------
def suggest_actions(causes):
    actions = []

    if "high temperature" in causes or "increasing temperature" in causes:
        actions.append("cool the water and improve aeration")

    if "low temperature" in causes:
        actions.append("check heater and stabilize water temperature")

    if "high turbidity" in causes or "rising turbidity" in causes:
        actions.append("check filtration and reduce feeding")

    if "moderate turbidity" in causes:
        actions.append("monitor water clarity and clean tank if needed")

    if "low pH" in causes or "high pH" in causes or "rising pH" in causes or "falling pH" in causes:
        actions.append("adjust pH gradually to avoid shocking the fish")

    if not actions:
        actions.append("continue monitoring current tank conditions")

    return actions

# -----------------------------
# Load recent sensor data
# IMPORTANT:
# This file should contain recent historical readings,
# not just one row, because trend features need previous data
# -----------------------------
df = pd.read_csv("fish_tank_data.csv")

# Convert timestamp and sort
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(by="timestamp").reset_index(drop=True)

# -----------------------------
# Create current risk score
# -----------------------------
df["risk_score"] = df.apply(
    lambda row: calculate_risk(row["temperature"], row["ph"], row["turbidity"]),
    axis=1
)

# -----------------------------
# Create trend features
# -----------------------------
df["temp_prev"] = df["temperature"].shift(1)
df["ph_prev"] = df["ph"].shift(1)
df["turb_prev"] = df["turbidity"].shift(1)
df["risk_prev"] = df["risk_score"].shift(1)

df["temp_change"] = df["temperature"] - df["temp_prev"]
df["ph_change"] = df["ph"] - df["ph_prev"]
df["turb_change"] = df["turbidity"] - df["turb_prev"]
df["risk_change"] = df["risk_score"] - df["risk_prev"]

df["time_diff_min"] = df["timestamp"].diff().dt.total_seconds() / 60

df["temp_rate"] = df["temp_change"] / df["time_diff_min"]
df["ph_rate"] = df["ph_change"] / df["time_diff_min"]
df["turb_rate"] = df["turb_change"] / df["time_diff_min"]
df["risk_rate"] = df["risk_change"] / df["time_diff_min"]

df["temp_roll3"] = df["temperature"].rolling(window=3).mean()
df["ph_roll3"] = df["ph"].rolling(window=3).mean()
df["turb_roll3"] = df["turbidity"].rolling(window=3).mean()
df["risk_roll3"] = df["risk_score"].rolling(window=3).mean()

df["temp_std3"] = df["temperature"].rolling(window=3).std()
df["ph_std3"] = df["ph"].rolling(window=3).std()
df["turb_std3"] = df["turbidity"].rolling(window=3).std()

# Drop rows with missing values from rolling and shift
df = df.dropna().reset_index(drop=True)

# Make sure there is at least one row left
if df.empty:
    print("Not enough data to create trend features. Need at least 3 readings.")
    exit()

# -----------------------------
# Take latest row for prediction
# -----------------------------
latest_row = df.iloc[-1]

# Features used by model
features = [
    "temperature", "ph", "turbidity", "tds", "light",
    "risk_score",
    "temp_change", "ph_change", "turb_change", "risk_change",
    "temp_rate", "ph_rate", "turb_rate", "risk_rate",
    "temp_roll3", "ph_roll3", "turb_roll3", "risk_roll3",
    "temp_std3", "ph_std3", "turb_std3"
]

input_df = pd.DataFrame([latest_row[features]])

# -----------------------------
# Predict 30-minute future risk score
# -----------------------------
predicted_score = model.predict(input_df)[0]
predicted_label = risk_to_label(predicted_score)

current_risk_score = latest_row["risk_score"]
predicted_change = predicted_score - current_risk_score

if predicted_change > 5:
    trend_message = "Fish stress is likely to increase in the next 30 minutes."
elif predicted_change < -5:
    trend_message = "Fish stress is likely to decrease in the next 30 minutes."
else:
    trend_message = "Fish stress is likely to remain stable in the next 30 minutes."

# -----------------------------
# Get causes and actions
# -----------------------------
causes = detect_causes(latest_row)
actions = suggest_actions(causes)

cause_text = " + ".join(causes) if causes else "stable conditions"
action_text = "; ".join(actions)

# -----------------------------
# Print final output
# -----------------------------
print("\n=== Fish Stress Prediction ===")
print(f"Current Timestamp: {latest_row['timestamp']}")
print(f"Current Risk Score: {current_risk_score:.2f}")
print(f"Predicted Risk Score (next 30 min): {predicted_score:.2f}")
print(f"Fish Stress Risk (30 min prediction): {predicted_label}")
print(f"Stress Trend: { trend_message}")
print(f"Cause: {cause_text}")
print(f"Action: {action_text}")