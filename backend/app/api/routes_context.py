from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.models.schema import MissingContextQuestion, ContextAnswerSubmission
from backend.app.services.context_engine import ContextEngine

router = APIRouter(prefix="/context", tags=["Missing Context Intelligence"])

@router.get("/questions", response_model=List[MissingContextQuestion])
def get_pending_questions(user_id: str = "user_default", db: Session = Depends(get_db)):
    return ContextEngine.get_pending_questions(db, user_id=user_id)

@router.post("/answer", response_model=MissingContextQuestion)
def submit_context_answer(
    submission: ContextAnswerSubmission,
    user_id: str = "user_default",
    db: Session = Depends(get_db)
):
    try:
        return ContextEngine.submit_answer(db, user_id=user_id, submission=submission)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/history")
def get_context_history(user_id: str = "user_default", db: Session = Depends(get_db)):
    return ContextEngine.get_context_history(db, user_id=user_id)
