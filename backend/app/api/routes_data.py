from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.schema import DataRecordBase, DataRecord, DailySummary, BaselineMetric
from backend.app.models.db_models import DataRecordDB
from backend.app.services.ingestion import IngestionPipeline
from backend.app.services.baseline_engine import BaselineEngine

router = APIRouter(prefix="/data", tags=["Unified Data Explorer"])

@router.get("/records")
def get_records(
    user_id: str = "user_default",
    metric: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(DataRecordDB).filter(DataRecordDB.user_id == user_id)
    if metric:
        query = query.filter(DataRecordDB.metric == metric.lower())
    if source:
        query = query.filter(DataRecordDB.source == source.lower())

    total = query.count()
    records = query.order_by(DataRecordDB.timestamp.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [r.to_dict() for r in records]
    }

@router.post("/record")
def ingest_single_record(record: DataRecordBase, db: Session = Depends(get_db)):
    try:
        db_rec = IngestionPipeline.ingest_record(db, record)
        return {"status": "success", "record": db_rec.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch")
def ingest_batch_records(records: List[DataRecordBase], db: Session = Depends(get_db)):
    results = IngestionPipeline.ingest_batch(db, records)
    return {"status": "success", "ingested_count": len(results)}

@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: str = "user_default",
    db: Session = Depends(get_db)
):
    content = await file.read()
    csv_text = content.decode("utf-8", errors="replace")
    parsed_records = IngestionPipeline.parse_csv(user_id=user_id, csv_content=csv_text)
    if not parsed_records:
        raise HTTPException(status_code=400, detail="Could not parse any valid records from CSV.")
    db_records = IngestionPipeline.ingest_batch(db, parsed_records)
    return {
        "status": "success",
        "parsed": len(parsed_records),
        "ingested": len(db_records)
    }

@router.get("/summaries", response_model=List[DailySummary])
def get_daily_summaries(days: int = 45, user_id: str = "user_default", db: Session = Depends(get_db)):
    return BaselineEngine.get_daily_summaries(db, user_id=user_id, days=days)

@router.get("/baselines")
def get_baselines(window_days: int = 30, user_id: str = "user_default", db: Session = Depends(get_db)):
    baselines = BaselineEngine.calculate_baselines(db, user_id=user_id, window_days=window_days)
    return {k: v.model_dump() for k, v in baselines.items()}
