import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat_routes import router as chat_router
from api.chemistry_routes import router as chemistry_router
from api.tank_config_routes import router as tank_config_router
from api.tanks_routes import router as tanks_router
from analytics_engine.temperature_stability.job_runner import start_background_scheduler
from analytics_engine.temperature_stability.mongo_client import close_connection

from analytics_engine.water_chemistry_analytics.job_runner import start_background_scheduler as start_water_chemistry_background_scheduler
from analytics_engine.water_chemistry_analytics.mongo_client import close_connection as close_water_chemistry_connection

from analytics_engine.filter_health.generate_filter_insights import start_periodic_filter_health_insights
from api.filter_health_routes import router as filter_health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting temperature stability scheduler...")
    temp_scheduler = start_background_scheduler()
    logger.info("Temperature stability scheduler running.")

    logger.info("Starting water chemistry scheduler...")
    water_chem_scheduler = start_water_chemistry_background_scheduler()
    logger.info("Water chemistry scheduler running.")

    yield  # Server is live and handling requests here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down temperature stability scheduler...")
    temp_scheduler.shutdown(wait=False)
    close_connection()

    logger.info("Shutting down water chemistry scheduler...")
    water_chem_scheduler.shutdown(wait=False)
    close_water_chemistry_connection()

    logger.info("Schedulers and MongoDB connections closed.")


app = FastAPI(title="AquaGuard Backend", lifespan=lifespan)

# CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(chat_router)
app.include_router(chemistry_router)
app.include_router(tank_config_router)
app.include_router(tanks_router)
app.include_router(filter_health_router)

@app.on_event("startup")
def startup_tasks() -> None:
    # Run filter-health insight generation every 30 minutes after server starts.
    start_periodic_filter_health_insights(interval_minutes=30.0)

@app.get("/")
def root():
    return {"message": "Backend running 🚀"}
