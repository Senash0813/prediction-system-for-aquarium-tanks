import pandas as pd

# Load dataset
df = pd.read_csv("fish_tank_data.csv")

# Convert timestamp and sort data
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(by="timestamp").reset_index(drop=True)

# -----------------------------
# Step 3: Calculate risk score
# -----------------------------
def calculate_risk(row):
    temp = row["temperature"]
    ph = row["ph"]
    turb = row["turbidity"]

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

# Apply risk score
df["risk_score"] = df.apply(calculate_risk, axis=1)

# Convert score to label
def risk_to_label(score):
    if score <= 30:
        return "Safe"
    elif score <= 60:
        return "Moderate"
    else:
        return "High"

df["risk_level"] = df["risk_score"].apply(risk_to_label)

# --------------------------------
# Step 4: Create trend features
# --------------------------------

# Previous values
df["temp_prev"] = df["temperature"].shift(1)
df["ph_prev"] = df["ph"].shift(1)
df["turb_prev"] = df["turbidity"].shift(1)
df["risk_prev"] = df["risk_score"].shift(1)

# Changes from previous reading
df["temp_change"] = df["temperature"] - df["temp_prev"]
df["ph_change"] = df["ph"] - df["ph_prev"]
df["turb_change"] = df["turbidity"] - df["turb_prev"]
df["risk_change"] = df["risk_score"] - df["risk_prev"]

# Time difference in minutes
df["time_diff_min"] = df["timestamp"].diff().dt.total_seconds() / 60

# Rate of change
df["temp_rate"] = df["temp_change"] / df["time_diff_min"]
df["ph_rate"] = df["ph_change"] / df["time_diff_min"]
df["turb_rate"] = df["turb_change"] / df["time_diff_min"]
df["risk_rate"] = df["risk_change"] / df["time_diff_min"]

# Rolling averages (last 3 readings)
df["temp_roll3"] = df["temperature"].rolling(window=3).mean()
df["ph_roll3"] = df["ph"].rolling(window=3).mean()
df["turb_roll3"] = df["turbidity"].rolling(window=3).mean()
df["risk_roll3"] = df["risk_score"].rolling(window=3).mean()

# Rolling standard deviation (instability)
df["temp_std3"] = df["temperature"].rolling(window=3).std()
df["ph_std3"] = df["ph"].rolling(window=3).std()
df["turb_std3"] = df["turbidity"].rolling(window=3).std()

# Optional trend direction labels
df["temp_trend"] = df["temp_change"].apply(
    lambda x: "Rising" if x > 0 else ("Falling" if x < 0 else "Stable")
)
df["ph_trend"] = df["ph_change"].apply(
    lambda x: "Rising" if x > 0 else ("Falling" if x < 0 else "Stable")
)
df["turb_trend"] = df["turb_change"].apply(
    lambda x: "Rising" if x > 0 else ("Falling" if x < 0 else "Stable")
)

# Remove rows with missing values caused by shift() and rolling()
df = df.dropna().reset_index(drop=True)

# Show first rows
print(df.head())

# Save final dataset with trend features
df.to_csv("trend_feature_data.csv", index=False)

print("Step 4 completed. File saved as trend_feature_data.csv")