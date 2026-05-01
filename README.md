# AquaGuard: IoT-Based Predictive Analytics System for Aquarium Tanks

A comprehensive, production-grade system for real-time monitoring, analysis, and prediction of aquarium tank health using machine learning and IoT sensors.

## 📋 Quick Links

- **📖 [Complete Final Report](FINAL_REPORT.md)** - Comprehensive system documentation (includes architecture, data flow, ML models, deployment guides)
- **🎯 [System Overview](#system-overview)** - Quick reference below
- **🚀 [Project Structure](#-project-folder-structure)** - Complete directory layout
- **📦 [Getting Started](#getting-started)**

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

---

## 📁 Project Folder Structure

```
prediction-system-for-aquarium-tanks/
│
├── 📄 README.md                         # Project overview and documentation
├── 📄 FINAL_REPORT.md                   # Comprehensive system report
│
├── 📦 backend/                          # Python Backend - Flask API & ML Engines
│   ├── 📄 main.py                       # Flask application entry point
│   ├── 📄 requirements.txt              # Python dependencies
│   ├── 📄 cleaning.py                   # Data cleaning utilities
│   ├── 📄 transform.py                  # Data transformation pipeline
│   │
│   ├── 📂 analytics_engine/             # 4 Independent ML Engine Modules
│   │   ├── 📂 filter_health/            # Filter Health & Oxygen Analysis
│   │   │   ├── 📄 main.py
│   │   │   ├── 📄 job_runner.py
│   │   │   ├── 📄 settings.py
│   │   │   ├── 📄 train_filter_health_model.py
│   │   │   ├── 📄 generate_filter_insights.py
│   │   │   ├── 📄 rule_filterhealth.py
│   │   │   ├── 📄 oxygen_estimation.py
│   │   │   ├── 📄 turbidity_service.py
│   │   │   └── 📄 filter_health_model.joblib    # Pre-trained model
│   │   │
│   │   ├── 📂 fishrisk/                 # Fish Risk Assessment Engine
│   │   │   ├── 📄 main.py
│   │   │   ├── 📄 job_runner.py
│   │   │   ├── 📄 settings.py
│   │   │   ├── 📄 mongo_client.py
│   │   │   ├── 📄 train_model.py
│   │   │   ├── 📄 predict_fish_risk.py
│   │   │   ├── 📄 insight_4_fish_risk.py
│   │   │   ├── 📄 load_csv.py
│   │   │   └── 📄 risk_labeled_data.csv
│   │   │
│   │   ├── 📂 temperature_stability/    # Temperature Stability Engine
│   │   │   ├── 📄 main.py
│   │   │   ├── 📄 job_runner.py
│   │   │   ├── 📄 settings.py
│   │   │   ├── 📄 mongo_client.py
│   │   │   ├── 📄 insight_1_temperature.py
│   │   │   ├── 📄 anomaly_detector.py
│   │   │   └── 📄 light_mapper.py
│   │   │
│   │   └── 📂 water_chemistry_analytics/  # Water Chemistry Analytics Engine
│   │       ├── 📄 main.py
│   │       ├── 📄 job_runner.py
│   │       ├── 📄 settings.py
│   │       ├── 📄 mongo_client.py
│   │       ├── 📄 mongo_loader.py
│   │       ├── 📄 insight_2_water_chemistry.py
│   │       ├── 📄 anomaly_detector.py
│   │       ├── 📄 feature_builder.py
│   │       ├── 📄 metric_analytics.py
│   │       ├── 📄 ml_predictor.py
│   │       ├── 📄 model_loader.py
│   │       ├── 📄 hybrid_decision.py
│   │       ├── 📄 ph_service.py
│   │       ├── 📄 train_models.py
│   │       ├── 📄 test_ph_analytics.py
│   │       └── 📂 models/               # Trained ML models storage
│   │
│   ├── 📂 api/                          # RESTful API Routes
│   │   ├── 📄 tanks_routes.py           # Tank management endpoints
│   │   ├── 📄 tank_config_routes.py     # Tank configuration endpoints
│   │   ├── 📄 chemistry_routes.py       # Chemistry insights endpoints
│   │   ├── 📄 filter_health_routes.py   # Filter health endpoints
│   │   └── 📄 chat_routes.py            # Chat/chatbot endpoints
│   │
│   └── 📂 raw_generator/                # Test Data Generation & ETL Triggers
│       ├── 📄 main.py
│       ├── 📄 config.py                 # Configuration settings
│       ├── 📄 tank1_profile.py          # Tank 1 sensor profiles
│       ├── 📄 generate_raw_tank1.py     # Raw data generator
│       ├── 📄 process_raw_tank1.py      # Raw data processor
│       ├── 📄 insert_test_data.py       # Test data insertion
│       └── 📄 trigger_function.js       # MongoDB trigger for ETL
│
├── 🎨 frontend/                         # React + TypeScript Dashboard
│   ├── 📄 package.json                  # Dependencies & scripts
│   ├── 📄 bun.lockb                     # Bun package lock
│   ├── 📄 vite.config.ts                # Vite build configuration
│   ├── 📄 tsconfig.json                 # TypeScript configuration
│   ├── 📄 tailwind.config.ts            # Tailwind CSS configuration
│   ├── 📄 postcss.config.js             # PostCSS configuration
│   ├── 📄 eslint.config.js              # ESLint configuration
│   ├── 📄 vitest.config.ts              # Vitest testing configuration
│   ├── 📄 components.json               # Component library config
│   ├── 📄 netlify.toml                  # Netlify deployment config
│   ├── 📄 index.html                    # HTML entry point
│   ├── 📄 README.md                     # Frontend-specific README
│   │
│   ├── 📂 public/                       # Static assets
│   │   └── 📄 robots.txt
│   │
│   └── 📂 src/                          # React application source
│       ├── 📄 main.tsx                  # React entry point
│       ├── 📄 App.tsx                   # Main App component
│       ├── 📄 App.css                   # App-level styles
│       ├── 📄 index.css                 # Global styles
│       ├── 📄 vite-env.d.ts             # Vite environment types
│       │
│       ├── 📂 api/
│       │   └── 📄 client.ts             # API client for backend communication
│       │
│       ├── 📂 components/               # React components
│       │   ├── 📄 Layout.tsx            # Main layout wrapper
│       │   ├── 📄 AppSidebar.tsx        # Sidebar navigation
│       │   ├── 📄 NavLink.tsx           # Navigation link component
│       │   ├── 📄 AddTankDialog.tsx     # Add tank modal
│       │   ├── 📄 TankCard.tsx          # Tank information card
│       │   ├── 📄 CircularGauge.tsx     # Circular gauge visualization
│       │   ├── 📄 TrendChart.tsx        # Trend chart component
│       │   ├── 📄 InsightCard.tsx       # Insight display card
│       │   ├── 📄 AlertBanner.tsx       # Alert notification banner
│       │   ├── 📄 PredictiveNotifications.tsx  # Predictive alerts
│       │   ├── 📂 chatbot/              # Chatbot components
│       │   └── 📂 ui/                   # Reusable UI components
│       │
│       ├── 📂 context/
│       │   └── 📄 TanksContext.tsx      # React context for tank state
│       │
│       ├── 📂 hooks/                    # Custom React hooks
│       │   ├── 📄 use-mobile.tsx        # Mobile detection hook
│       │   ├── 📄 use-toast.ts          # Toast notification hook
│       │   └── 📄 useTheme.ts           # Theme management hook
│       │
│       ├── 📂 lib/                      # Utility libraries and helpers
│       │   └── (various utility functions)
│       │
│       ├── 📂 pages/                    # Page components
│       │
│       ├── 📂 styles/                   # Styling modules
│       │
│       └── 📂 test/                     # Test files
│
├── 🔧 other_codes/                      # Additional/Legacy Code
│   ├── 📄 package.json
│   ├── 📄 server.js                     # Node.js server (legacy)
│   └── 📄 sketch_mar17a.ino             # Arduino/ESP32 firmware sketch
│
```

---

## 🔑 Key Components Explained

### Backend Architecture
- **Flask API** (`main.py`): Handles all HTTP requests from the frontend
- **ML Engines** (4 independent modules): Run asynchronously every 3 minutes to generate insights
- **Data Pipeline**: Raw data → Cleaning → Transformation → ML Analysis → Insights
- **MongoDB Integration**: Stores raw data, cleaned data, and generated insights

### Frontend Architecture
- **React + TypeScript**: Type-safe component development
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first styling
- **Real-time Dashboard**: Displays live tank metrics and AI insights

### ML Engine Modules

| Engine | Purpose | Location |
|--------|---------|----------|
| **Temperature Stability** | Detects anomalies & trend analysis | `temperature_stability/` |
| **Water Chemistry** | pH, TDS forecasting & multivariate analysis | `water_chemistry_analytics/` |
| **Fish Risk** | Predicts fish stress levels | `fishrisk/` |
| **Filter Health** | Oxygen estimation & filter performance | `filter_health/` |

---

## 🚀 Getting Started

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
