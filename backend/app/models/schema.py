from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class DataRecordBase(BaseModel):
    user_id: str = "user_default"
    source: str = Field(..., description="Data origin (e.g. smartwatch, smartphone, fitness_tracker, manual, health_connect)")
    metric: str = Field(..., description="Metric identifier e.g. sleep_duration, step_count, screen_time, resting_heart_rate")
    value: float = Field(..., description="Numerical measured value")
    unit: str = Field(..., description="Unit of measurement (hours, steps, minutes, bpm)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Data provenance & reliability score (0-1)")
    consent_scope: str = Field(default="vital_analytics", description="User authorized scope for this datum")
    metadata: Optional[Dict[str, Any]] = None

class DataRecordCreate(DataRecordBase):
    pass

class DataRecord(DataRecordBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DailySummary(BaseModel):
    date: str
    sleep_duration: Optional[float] = None
    step_count: Optional[float] = None
    screen_time: Optional[float] = None
    resting_heart_rate: Optional[float] = None
    active_minutes: Optional[float] = None
    context_tags: List[str] = []

class BaselineMetric(BaseModel):
    metric: str
    mean: float
    std: float
    median: float
    min_val: float
    max_val: float
    unit: str
    n_days: int
    window_days: int
    last_updated: datetime

class DiscoveryItem(BaseModel):
    id: str
    title: str
    observation: str
    signal_a: str
    signal_b: str
    observation_window: str
    valid_observations: int
    correlation_coefficient: float
    p_value: float
    statistical_strength: str  # "Weak", "Moderate", "Strong"
    effect_size: str
    confidence_limitations: List[str]
    possible_alternative_explanations: List[str]
    plain_language_explanation: str
    has_missing_context_question: bool
    context_question_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MissingContextQuestion(BaseModel):
    id: str
    discovery_id: str
    question_text: str
    target_metric: str
    observed_anomaly_period: str
    options: List[str]
    selected_option: Optional[str] = None
    user_notes: Optional[str] = None
    status: str = "pending"  # "pending", "answered", "dismissed"
    answered_at: Optional[datetime] = None

class ContextAnswerSubmission(BaseModel):
    question_id: str
    selected_option: str
    user_notes: Optional[str] = None

class WhatIfSimulationRequest(BaseModel):
    intervention_metric: str  # e.g., "sleep_duration"
    delta_value: float        # e.g., +0.5 (hours)
    duration_days: int = 7
    target_metric: str        # e.g., "step_count"

class WhatIfSimulationResult(BaseModel):
    scenario_id: str
    intervention_metric: str
    delta_value: float
    duration_days: int
    target_metric: str
    current_baseline_target: float
    estimated_target_change: float
    predicted_scenario_range: Dict[str, float]  # {"low": float, "mid": float, "high": float}
    uncertainty_level: str  # "Low", "Moderate", "High"
    assumptions: List[str]
    required_data_to_verify: List[str]
    scientific_disclaimer: str

class ExperimentCreate(BaseModel):
    title: str
    goal: str
    hypothesis: str
    intervention_metric: str
    intervention_target_value: float
    target_metric: str
    duration_days: int = 7

class ExperimentRecord(BaseModel):
    id: str
    user_id: str
    title: str
    goal: str
    hypothesis: str
    intervention_metric: str
    intervention_target_value: float
    target_metric: str
    duration_days: int
    status: str  # "active", "completed", "declined"
    start_date: str
    end_date: str
    days_elapsed: int
    adherence_rate: float
    baseline_stats: Dict[str, Any]
    intervention_stats: Dict[str, Any]
    t_statistic: Optional[float] = None
    p_value: Optional[float] = None
    percentage_change: Optional[float] = None
    causal_limitations: List[str]
    conclusion: Optional[str] = None

class PrivacySettings(BaseModel):
    user_id: str = "user_default"
    sources_connected: Dict[str, bool]
    consent_scopes: Dict[str, bool]
    local_storage_only: bool = True
    ai_cloud_processing_opt_in: bool = False
    audit_log_entries: List[Dict[str, Any]] = []

class DataExportPayload(BaseModel):
    user_id: str
    exported_at: datetime
    record_count: int
    records: List[DataRecordBase]
    context_logs: List[Any]
    experiments: List[Any]
