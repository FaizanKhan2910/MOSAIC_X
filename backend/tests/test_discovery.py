import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.services.demo_generator import DemoDataGenerator
from backend.app.services.discovery_engine import DiscoveryEngine
from backend.app.services.baseline_engine import BaselineEngine

@pytest.fixture
def populated_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        DemoDataGenerator.load_demo_dataset(db, user_id="test_user")
        yield db
    finally:
        db.close()

def test_baseline_calculation(populated_db):
    baselines = BaselineEngine.calculate_baselines(populated_db, user_id="test_user", window_days=30)
    assert "sleep_duration" in baselines
    assert "step_count" in baselines
    assert baselines["sleep_duration"].mean > 5.0
    assert baselines["step_count"].mean > 3000.0

def test_discovery_engine_statistical_rigor(populated_db):
    discoveries = DiscoveryEngine.analyze_patterns(populated_db, user_id="test_user")
    assert len(discoveries) >= 2

    # Check first discovery: sleep vs step count
    sleep_steps_disc = next((d for d in discoveries if "Sleep" in d.title), None)
    assert sleep_steps_disc is not None
    assert sleep_steps_disc.valid_observations >= 20
    assert sleep_steps_disc.statistical_strength in ["Moderate", "Strong"]
    assert sleep_steps_disc.correlation_coefficient > 0.0  # Positive correlation in demo
    assert sleep_steps_disc.p_value < 0.05
    # Ensure limitations and alternative explanations are present
    assert len(sleep_steps_disc.confidence_limitations) >= 2
    assert len(sleep_steps_disc.possible_alternative_explanations) >= 2
    assert "correlation does NOT establish" in sleep_steps_disc.confidence_limitations[0]
