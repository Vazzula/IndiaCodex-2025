from fastapi import APIRouter
from src.api.simulation.controller import router as simulation_router

api_router = APIRouter()

# Include routers from the individual endpoint files
api_router.include_router(
    simulation_router, prefix="/simulation", tags=["Simulation Endpoints"]
)
