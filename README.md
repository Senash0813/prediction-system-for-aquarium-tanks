# AquaGuard: IoT-Based Predictive Analytics System for Aquarium Tanks

A comprehensive, production-grade system for real-time monitoring, analysis, and prediction of aquarium tank health using machine learning and IoT sensors.

## 📋 Quick Links

- **📖 [Complete Final Report](FINAL_REPORT.md)** - Comprehensive system documentation (includes architecture, data flow, ML models, deployment guides)
- **🎯 [System Overview](#system-overview)** - Quick reference below
- **🚀 [Getting Started](#getting-started)**

## 🎯 System Overview

**AquaGuard** is a complete IoT analytics platform featuring:

- **Real-time Data Collection**: ESP32-based sensors (temperature, pH, TDS, turbidity, light) sampling every 3 minutes
- **Cloud Data Pipeline**: MongoDB Atlas with automatic ETL triggers for data cleaning and transformation
- **AI-Powered Analytics**: 4 independent ML engines providing predictive insights:
  - 🌡️ Temperature Stability (trend analysis + anomaly detection)
  - 💧 Water Chemistry (multivariate forecasting)
  - 🐠 Fish Risk Assessment (stress level prediction)
  - 🔧 Filter Health & Oxygen Estimation
- **Interactive Dashboard**: React-based real-time visualizations with circular gauges, trend charts, and AI insights
- **RESTful API**: Well-designed endpoints for all data and insights
- **Hybrid Decision System**: Combines explainable rule-based logic with adaptive machine learning

## 🏗️ Architecture Highlights

```
ESP32 Sensors (3-min intervals)
    ↓
REST API Backend
    ↓
MongoDB Raw Collections (raw_tank_*)
    ↓
MongoDB Trigger (Auto-cleaning & transformation)
    ↓
MongoDB Cleaned Collections (tank_*)
    ↓
4 Async ML Engines (Every 3 min)
    ├─ Temperature Stability Engine
    ├─ Water Chemistry Analytics
    ├─ Fish Risk Engine
    └─ Filter Health Engine
    ↓
Insights Database
    ↓
REST API Endpoints
    ↓
React Dashboard (Real-time visualization)
```

## 🛠️ Technical Stack

| Component | Technology |
|-----------|-----------|
| IoT Devices | ESP32 (Arduino-based) + Multiple Sensors |
| Backend | Python 3.11, FastAPI |
| Database | MongoDB Atlas (NoSQL, Cloud) |
| Data Triggers | Node.js (MongoDB Realm) |
| ML/Analytics | scikit-learn, pandas, numpy |
| Scheduling | APScheduler (async jobs) |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS + shadcn-ui |

## 📊 Machine Learning Techniques Implemented

✅ **Temporal Trend Analysis**: Linear regression on time-series data for rate-of-change predictions
✅ **Anomaly Detection**: Isolation Forest model trained on 7-day historical baselines
✅ **Multivariate Forecasting**: Random Forest regressors for pH, TDS, temperature 30-min ahead
✅ **Risk Classification**: Behavior pattern analysis combining rule-based + ML scoring
✅ **Filter Degradation Tracking**: Turbidity patterns for predictive maintenance

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- ESP32 microcontroller with sensors
- Render.com account (backend)
- Netlify account (frontend)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI, API keys

# Run server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Runs on :5173
```

### ESP32 Setup

1. Open `other_codes/sketch_mar17a.ino` in Arduino IDE
2. Configure WiFi credentials and backend URL
3. Install required libraries:
   - OneWire
   - DallasTemperature
   - BH1750
   - PubSubClient
4. Upload to ESP32 Dev Module

## 📝 API Endpoints

```
GET    /api/tanks                          # List all tanks
GET    /api/tanks/{id}/latest              # Latest sensor reading
GET    /api/tanks/{id}/latest-insight      # Latest AI insights
GET    /api/tank/{id}/ph-analysis          # Water chemistry analysis
GET    /api/tank/{id}/turbidity-analysis   # Filter health analysis
POST   /api/chat                           # AI-powered Q&A
```

## 📺 Dashboard Features

- **Tank Overview**: Grid view of all monitored tanks
- **Real-time Gauges**: Circular gauges for temp, pH, TDS, turbidity
- **Trend Charts**: 24h, 7d, 30d time-series visualizations
- **AI Insights**: Machine-generated analysis and recommendations
- **Alert Notifications**: Real-time warnings and predictions
- **Predictive Alerts**: "Temperature will be unsafe in 25 minutes"

## 🔬 Data Flow Example

### 1. Sensor → Raw Collection
```
ESP32 → /api/sensor-data → raw_tank_1 collection
{
  mac_address: "AA:BB:CC:DD:EE:FF",
  timestamp: 2026-04-21T12:30:00Z,
  temperature: 26.5,
  ph: 7.2,
  turbidity: 2.8,
  tds: 295.0,
  light: 3500.0
}
```

### 2. MongoDB Trigger Cleaning
```javascript
// trigger_function.js
// 1. Validate sensor values (outlier detection)
// 2. Fill missing with last_good_value
// 3. Categorize light (Night Mode, Ideal, etc.)
// 4. Flag anomalies
// 5. Insert into tank_1 collection
```

### 3. ML Analysis Every 3 Minutes
```python
# Each engine independently:
# 1. Fetch last 10 readings from tank_1
# 2. Build ML features
# 3. Load pre-trained models
# 4. Generate predictions
# 5. Combine with rule-based logic
# 6. Save to insights database
```

### 4. API Returns Insights
```json
{
  "status": "normal",
  "current_temperature": 26.5,
  "rate_per_minute": -0.02,
  "prediction_30_min": "normal",
  "anomaly_detected": false,
  "recommendation": "Conditions are optimal",
  "confidence": 0.92
}
```

## 📈 Key Metrics

- **Data Points/Day**: 480 per tank (3-minute intervals)
- **API Response Time**: <100ms (cached)
- **Trigger Latency**: 50-100ms (MongoDB)
- **ML Prediction Time**: 10-50ms (cached models)
- **Dashboard Update Interval**: 30 seconds

## 🔒 Data Management

- **Raw collections**: 30-day TTL (audit trail)
- **Cleaned collections**: 90-day TTL (analysis data)
- **Insights**: 7-day TTL (rolling predictions)
- **MongoDB backups**: Automated, multi-region replication

## 🎓 Educational Value

This system demonstrates:
- ✅ IoT data pipeline architecture
- ✅ NoSQL database design for time-series
- ✅ Real-time ETL with cloud triggers
- ✅ ML model training and inference at scale
- ✅ Hybrid rule-based + ML decision systems
- ✅ RESTful API design principles
- ✅ Production-grade error handling
- ✅ React modern state management
- ✅ Software engineering best practices

## 🤝 Contributing

This is a student project. Contributions for enhancements welcome!

Potential improvements:
- LSTM/Prophet for advanced forecasting
- Computer vision integration (algae detection)
- Cross-tank correlation analysis
- TensorFlow Lite edge AI on ESP32
- Home automation integration
- Advanced XAI (SHAP) explanations

## 📄 License

Educational project - Free to use and modify

---

**For detailed system documentation, architecture decisions, ML models, and deployment guides, see [FINAL_REPORT.md](FINAL_REPORT.md)** 
