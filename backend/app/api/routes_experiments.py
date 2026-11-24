from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.models.schema import ExperimentCreate, ExperimentRecord
from backend.app.services.experiment_engine import ExperimentEngine

router = APIRouter(prefix="/experiments", tags=["Personal Experiment Lab"])

@router.get("", response_model=List[ExperimentRecord])
def list_experiments(user_id: str = "user_default", db: Session = Depends(get_db)):
    return ExperimentEngine.get_experiments(db, user_id=user_id)

@router.post("", response_model=ExperimentRecord)
def create_experiment(
    exp_data: ExperimentCreate,
    user_id: str = "user_default",
    db: Session = Depends(get_db)
):
    return ExperimentEngine.create_experiment(db, user_id=user_id, exp_data=exp_data)

@router.post("/{experiment_id}/evaluate", response_model=ExperimentRecord)
def evaluate_experiment(
    experiment_id: str,
    user_id: str = "user_default",
    db: Session = Depends(get_db)
):
    try:
        return ExperimentEngine.evaluate_experiment_outcome(db, experiment_id=experiment_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
