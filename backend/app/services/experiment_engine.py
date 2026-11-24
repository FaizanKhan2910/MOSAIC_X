import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import numpy as np
from scipy import stats
from sqlalchemy.orm import Session
from backend.app.models.db_models import ExperimentDB, PrivacyLogDB
from backend.app.models.schema import ExperimentCreate, ExperimentRecord
from backend.app.services.baseline_engine import BaselineEngine

class ExperimentEngine:
    @staticmethod
    def create_experiment(db: Session, user_id: str, exp_data: ExperimentCreate) -> ExperimentRecord:
        start_date = datetime.utcnow().strftime("%Y-%m-%d")
        end_date = (datetime.utcnow() + timedelta(days=exp_data.duration_days)).strftime("%Y-%m-%d")

        # Compute pre-intervention baseline stats for target metric
        baselines = BaselineEngine.calculate_baselines(db, user_id=user_id, window_days=21)
        target_base = baselines.get(exp_data.target_metric)
        base_stats = {
            "mean": target_base.mean if target_base else 0.0,
            "std": target_base.std if target_base else 0.0,
            "n_days": target_base.n_days if target_base else 0
        }

        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        limitations = [
            "N=1 personal trial without a concurrent control or sham comparison group.",
            "Potential regression to the mean: natural behavioral fluctuations may coincide with intervention timing.",
            "Expectancy and Hawthorne effects: conscious tracking often alters routines independently of the intervention."
        ]

        db_exp = ExperimentDB(
            id=exp_id,
            user_id=user_id,
            title=exp_data.title,
            goal=exp_data.goal,
            hypothesis=exp_data.hypothesis,
            intervention_metric=exp_data.intervention_metric,
            intervention_target_value=exp_data.intervention_target_value,
            target_metric=exp_data.target_metric,
            duration_days=exp_data.duration_days,
            status="active",
            start_date=start_date,
            end_date=end_date,
            days_elapsed=1,
            adherence_rate=1.0,
            baseline_stats=json.dumps(base_stats),
            intervention_stats=json.dumps({}),
            causal_limitations=json.dumps(limitations),
            conclusion=None
        )
        db.add(db_exp)

        audit = PrivacyLogDB(
            user_id=user_id,
            action="EXPERIMENT_CREATED",
            target=exp_id,
            details=json.dumps({"title": exp_data.title})
        )
        db.add(audit)
        db.commit()
        db.refresh(db_exp)

        return ExperimentRecord(
            id=db_exp.id,
            user_id=db_exp.user_id,
            title=db_exp.title,
            goal=db_exp.goal,
            hypothesis=db_exp.hypothesis,
            intervention_metric=db_exp.intervention_metric,
            intervention_target_value=db_exp.intervention_target_value,
            target_metric=db_exp.target_metric,
            duration_days=db_exp.duration_days,
            status=db_exp.status,
            start_date=db_exp.start_date,
            end_date=db_exp.end_date,
            days_elapsed=db_exp.days_elapsed,
            adherence_rate=db_exp.adherence_rate,
            baseline_stats=base_stats,
            intervention_stats={},
            causal_limitations=limitations
        )

    @staticmethod
    def get_experiments(db: Session, user_id: str = "user_default") -> List[ExperimentRecord]:
        records = db.query(ExperimentDB).filter(
            ExperimentDB.user_id == user_id
        ).order_by(ExperimentDB.created_at.desc()).all()

        results = []
        for r in records:
            results.append(ExperimentRecord(
                id=r.id,
                user_id=r.user_id,
                title=r.title,
                goal=r.goal,
                hypothesis=r.hypothesis,
                intervention_metric=r.intervention_metric,
                intervention_target_value=r.intervention_target_value,
                target_metric=r.target_metric,
                duration_days=r.duration_days,
                status=r.status,
                start_date=r.start_date,
                end_date=r.end_date,
                days_elapsed=r.days_elapsed,
                adherence_rate=r.adherence_rate,
                baseline_stats=json.loads(r.baseline_stats) if r.baseline_stats else {},
                intervention_stats=json.loads(r.intervention_stats) if r.intervention_stats else {},
                t_statistic=r.t_statistic,
                p_value=r.p_value,
                percentage_change=r.percentage_change,
                causal_limitations=json.loads(r.causal_limitations) if r.causal_limitations else [],
                conclusion=r.conclusion
            ))
        return results

    @staticmethod
    def evaluate_experiment_outcome(db: Session, experiment_id: str, user_id: str = "user_default") -> ExperimentRecord:
        exp = db.query(ExperimentDB).filter(
            ExperimentDB.id == experiment_id,
            ExperimentDB.user_id == user_id
        ).first()

        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Load summaries to evaluate baseline vs intervention periods
        summaries = BaselineEngine.get_daily_summaries(db, user_id=user_id, days=60)
        
        # Partition into pre-start and post-start
        pre_vals = []
        post_vals = []
        adherence_hits = 0

        for s in summaries:
            val_target = getattr(s, exp.target_metric)
            val_interv = getattr(s, exp.intervention_metric)
            if s.date < exp.start_date:
                if val_target is not None:
                    pre_vals.append(val_target)
            elif exp.start_date <= s.date <= exp.end_date:
                if val_target is not None:
                    post_vals.append(val_target)
                if val_interv is not None:
                    if exp.intervention_metric == "sleep_duration" and val_interv >= exp.intervention_target_value:
                        adherence_hits += 1
                    elif exp.intervention_metric == "screen_time" and val_interv <= exp.intervention_target_value:
                        adherence_hits += 1

        adherence = round(adherence_hits / max(len(post_vals), 1), 2)
        exp.adherence_rate = adherence
        exp.days_elapsed = len(post_vals)

        if len(pre_vals) >= 3 and len(post_vals) >= 3:
            t_stat, p_val = stats.ttest_ind(post_vals, pre_vals, equal_var=False)
            pre_mean = float(np.mean(pre_vals))
            post_mean = float(np.mean(post_vals))
            pct_change = round(((post_mean - pre_mean) / pre_mean) * 100.0, 1) if pre_mean != 0 else 0.0

            interv_stats = {
                "mean": round(post_mean, 2),
                "std": round(float(np.std(post_vals, ddof=1)), 2),
                "n_days": len(post_vals)
            }

            exp.intervention_stats = json.dumps(interv_stats)
            exp.t_statistic = round(float(t_stat), 3)
            exp.p_value = round(float(p_val), 4)
            exp.percentage_change = pct_change

            sig_text = "statistically significant" if p_val < 0.05 else "not statistically significant at alpha=0.05"
            direction = "increase" if pct_change > 0 else "decrease"
            exp.conclusion = (
                f"During the intervention phase, {exp.target_metric.replace('_', ' ')} showed an observed {abs(pct_change)}% {direction} "
                f"(baseline mean: {pre_mean:.1f} vs intervention mean: {post_mean:.1f}, p={p_val:.3f}). "
                f"This shift is {sig_text}. Due to N=1 observational conditions and lack of blinded controls, "
                f"this observation demonstrates association within your personal routine rather than definitive causality."
            )
            if exp.days_elapsed >= exp.duration_days:
                exp.status = "completed"

            db.commit()
            db.refresh(exp)

        return ExperimentRecord(
            id=exp.id,
            user_id=exp.user_id,
            title=exp.title,
            goal=exp.goal,
            hypothesis=exp.hypothesis,
            intervention_metric=exp.intervention_metric,
            intervention_target_value=exp.intervention_target_value,
            target_metric=exp.target_metric,
            duration_days=exp.duration_days,
            status=exp.status,
            start_date=exp.start_date,
            end_date=exp.end_date,
            days_elapsed=exp.days_elapsed,
            adherence_rate=exp.adherence_rate,
            baseline_stats=json.loads(exp.baseline_stats) if exp.baseline_stats else {},
            intervention_stats=json.loads(exp.intervention_stats) if exp.intervention_stats else {},
            t_statistic=exp.t_statistic,
            p_value=exp.p_value,
            percentage_change=exp.percentage_change,
            causal_limitations=json.loads(exp.causal_limitations) if exp.causal_limitations else [],
            conclusion=exp.conclusion
        )
