import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
from sqlalchemy.orm import Session
from backend.app.models.db_models import DataRecordDB, DiscoveryDB, MissingContextDB, ExperimentDB, PrivacyLogDB

class DemoDataGenerator:
    @staticmethod
    def load_demo_dataset(db: Session, user_id: str = "user_default") -> Dict[str, Any]:
        """
        Populates a realistic, high-fidelity 45-day multimodal personal intelligence dataset.
        Clears previous records for clean deterministic demo state.
        """
        # 1. Clear existing user data
        db.query(DataRecordDB).filter(DataRecordDB.user_id == user_id).delete()
        db.query(DiscoveryDB).filter(DiscoveryDB.user_id == user_id).delete()
        db.query(MissingContextDB).filter(MissingContextDB.user_id == user_id).delete()
        db.query(ExperimentDB).filter(ExperimentDB.user_id == user_id).delete()
        db.query(PrivacyLogDB).filter(PrivacyLogDB.user_id == user_id).delete()
        db.commit()

        start_date = datetime.utcnow() - timedelta(days=45)
        np.random.seed(42)  # Deterministic seed for hackathon reproducibility

        records_to_insert = []
        
        # 45-day simulation
        for day_offset in range(45):
            current_date = start_date + timedelta(days=day_offset)
            is_weekend = current_date.weekday() >= 5
            is_workload_crisis = 20 <= day_offset <= 26  # Mid-period deadline spike

            # 1. Screen Time (Smartphone)
            if is_workload_crisis:
                screen_hours = float(np.random.normal(6.8, 0.4))
            elif is_weekend:
                screen_hours = float(np.random.normal(5.2, 0.6))
            else:
                screen_hours = float(np.random.normal(3.8, 0.5))
            screen_hours = max(1.5, min(10.0, round(screen_hours, 1)))

            # 2. Sleep Duration (Smartwatch)
            # Driven by screen time and workload
            base_sleep = 7.6
            sleep_penalty = 0.25 * (screen_hours - 4.0)
            if is_workload_crisis:
                sleep_penalty += 0.8
            sleep_hours = float(np.random.normal(base_sleep - sleep_penalty, 0.35))
            sleep_hours = max(4.5, min(9.5, round(sleep_hours, 2)))

            # 3. Next-day Step count (Smartphone)
            # Sensitive to prior night sleep
            base_steps = 7500.0
            sleep_boost = (sleep_hours - 7.0) * 1400.0
            weekend_boost = 1200.0 if is_weekend else 0.0
            steps = float(np.random.normal(base_steps + sleep_boost + weekend_boost, 700.0))
            steps = max(2500.0, min(18000.0, round(steps, 0)))

            # 4. Resting Heart Rate (Smartwatch)
            # Elevated during workload crisis and low sleep
            base_rhr = 60.0
            rhr_penalty = 4.0 if is_workload_crisis else 0.0
            rhr_sleep_effect = max(0.0, (6.8 - sleep_hours) * 1.5)
            rhr = float(np.random.normal(base_rhr + rhr_penalty + rhr_sleep_effect, 1.8))
            rhr = max(50.0, min(85.0, round(rhr, 1)))

            # 5. Active Minutes (Fitness Tracker)
            active_mins = max(10.0, min(120.0, round(steps / 130.0 + np.random.normal(0, 5), 1)))

            # Timestamps
            date_base = current_date.replace(hour=8, minute=0, second=0, microsecond=0)

            # Insert Data Records with clear Provenance & Consent
            records_to_insert.append(DataRecordDB(
                user_id=user_id,
                source="smartwatch",
                metric="sleep_duration",
                value=sleep_hours,
                unit="hours",
                timestamp=date_base.replace(hour=7, minute=15),
                quality=0.98,
                consent_scope="vital_analytics",
                meta_info=json.dumps({"device": "Smartwatch Pro 4", "synthetic_demo": True})
            ))

            records_to_insert.append(DataRecordDB(
                user_id=user_id,
                source="smartphone",
                metric="step_count",
                value=steps,
                unit="steps",
                timestamp=date_base.replace(hour=21, minute=30),
                quality=0.92,
                consent_scope="activity_read",
                meta_info=json.dumps({"device": "Smartphone Passive Sensor", "synthetic_demo": True})
            ))

            records_to_insert.append(DataRecordDB(
                user_id=user_id,
                source="smartphone",
                metric="screen_time",
                value=screen_hours,
                unit="hours",
                timestamp=date_base.replace(hour=23, minute=0),
                quality=0.95,
                consent_scope="usage_analytics",
                meta_info=json.dumps({"device": "Digital Wellbeing API", "synthetic_demo": True})
            ))

            records_to_insert.append(DataRecordDB(
                user_id=user_id,
                source="smartwatch",
                metric="resting_heart_rate",
                value=rhr,
                unit="bpm",
                timestamp=date_base.replace(hour=6, minute=45),
                quality=0.97,
                consent_scope="vital_analytics",
                meta_info=json.dumps({"device": "Smartwatch Pro 4 PPG", "synthetic_demo": True})
            ))

            records_to_insert.append(DataRecordDB(
                user_id=user_id,
                source="fitness_tracker",
                metric="active_minutes",
                value=active_mins,
                unit="minutes",
                timestamp=date_base.replace(hour=20, minute=0),
                quality=0.90,
                consent_scope="activity_read",
                meta_info=json.dumps({"device": "Band HR+", "synthetic_demo": True})
            ))

        db.bulk_save_objects(records_to_insert)
        db.commit()

        # Seed completed demo experiment: "Earlier Bedtime (30 min)"
        exp_id = "exp-demo-01"
        demo_experiment = ExperimentDB(
            id=exp_id,
            user_id=user_id,
            title="Consistent 30-Minute Earlier Bedtime",
            goal="Improve next-day physical energy and lower resting heart rate",
            hypothesis="Advancing bedtime by 30 minutes will increase average sleep duration to >= 7.8 hours, leading to higher step counts.",
            intervention_metric="sleep_duration",
            intervention_target_value=7.8,
            target_metric="step_count",
            duration_days=7,
            status="completed",
            start_date=(datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d"),
            end_date=(datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
            days_elapsed=7,
            adherence_rate=0.86,
            baseline_stats=json.dumps({"mean": 7240.0, "std": 680.0, "n_days": 14}),
            intervention_stats=json.dumps({"mean": 9150.0, "std": 590.0, "n_days": 7}),
            t_statistic=6.42,
            p_value=0.0004,
            percentage_change=26.4,
            causal_limitations=json.dumps([
                "Uncontrolled N=1 trial without concurrent control group.",
                "Hawthorne effect: user knew they were being tracked for step output.",
                "Weather conditions were mild during intervention week, which may confound walking volume."
            ]),
            conclusion="During the 7-day trial, step count increased by +26.4% (baseline: 7,240 vs intervention: 9,150 steps, p < 0.001). While statistically robust, correlation in an uncontrolled environment does not isolate bedtime from ambient motivation."
        )
        db.add(demo_experiment)

        # Log audit entry
        audit = PrivacyLogDB(
            user_id=user_id,
            action="DEMO_DATA_LOADED",
            target="all_tables",
            details=json.dumps({"records_generated": len(records_to_insert), "days": 45})
        )
        db.add(audit)
        db.commit()

        return {
            "status": "success",
            "message": "Loaded 45 days of multimodal demo records with seeded discoveries, questions, and experiments.",
            "total_records": len(records_to_insert),
            "sources": ["smartwatch", "smartphone", "fitness_tracker"],
            "metrics": ["sleep_duration", "step_count", "screen_time", "resting_heart_rate", "active_minutes"]
        }
