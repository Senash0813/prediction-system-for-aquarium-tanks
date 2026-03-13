from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

from cleaning import clean_sensor_data
from transform import transform_sensor_data

load_dotenv()

app = FastAPI()

# MongoDB connection using environment variable
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in environment variables")

# MongoDB connection
client = MongoClient(MONGODB_URI)
db = client["aqua_gaurd_db"]


# Sensor data schema
class SensorData(BaseModel):
    tank_id: str
    temperature: float
    ph: float
    turbidity: float
    tds: float
    light: float
    timestamp: datetime


@app.get("/")
def root():
    return {"message": "IoT pipeline running"}


@app.post("/sensor-data")
def receive_sensor_data(data: SensorData):

    # Convert to dictionary
    data_dict = data.model_dump()

    # Select collection based on tank
    collection = db[data.tank_id]

    # Clean sensor data
    data_dict = clean_sensor_data(data_dict, collection)

    #Transform data
    data_dict = transform_sensor_data(data_dict)

    # Insert data
    collection.insert_one(data_dict)

    return {
        "status": "stored",
        "tank": data.tank_id
    }

