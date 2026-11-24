import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.schema import DataRecordBase
from backend.app.services.ingestion import IngestionPipeline

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_ingestion_range_validation():
    # Valid sleep
    valid_rec = DataRecordBase(
        user_id="user_test",
        source="smartwatch",
        metric="sleep_duration",
        value=7.5,
        unit="hours"
    )
    is_valid, err, quality = IngestionPipeline.validate_and_normalize(valid_rec)
    assert is_valid is True
    assert quality >= 0.9

    # Out of range sleep (e.g. 35 hours)
    invalid_rec = DataRecordBase(
        user_id="user_test",
        source="smartwatch",
        metric="sleep_duration",
        value=35.0,
        unit="hours"
    )
    is_valid, err, quality = IngestionPipeline.validate_and_normalize(invalid_rec)
    assert is_valid is False
    assert "out of expected physiological range" in err

def test_csv_parser():
    sample_csv = """date,sleep_duration,step_count,screen_time,resting_heart_rate
2026-03-01,7.2,8500,4.1,62
2026-03-02,8.0,9800,3.5,59
"""
    records = IngestionPipeline.parse_csv(user_id="user_test", csv_content=sample_csv)
    assert len(records) == 8  # 4 metrics * 2 days
    sleep_recs = [r for r in records if r.metric == "sleep_duration"]
    assert len(sleep_recs) == 2
    assert sleep_recs[0].value == 7.2
