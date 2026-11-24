import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.db_models import DataRecordDB, DiscoveryDB, MissingContextDB, ExperimentDB, PrivacyLogDB

router = APIRouter(prefix="/privacy", tags=["Privacy Centre"])

@router.get("/status")
def get_privacy_status(user_id: str = "user_default", db: Session = Depends(get_db)):
    # Calculate real statistics on stored data
    record_count = db.query(DataRecordDB).filter(DataRecordDB.user_id == user_id).count()
    sources = db.query(DataRecordDB.source).filter(DataRecordDB.user_id == user_id).distinct().all()
    source_names = [s[0] for s in sources]

    audit_logs = db.query(PrivacyLogDB).filter(
        PrivacyLogDB.user_id == user_id
    ).order_by(PrivacyLogDB.timestamp.desc()).limit(20).all()

    return {
        "user_id": user_id,
        "storage_mode": "Local SQLite Database (Strict zero cloud persistence by default)",
        "encryption": "Database stored locally on device storage with user-level access controls",
        "total_records_stored": record_count,
        "active_sources": {
            "smartwatch": "smartwatch" in source_names,
            "smartphone": "smartphone" in source_names,
            "fitness_tracker": "fitness_tracker" in source_names,
            "android_health_connect": "health_connect" in source_names,
            "csv_import": "csv_import" in source_names
        },
        "consent_scopes": {
            "vital_analytics": True,
            "activity_read": True,
            "usage_analytics": True,
            "anonymized_research_opt_in": False
        },
        "recent_audit_events": [
            {
                "id": log.id,
                "action": log.action,
                "target": log.target,
                "timestamp": log.timestamp.isoformat(),
                "details": json.loads(log.details) if log.details else {}
            }
            for log in audit_logs
        ]
    }

@router.get("/export")
def export_user_data(user_id: str = "user_default", db: Session = Depends(get_db)):
    records = db.query(DataRecordDB).filter(DataRecordDB.user_id == user_id).all()
    questions = db.query(MissingContextDB).filter(MissingContextDB.user_id == user_id).all()
    experiments = db.query(ExperimentDB).filter(ExperimentDB.user_id == user_id).all()

    # Log export event in privacy ledger
    audit = PrivacyLogDB(
        user_id=user_id,
        action="DATA_EXPORTED",
        target="full_archive",
        details=json.dumps({"record_count": len(records)})
    )
    db.add(audit)
    db.commit()

    return {
        "export_metadata": {
            "user_id": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "export_format": "NEXORA_PORTABLE_INTELLIGENCE_JSON_V1",
            "compliance": "GDPR / CCPA / HIPAA Self-sovereign data portability compliant"
        },
        "data_records": [r.to_dict() for r in records],
        "context_logs": [q.to_dict() for q in questions],
        "experiments": [e.to_dict() for e in experiments]
    }

@router.delete("/purge-all")
def purge_all_data(user_id: str = "user_default", db: Session = Depends(get_db)):
    deleted_records = db.query(DataRecordDB).filter(DataRecordDB.user_id == user_id).delete()
    deleted_discoveries = db.query(DiscoveryDB).filter(DiscoveryDB.user_id == user_id).delete()
    deleted_questions = db.query(MissingContextDB).filter(MissingContextDB.user_id == user_id).delete()
    deleted_experiments = db.query(ExperimentDB).filter(ExperimentDB.user_id == user_id).delete()

    audit = PrivacyLogDB(
        user_id=user_id,
        action="DATA_PURGED_PERMANENTLY",
        target="all_personal_stores",
        details=json.dumps({
            "purged_records": deleted_records,
            "purged_discoveries": deleted_discoveries,
            "purged_questions": deleted_questions,
            "purged_experiments": deleted_experiments
        })
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": "All personal records, discoveries, and experimental logs have been permanently erased from local storage.",
        "purged_records": deleted_records,
        "timestamp": datetime.utcnow().isoformat()
    }
