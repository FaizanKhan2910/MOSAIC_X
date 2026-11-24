import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.db_models import MissingContextDB, PrivacyLogDB
from backend.app.models.schema import MissingContextQuestion, ContextAnswerSubmission

class ContextEngine:
    @staticmethod
    def get_pending_questions(db: Session, user_id: str = "user_default") -> List[MissingContextQuestion]:
        records = db.query(MissingContextDB).filter(
            MissingContextDB.user_id == user_id,
            MissingContextDB.status == "pending"
        ).order_by(MissingContextDB.created_at.desc()).all()

        return [
            MissingContextQuestion(
                id=r.id,
                discovery_id=r.discovery_id,
                question_text=r.question_text,
                target_metric=r.target_metric,
                observed_anomaly_period=r.observed_anomaly_period,
                options=json.loads(r.options) if r.options else [],
                selected_option=r.selected_option,
                user_notes=r.user_notes,
                status=r.status,
                answered_at=r.answered_at
            ) for r in records
        ]

    @staticmethod
    def submit_answer(db: Session, user_id: str, submission: ContextAnswerSubmission) -> MissingContextQuestion:
        record = db.query(MissingContextDB).filter(
            MissingContextDB.id == submission.question_id,
            MissingContextDB.user_id == user_id
        ).first()

        if not record:
            raise ValueError(f"Question with id {submission.question_id} not found.")

        record.selected_option = submission.selected_option
        record.user_notes = submission.user_notes
        record.status = "answered"
        record.answered_at = datetime.utcnow()

        # Audit log
        audit = PrivacyLogDB(
            user_id=user_id,
            action="CONTEXT_ANSWER_SUBMITTED",
            target=f"question:{submission.question_id}",
            details=json.dumps({"option": submission.selected_option})
        )
        db.add(audit)
        db.commit()
        db.refresh(record)

        return MissingContextQuestion(
            id=record.id,
            discovery_id=record.discovery_id,
            question_text=record.question_text,
            target_metric=record.target_metric,
            observed_anomaly_period=record.observed_anomaly_period,
            options=json.loads(record.options) if record.options else [],
            selected_option=record.selected_option,
            user_notes=record.user_notes,
            status=record.status,
            answered_at=record.answered_at
        )

    @staticmethod
    def get_context_history(db: Session, user_id: str = "user_default") -> List[Dict[str, Any]]:
        records = db.query(MissingContextDB).filter(
            MissingContextDB.user_id == user_id,
            MissingContextDB.status == "answered"
        ).order_by(MissingContextDB.answered_at.desc()).all()

        return [r.to_dict() for r in records]
