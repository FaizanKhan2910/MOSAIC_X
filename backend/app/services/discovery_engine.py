import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from scipy import stats
from sqlalchemy.orm import Session
from backend.app.models.db_models import DiscoveryDB, MissingContextDB
from backend.app.models.schema import DiscoveryItem, MissingContextQuestion
from backend.app.services.baseline_engine import BaselineEngine

class DiscoveryEngine:
    MIN_SAMPLE_SIZE = 7

    @staticmethod
    def analyze_patterns(db: Session, user_id: str = "user_default") -> List[DiscoveryItem]:
        """
        Runs comprehensive statistical correlation and pattern discovery across personal data signals.
        Evaluates:
        1. Sleep Duration (night t) vs Step Count (day t+1) (Lag-1 relationship)
        2. Screen Time (day t) vs Sleep Duration (night t) (Same-day impact)
        3. Step Count (day t) vs Resting Heart Rate (night t+1 / day t+1)
        """
        summaries = BaselineEngine.get_daily_summaries(db, user_id=user_id, days=60)
        if len(summaries) < DiscoveryEngine.MIN_SAMPLE_SIZE:
            return []

        discoveries: List[DiscoveryItem] = []

        # 1. Pattern: Sleep Duration (t) vs Next-day Activity (t+1)
        sleep_vs_activity = DiscoveryEngine._evaluate_lagged_correlation(
            summaries=summaries,
            signal_a="sleep_duration",
            signal_b="step_count",
            lag=1,
            title="Sleep Duration & Next-Day Physical Activity",
            direction_desc="higher step counts on days following longer sleep",
            inverse_desc="lower physical activity following nights with shorter sleep duration"
        )
        if sleep_vs_activity:
            discoveries.append(sleep_vs_activity)

        # 2. Pattern: Screen Time (t) vs Sleep Duration (t)
        screen_vs_sleep = DiscoveryEngine._evaluate_same_day_correlation(
            summaries=summaries,
            signal_a="screen_time",
            signal_b="sleep_duration",
            title="Evening Screen Exposure & Sleep Duration",
            direction_desc="longer sleep on days with higher screen time",
            inverse_desc="decreased sleep duration on days characterized by elevated screen exposure"
        )
        if screen_vs_sleep:
            discoveries.append(screen_vs_sleep)

        # 3. Pattern: Step Count (t) vs Resting Heart Rate (t+1)
        activity_vs_rhr = DiscoveryEngine._evaluate_lagged_correlation(
            summaries=summaries,
            signal_a="step_count",
            signal_b="resting_heart_rate",
            lag=1,
            title="Daily Physical Activity & Next-Day Resting Heart Rate",
            direction_desc="elevated resting heart rate following high activity days",
            inverse_desc="modest decreases in resting heart rate following active days"
        )
        if activity_vs_rhr:
            discoveries.append(activity_vs_rhr)

        # Sync discoveries to database and check for missing context questions
        persisted_discoveries: List[DiscoveryItem] = []
        for disc in discoveries:
            existing = db.query(DiscoveryDB).filter(
                DiscoveryDB.user_id == user_id,
                DiscoveryDB.signal_a == disc.signal_a,
                DiscoveryDB.signal_b == disc.signal_b
            ).first()

            if not existing:
                context_q_id = None
                has_q = False
                # If strong or moderate, formulate a context question
                if disc.statistical_strength in ["Moderate", "Strong"]:
                    has_q = True
                    context_q_id = f"ctx-{uuid.uuid4().hex[:8]}"
                    q_text, opts = DiscoveryEngine._generate_context_question_spec(disc)
                    ctx_record = MissingContextDB(
                        id=context_q_id,
                        user_id=user_id,
                        discovery_id=disc.id,
                        question_text=q_text,
                        target_metric=disc.signal_b,
                        observed_anomaly_period=disc.observation_window,
                        options=json.dumps(opts),
                        status="pending"
                    )
                    db.add(ctx_record)

                db_disc = DiscoveryDB(
                    id=disc.id,
                    user_id=user_id,
                    title=disc.title,
                    observation=disc.observation,
                    signal_a=disc.signal_a,
                    signal_b=disc.signal_b,
                    observation_window=disc.observation_window,
                    valid_observations=disc.valid_observations,
                    correlation_coefficient=disc.correlation_coefficient,
                    p_value=disc.p_value,
                    statistical_strength=disc.statistical_strength,
                    effect_size=disc.effect_size,
                    confidence_limitations=json.dumps(disc.confidence_limitations),
                    possible_alternative_explanations=json.dumps(disc.possible_alternative_explanations),
                    plain_language_explanation=disc.plain_language_explanation,
                    has_missing_context_question=has_q,
                    context_question_id=context_q_id
                )
                db.add(db_disc)
                disc.has_missing_context_question = has_q
                disc.context_question_id = context_q_id
                persisted_discoveries.append(disc)
            else:
                disc.id = existing.id
                disc.has_missing_context_question = existing.has_missing_context_question
                disc.context_question_id = existing.context_question_id
                persisted_discoveries.append(disc)

        db.commit()
        return persisted_discoveries

    @staticmethod
    def _evaluate_lagged_correlation(
        summaries: List[Any],
        signal_a: str,
        signal_b: str,
        lag: int,
        title: str,
        direction_desc: str,
        inverse_desc: str
    ) -> Optional[DiscoveryItem]:
        pairs_a = []
        pairs_b = []

        for i in range(len(summaries) - lag):
            val_a = getattr(summaries[i], signal_a)
            val_b = getattr(summaries[i + lag], signal_b)
            if val_a is not None and val_b is not None:
                pairs_a.append(val_a)
                pairs_b.append(val_b)

        if len(pairs_a) < DiscoveryEngine.MIN_SAMPLE_SIZE:
            return None

        arr_a = np.array(pairs_a, dtype=float)
        arr_b = np.array(pairs_b, dtype=float)

        # Check for non-zero variance
        if np.std(arr_a) < 1e-5 or np.std(arr_b) < 1e-5:
            return None

        r, p_val = stats.pearsonr(arr_a, arr_b)
        spearman_r, _ = stats.spearmanr(arr_a, arr_b)

        # Statistical classification
        abs_r = abs(r)
        if abs_r >= 0.5 and p_val < 0.05:
            strength = "Strong"
            effect = f"Large effect size (r = {r:.2f}, R² = {r**2:.2f})"
        elif abs_r >= 0.25 and p_val < 0.10:
            strength = "Moderate"
            effect = f"Moderate effect size (r = {r:.2f}, R² = {r**2:.2f})"
        else:
            strength = "Weak"
            effect = f"Weak association (r = {r:.2f})"

        obs_desc = direction_desc if r > 0 else inverse_desc
        window_str = f"{summaries[0].date} to {summaries[-1].date}"

        observation = (
            f"Over {len(pairs_a)} matched observation days, NEXORA detected {obs_desc}. "
            f"Linear correlation coefficient r = {r:.2f} (p = {p_val:.4f})."
        )

        limitations = [
            "Observational data only; statistical correlation does NOT establish biological or behavioral causality.",
            "Potential unmeasured confounders (e.g. work deadlines, caffeine, emotional stress, ambient weather) were not controlled for.",
            f"Small personal sample size (N={len(pairs_a)} days); findings reflect idiosyncratic personal patterns rather than general clinical truth."
        ]

        alternatives = [
            "Workload pressure or travel schedules could simultaneously reduce sleep and restrict time available for physical activity.",
            "Fatigue from intense exercise on day t could reduce activity on day t+1 irrespective of prior sleep.",
            "Day of week variation (e.g. weekend vs weekday schedules) may synchronize both variables artificially."
        ]

        explanation = (
            f"When evaluating your {signal_a.replace('_', ' ')} against next-day {signal_b.replace('_', ' ')}, "
            f"we observed a {strength.lower()} statistical pattern (r={r:.2f}, p={p_val:.3f}). "
            f"While the mathematical association is notable, correlation does not indicate causation. "
            f"Third factors like calendar commitments or illness often drive both signals simultaneously."
        )

        return DiscoveryItem(
            id=f"disc-{uuid.uuid4().hex[:8]}",
            title=title,
            observation=observation,
            signal_a=signal_a,
            signal_b=signal_b,
            observation_window=window_str,
            valid_observations=len(pairs_a),
            correlation_coefficient=round(float(r), 3),
            p_value=round(float(p_val), 4),
            statistical_strength=strength,
            effect_size=effect,
            confidence_limitations=limitations,
            possible_alternative_explanations=alternatives,
            plain_language_explanation=explanation,
            has_missing_context_question=False
        )

    @staticmethod
    def _evaluate_same_day_correlation(
        summaries: List[Any],
        signal_a: str,
        signal_b: str,
        title: str,
        direction_desc: str,
        inverse_desc: str
    ) -> Optional[DiscoveryItem]:
        pairs_a = []
        pairs_b = []

        for s in summaries:
            val_a = getattr(s, signal_a)
            val_b = getattr(s, signal_b)
            if val_a is not None and val_b is not None:
                pairs_a.append(val_a)
                pairs_b.append(val_b)

        if len(pairs_a) < DiscoveryEngine.MIN_SAMPLE_SIZE:
            return None

        arr_a = np.array(pairs_a, dtype=float)
        arr_b = np.array(pairs_b, dtype=float)

        if np.std(arr_a) < 1e-5 or np.std(arr_b) < 1e-5:
            return None

        r, p_val = stats.pearsonr(arr_a, arr_b)

        abs_r = abs(r)
        if abs_r >= 0.5 and p_val < 0.05:
            strength = "Strong"
            effect = f"Large effect size (r = {r:.2f}, R² = {r**2:.2f})"
        elif abs_r >= 0.25 and p_val < 0.10:
            strength = "Moderate"
            effect = f"Moderate effect size (r = {r:.2f}, R² = {r**2:.2f})"
        else:
            strength = "Weak"
            effect = f"Weak association (r = {r:.2f})"

        obs_desc = direction_desc if r > 0 else inverse_desc
        window_str = f"{summaries[0].date} to {summaries[-1].date}"

        observation = (
            f"Across {len(pairs_a)} recorded days, NEXORA observed {obs_desc}. "
            f"Pearson r = {r:.2f} (two-tailed p = {p_val:.4f})."
        )

        limitations = [
            "Passive smartphone screen tracking does not distinguish between active reading, passive streaming, or professional productivity.",
            "Reverse causality is plausible: difficulty falling asleep may cause extended screen usage, rather than vice versa.",
            "Circadian phase shifts and ambient room lighting were not logged."
        ]

        alternatives = [
            "Late night work deadlines could lead to both high screen time and truncated sleep windows.",
            "Insomnia or psychological rumination may prompt screen viewing as an entertainment coping mechanism.",
            "Weekend social schedules often postpone both bedtime and device lock times."
        ]

        explanation = (
            f"Analysis of your daily {signal_a.replace('_', ' ')} and {signal_b.replace('_', ' ')} revealed a {strength.lower()} "
            f"association (r={r:.2f}, p={p_val:.3f}). Before assuming screens directly shortened your sleep, "
            f"NEXORA considers whether situational drivers like project deadlines or insomnia preceded device usage."
        )

        return DiscoveryItem(
            id=f"disc-{uuid.uuid4().hex[:8]}",
            title=title,
            observation=observation,
            signal_a=signal_a,
            signal_b=signal_b,
            observation_window=window_str,
            valid_observations=len(pairs_a),
            correlation_coefficient=round(float(r), 3),
            p_value=round(float(p_val), 4),
            statistical_strength=strength,
            effect_size=effect,
            confidence_limitations=limitations,
            possible_alternative_explanations=alternatives,
            plain_language_explanation=explanation,
            has_missing_context_question=False
        )

    @staticmethod
    def _generate_context_question_spec(disc: DiscoveryItem) -> Tuple[str, List[str]]:
        if "Sleep Duration & Next-Day Physical Activity" in disc.title:
            q_text = (
                "NEXORA noticed lower physical activity following days with shorter sleep. "
                "During those low-sleep intervals, were any of these situational factors present?"
            )
            opts = [
                "Unusually high professional workload or exams",
                "Travel or transit days",
                "Acute illness or physical recovery",
                "Intentional rest / bad weather",
                "Nothing unusual (typical routine)",
                "Prefer not to say"
            ]
            return q_text, opts
        elif "Screen Exposure" in disc.title:
            q_text = (
                "On evenings with elevated screen time, what was the primary nature of your device usage?"
            )
            opts = [
                "Work deadlines / urgent communications",
                "Leisure streaming / video games",
                "Difficulty sleeping (using phone to pass time)",
                "Social messaging with family/friends",
                "Prefer not to say"
            ]
            return q_text, opts
        else:
            q_text = (
                f"We observed changes in your {disc.signal_b.replace('_', ' ')}. "
                "Did an unmeasured event occur during this observation period?"
            )
            opts = [
                "High stress or schedule disruption",
                "Change in medication or diet",
                "Travel across time zones",
                "Standard routine",
                "Prefer not to say"
            ]
            return q_text, opts
