import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.services.demo_generator import DemoDataGenerator
from backend.app.services.experiment_engine import ExperimentEngine
from backend.app.services.simulation_engine import SimulationEngine
from backend.app.models.schema import ExperimentCreate, WhatIfSimulationRequest

@pytest.fixture
def db_with_demo():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        DemoDataGenerator.load_demo_dataset(db, user_id="exp_user")
        yield db
    finally:
        db.close()

def test_experiment_creation_and_listing(db_with_demo):
    new_exp = ExperimentCreate(
        title="Reduce evening screen time",
        goal="Improve sleep quality",
        hypothesis="Limiting screens to under 3.0 hours will increase sleep duration",
        intervention_metric="screen_time",
        intervention_target_value=3.0,
        target_metric="sleep_duration",
        duration_days=7
    )
    created = ExperimentEngine.create_experiment(db_with_demo, user_id="exp_user", exp_data=new_exp)
    assert created.id is not None
    assert created.status == "active"
    assert len(created.causal_limitations) > 0

    all_exps = ExperimentEngine.get_experiments(db_with_demo, user_id="exp_user")
    # 1 demo seeded + 1 newly created
    assert len(all_exps) == 2

def test_what_if_simulation_uncertainty(db_with_demo):
    req = WhatIfSimulationRequest(
        intervention_metric="sleep_duration",
        delta_value=0.5,
        duration_days=7,
        target_metric="step_count"
    )
    result = SimulationEngine.simulate_scenario(db_with_demo, req, user_id="exp_user")
    assert result.estimated_target_change != 0
    assert result.predicted_scenario_range["high"] > result.predicted_scenario_range["low"]
    assert result.uncertainty_level in ["Low", "Moderate", "High"]
    assert "NOT a medical diagnosis" in result.scientific_disclaimer
