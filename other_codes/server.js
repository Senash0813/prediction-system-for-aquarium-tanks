require("dotenv").config();

const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

// ==============================
// MongoDB Atlas Connection
// ==============================
mongoose
  .connect(process.env.MONGO_URI)
  .then(() => {
    console.log("MongoDB Atlas connected successfully");
  })
  .catch((err) => {
    console.error("MongoDB connection error:", err);
  });

// ==============================
// Schema
// ==============================
const sensorSchema = new mongoose.Schema(
  {
    deviceId: { type: String, required: true },
    temperature: { type: Number, required: true },
    turbidity: { type: Number, required: true },
    tds: { type: Number, required: true },
    light: { type: Number, required: true },
    ph: { type: Number, required: true },
    timestamp: { type: String, required: true }
  },
  { timestamps: true }
);

const SensorReading = mongoose.model("SensorReading", sensorSchema);

// ==============================
// Routes
// ==============================
app.get("/", (req, res) => {
  res.send("Fish tank backend is running");
});

app.post("/api/sensor-data", async (req, res) => {
  try {
    console.log("Received data:", req.body);

    const {
      deviceId,
      temperature,
      turbidity,
      tds,
      light,
      ph,
      timestamp
    } = req.body;

    const newReading = new SensorReading({
      deviceId,
      temperature,
      turbidity,
      tds,
      light,
      ph,
      timestamp
    });

    await newReading.save();

    res.status(200).json({
      success: true,
      message: "Sensor data stored successfully in MongoDB Atlas"
    });
  } catch (error) {
    console.error("Error saving sensor data:", error);
    res.status(500).json({
      success: false,
      message: "Failed to save sensor data"
    });
  }
});

// ==============================
// Start Server
// ==============================
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});