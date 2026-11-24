from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.demo_generator import DemoDataGenerator
from backend.app.services.discovery_engine import DiscoveryEngine

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

@router.post("/load")
def load_demo(user_id: str = "user_default", db: Session = Depends(get_db)):
    result = DemoDataGenerator.load_demo_dataset(db, user_id=user_id)
    # Immediately trigger pattern analysis so discoveries and context questions are live
    discoveries = DiscoveryEngine.analyze_patterns(db, user_id=user_id)
    result["discoveries_computed"] = len(discoveries)
    return result
