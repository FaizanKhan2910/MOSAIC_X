from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.models.schema import DiscoveryItem
from backend.app.services.discovery_engine import DiscoveryEngine

router = APIRouter(prefix="/discovery", tags=["Personal Discovery Engine"])

@router.get("/patterns", response_model=List[DiscoveryItem])
def get_discoveries(user_id: str = "user_default", db: Session = Depends(get_db)):
    return DiscoveryEngine.analyze_patterns(db, user_id=user_id)

@router.post("/analyze", response_model=List[DiscoveryItem])
def trigger_analysis(user_id: str = "user_default", db: Session = Depends(get_db)):
    return DiscoveryEngine.analyze_patterns(db, user_id=user_id)
