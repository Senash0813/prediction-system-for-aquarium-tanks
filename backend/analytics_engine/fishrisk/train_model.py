import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

# Load dataset
df = pd.read_csv("trend_feature_data.csv")

print(df["risk_score"].value_counts())

# Convert timestamp and sort
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(by="timestamp").reset_index(drop=True)

# -------------------------------------------------
# Step 1: Define how many rows represent 30 minutes
# Example: if readings are every 3 minutes -> 10 rows
# -------------------------------------------------
steps_ahead = 10

# Create target: risk score after 30 minutes
df["future_risk_score_30min"] = df["risk_score"].shift(-steps_ahead)

# Drop rows with missing future target
df = df.dropna().reset_index(drop=True)

# Select input features
features = [
    "temperature", "ph", "turbidity", "tds", "light",
    "risk_score",
    "temp_change", "ph_change", "turb_change", "risk_change",
    "temp_rate", "ph_rate", "turb_rate", "risk_rate",
    "temp_roll3", "ph_roll3", "turb_roll3", "risk_roll3",
    "temp_std3", "ph_std3", "turb_std3"
]

X = df[features]
y = df["future_risk_score_30min"]

# -------------------------------------------------
# Step 2: Time-based split (better for sensor data)
# -------------------------------------------------
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]
y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# Train model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

# Predict
y_pred = model.predict(X_test)

# Evaluate
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("RMSE:", rmse)
print("R2 Score:", r2)

# Feature importance
importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

print("\nFeature Importance:")
print(importance)

# Show sample predictions
results = pd.DataFrame({
    "Actual_Risk_30min": y_test.values,
    "Predicted_Risk_30min": y_pred
})

print("\nSample Predictions:")
print(results.head(10))

# import joblib
# joblib.dump(model, "fish_risk_model.pkl")
# print("Model saved as fish_risk_model.pkl")