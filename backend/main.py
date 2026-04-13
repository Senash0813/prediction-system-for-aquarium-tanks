from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chemistry_routes import router as chemistry_router
from api.tank_config_routes import router as tank_config_router
from api.tanks_routes import router as tanks_router

app = FastAPI(title="AquaGuard Backend")

# CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(chemistry_router)
app.include_router(tank_config_router)
app.include_router(tanks_router)


@app.get("/")
def root():
    return {"message": "Backend running 🚀"}