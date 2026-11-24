import uuid
from typing import List, Dict, Any
import numpy as np
from scipy import stats
from sqlalchemy.orm import Session
from backend.app.models.schema import WhatIfSimulationRequest, WhatIfSimulationResult
from backend.app.services.baseline_engine import BaselineEngine

class SimulationEngine:
    @staticmethod
    def simulate_scenario(db: Session, request: WhatIfSimulationRequest, user_id: str = "user_default") -> WhatIfSimulationResult:
        """
        Calculates an empirical what-if scenario based on personal regression slope and confidence bounds.
        E.g., what if sleep increases by 0.5 hours for 7 days -> impact on step count.
        """
        baselines = BaselineEngine.calculate_baselines(db, user_id=user_id, window_days=45)
        summaries = BaselineEngine.get_daily_summaries(db, user_id=user_id, days=45)

        target_base = baselines.get(request.target_metric)
        interv_base = baselines.get(request.intervention_metric)

        current_baseline_val = target_base.mean if target_base else 8000.0
        n_obs = len(summaries)

        # Extract paired points to calculate empirical sensitivity
        x_vals = []
        y_vals = []
        lag = 1 if request.intervention_metric == "sleep_duration" and request.target_metric == "step_count" else 0

        for i in range(len(summaries) - lag):
            x = getattr(summaries[i], request.intervention_metric)
            y = getattr(summaries[i + lag], request.target_metric)
            if x is not None and y is not None:
                x_vals.append(x)
                y_vals.append(y)

        if len(x_vals) >= 7 and np.std(x_vals) > 1e-4:
            slope, intercept, r_val, p_val, std_err = stats.linregress(x_vals, y_vals)
            r2 = r_val ** 2
        else:
            # Fallback biological estimate if insufficient paired data
            if request.intervention_metric == "sleep_duration" and request.target_metric == "step_count":
                slope = 750.0  # ~750 steps per additional hour of sleep
                std_err = 200.0
                r2 = 0.25
            else:
                slope = 0.0
                std_err = 0.0
                r2 = 0.05

        # Projected impact for delta
        projected_mean_change = slope * request.delta_value

        # Calculate 95% Confidence Interval for the slope
        t_critical = stats.t.ppf(0.975, df=max(len(x_vals) - 2, 5))
        margin_of_error = t_critical * std_err * abs(request.delta_value)

        scenario_range = {
            "low": round(float(current_baseline_val + projected_mean_change - margin_of_error), 1),
            "mid": round(float(current_baseline_val + projected_mean_change), 1),
            "high": round(float(current_baseline_val + projected_mean_change + margin_of_error), 1)
        }

        # Uncertainty classification
        if r2 >= 0.4 and len(x_vals) >= 20:
            uncertainty = "Low"
        elif r2 >= 0.15 and len(x_vals) >= 10:
            uncertainty = "Moderate"
        else:
            uncertainty = "High"

        assumptions = [
            f"Linear responsiveness holds within the proposed delta range ({request.delta_value:+} {request.intervention_metric}).",
            "Ceteris paribus assumption: no concurrent shifts in acute illness, work stress, travel, or nutritional intake.",
            f"Behavior is maintained consistently across the selected {request.duration_days}-day duration window."
        ]

        data_needed = [
            f"Daily {request.intervention_metric.replace('_', ' ')} logs during the {request.duration_days}-day experimental period.",
            f"Concurrent daily tracking of {request.target_metric.replace('_', ' ')}.",
            "Subjective context reporting to account for potential confounding life events (travel, sickness, overtime work)."
        ]

        disclaimer = (
            "NOTICE: This is an empirical scenario projection derived from observational personal data. "
            "It is NOT a medical diagnosis, clinical prediction, or guaranteed behavioral outcome. "
            "Real-world physiological adaptation is influenced by complex unmeasured systemic factors."
        )

        return WhatIfSimulationResult(
            scenario_id=f"sim-{uuid.uuid4().hex[:8]}",
            intervention_metric=request.intervention_metric,
            delta_value=request.delta_value,
            duration_days=request.duration_days,
            target_metric=request.target_metric,
            current_baseline_target=round(float(current_baseline_val), 1),
            estimated_target_change=round(float(projected_mean_change), 1),
            predicted_scenario_range=scenario_range,
            uncertainty_level=uncertainty,
            assumptions=assumptions,
            required_data_to_verify=data_needed,
            scientific_disclaimer=disclaimer
        )
