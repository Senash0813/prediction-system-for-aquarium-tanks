require("dotenv").config();

const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

// ==============================
// MongoDB Connection
// ==============================
mongoose
  .connect(process.env.MONGODB_URI, { dbName: "aqua_guard_db" })
  .then(() => console.log("MongoDB connected to aqua_guard_db"))
  .catch((err) => console.error("MongoDB connection error:", err));

// ==============================
// tank_config schema (read-only here)
// ==============================
const tankConfigSchema = new mongoose.Schema({
  tank_id: String,
  mac_address: String,
}, { collection: "tank_config" });

const TankConfig = mongoose.model("TankConfig", tankConfigSchema);

// ==============================
// Sensor reading schema factory
// Returns a model bound to a specific collection e.g. raw_tank_1
// ==============================
function getSensorModel(collectionName) {
  if (mongoose.modelNames().includes(collectionName)) {
    return mongoose.model(collectionName);
  }

  const schema = new mongoose.Schema({
    tank_id:     { type: String,  required: true },
    temperature: { type: Number,  required: true },
    ph:          { type: Number,  required: true },
    turbidity:   { type: Number,  required: true },
    tds:         { type: Number,  required: true },
    light:       { type: Number,  required: true },
    timestamp:   { type: Date,    required: true },
    processed:   { type: Boolean, default: false },
  }, { collection: collectionName });

  return mongoose.model(collectionName, schema);
}

// ==============================
// Routes
// ==============================
app.get("/", (req, res) => {
  res.send("AquaGuard ESP32 receiver is running");
});

app.post("/api/sensor-data", async (req, res) => {
  try {
    const { mac, temperature, ph, turbidity, tds, light, timestamp } = req.body;

    if (!mac) {
      return res.status(400).json({ success: false, message: "MAC address is required" });
    }

    // Look up tank by MAC address
    const tankConfig = await TankConfig.findOne({ mac_address: mac.toUpperCase() });

    if (!tankConfig) {
      return res.status(404).json({ success: false, message: `No tank registered for MAC: ${mac}` });
    }

    const tankId = tankConfig.tank_id;
    const collectionName = `raw_${tankId}`;

    const SensorReading = getSensorModel(collectionName);

    const newReading = new SensorReading({
      tank_id:     tankId,
      temperature,
      ph,
      turbidity,
      tds,
      light,
      timestamp:   timestamp ? new Date(timestamp) : new Date(),
      processed:   false,
    });

    await newReading.save();

    console.log(`Saved reading for ${tankId} (MAC: ${mac}) → collection: ${collectionName}`);

    res.status(200).json({ success: true, message: `Data saved to ${collectionName}` });

  } catch (error) {
    console.error("Error saving sensor data:", error);
    res.status(500).json({ success: false, message: "Failed to save sensor data" });
  }
});

// ==============================
// Start Server
// ==============================
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
