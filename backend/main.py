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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting temperature stability scheduler...")
    scheduler = start_background_scheduler()
    logger.info("Temperature stability scheduler running.")

    yield  # Server is live and handling requests here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down temperature stability scheduler...")
    scheduler.shutdown(wait=False)
    close_connection()
    logger.info("Scheduler and MongoDB connection closed.")


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


@app.get("/")
def root():
    return {"message": "Backend running 🚀"}
