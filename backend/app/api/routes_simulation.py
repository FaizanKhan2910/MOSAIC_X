from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.schema import WhatIfSimulationRequest, WhatIfSimulationResult
from backend.app.services.simulation_engine import SimulationEngine

router = APIRouter(prefix="/simulation", tags=["What-If Simulation"])

@router.post("/what-if", response_model=WhatIfSimulationResult)
def run_simulation(
    request: WhatIfSimulationRequest,
    user_id: str = "user_default",
    db: Session = Depends(get_db)
):
    return SimulationEngine.simulate_scenario(db, request, user_id=user_id)
