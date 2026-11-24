import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from backend.app.core.database import Base

class DataRecordDB(Base):
    __tablename__ = "data_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True, default="user_default")
    source = Column(String, index=True)
    metric = Column(String, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    quality = Column(Float, default=1.0)
    consent_scope = Column(String, default="vital_analytics")
    meta_info = Column(Text, default="{}")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source": self.source,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "quality": self.quality,
            "consent_scope": self.consent_scope,
            "metadata": json.loads(self.meta_info) if self.meta_info else {}
        }

class DiscoveryDB(Base):
    __tablename__ = "discoveries"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, default="user_default")
    title = Column(String, nullable=False)
    observation = Column(Text, nullable=False)
    signal_a = Column(String, nullable=False)
    signal_b = Column(String, nullable=False)
    observation_window = Column(String, nullable=False)
    valid_observations = Column(Integer, nullable=False)
    correlation_coefficient = Column(Float, nullable=False)
    p_value = Column(Float, nullable=False)
    statistical_strength = Column(String, nullable=False)
    effect_size = Column(String, nullable=False)
    confidence_limitations = Column(Text, default="[]")  # JSON array
    possible_alternative_explanations = Column(Text, default="[]")  # JSON array
    plain_language_explanation = Column(Text, nullable=False)
    has_missing_context_question = Column(Boolean, default=False)
    context_question_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "observation": self.observation,
            "signal_a": self.signal_a,
            "signal_b": self.signal_b,
            "observation_window": self.observation_window,
            "valid_observations": self.valid_observations,
            "correlation_coefficient": self.correlation_coefficient,
            "p_value": self.p_value,
            "statistical_strength": self.statistical_strength,
            "effect_size": self.effect_size,
            "confidence_limitations": json.loads(self.confidence_limitations) if self.confidence_limitations else [],
            "possible_alternative_explanations": json.loads(self.possible_alternative_explanations) if self.possible_alternative_explanations else [],
            "plain_language_explanation": self.plain_language_explanation,
            "has_missing_context_question": self.has_missing_context_question,
            "context_question_id": self.context_question_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class MissingContextDB(Base):
    __tablename__ = "missing_context_questions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, default="user_default")
    discovery_id = Column(String, index=True, nullable=False)
    question_text = Column(Text, nullable=False)
    target_metric = Column(String, nullable=False)
    observed_anomaly_period = Column(String, nullable=False)
    options = Column(Text, default="[]")  # JSON array
    selected_option = Column(String, nullable=True)
    user_notes = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, answered, dismissed
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "discovery_id": self.discovery_id,
            "question_text": self.question_text,
            "target_metric": self.target_metric,
            "observed_anomaly_period": self.observed_anomaly_period,
            "options": json.loads(self.options) if self.options else [],
            "selected_option": self.selected_option,
            "user_notes": self.user_notes,
            "status": self.status,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None
        }

class ExperimentDB(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, default="user_default")
    title = Column(String, nullable=False)
    goal = Column(String, nullable=False)
    hypothesis = Column(Text, nullable=False)
    intervention_metric = Column(String, nullable=False)
    intervention_target_value = Column(Float, nullable=False)
    target_metric = Column(String, nullable=False)
    duration_days = Column(Integer, default=7)
    status = Column(String, default="active")  # active, completed, declined
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    days_elapsed = Column(Integer, default=0)
    adherence_rate = Column(Float, default=0.0)
    baseline_stats = Column(Text, default="{}")  # JSON
    intervention_stats = Column(Text, default="{}")  # JSON
    t_statistic = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    percentage_change = Column(Float, nullable=True)
    causal_limitations = Column(Text, default="[]")  # JSON
    conclusion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "goal": self.goal,
            "hypothesis": self.hypothesis,
            "intervention_metric": self.intervention_metric,
            "intervention_target_value": self.intervention_target_value,
            "target_metric": self.target_metric,
            "duration_days": self.duration_days,
            "status": self.status,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "days_elapsed": self.days_elapsed,
            "adherence_rate": self.adherence_rate,
            "baseline_stats": json.loads(self.baseline_stats) if self.baseline_stats else {},
            "intervention_stats": json.loads(self.intervention_stats) if self.intervention_stats else {},
            "t_statistic": self.t_statistic,
            "p_value": self.p_value,
            "percentage_change": self.percentage_change,
            "causal_limitations": json.loads(self.causal_limitations) if self.causal_limitations else [],
            "conclusion": self.conclusion
        }

class PrivacyLogDB(Base):
    __tablename__ = "privacy_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True, default="user_default")
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, default="{}")
