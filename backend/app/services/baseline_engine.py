from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from backend.app.models.db_models import DataRecordDB
from backend.app.models.schema import BaselineMetric, DailySummary

class BaselineEngine:
    @staticmethod
    def get_daily_summaries(db: Session, user_id: str = "user_default", days: int = 45) -> List[DailySummary]:
        """
        Aggregates raw data records into a structured daily summary time-series.
        """
        records = db.query(DataRecordDB).filter(
            DataRecordDB.user_id == user_id
        ).order_by(DataRecordDB.timestamp.asc()).all()

        daily_map: Dict[str, Dict[str, List[float]]] = {}
        for r in records:
            day_str = r.timestamp.strftime("%Y-%m-%d")
            if day_str not in daily_map:
                daily_map[day_str] = {}
            if r.metric not in daily_map[day_str]:
                daily_map[day_str][r.metric] = []
            daily_map[day_str][r.metric].append(r.value)

        summaries = []
        # Sort days chronologically
        sorted_days = sorted(daily_map.keys())
        # Filter to requested window if provided
        if days and len(sorted_days) > days:
            sorted_days = sorted_days[-days:]

        for d in sorted_days:
            metrics = daily_map[d]
            # Sleep: take sum if fragments or max/avg
            sleep_vals = metrics.get("sleep_duration", [])
            sleep_duration = round(float(np.sum(sleep_vals)), 2) if sleep_vals else None

            # Steps: sum of steps for the day
            step_vals = metrics.get("step_count", [])
            step_count = round(float(np.sum(step_vals)), 0) if step_vals else None

            # Screen time: sum of hours
            screen_vals = metrics.get("screen_time", [])
            screen_time = round(float(np.sum(screen_vals)), 2) if screen_vals else None

            # Resting Heart Rate: mean of readings
            rhr_vals = metrics.get("resting_heart_rate", [])
            rhr = round(float(np.mean(rhr_vals)), 1) if rhr_vals else None

            # Active minutes
            active_vals = metrics.get("active_minutes", [])
            active_min = round(float(np.sum(active_vals)), 1) if active_vals else None

            summaries.append(DailySummary(
                date=d,
                sleep_duration=sleep_duration,
                step_count=step_count,
                screen_time=screen_time,
                resting_heart_rate=rhr,
                active_minutes=active_min
            ))

        return summaries

    @staticmethod
    def calculate_baselines(db: Session, user_id: str = "user_default", window_days: int = 30) -> Dict[str, BaselineMetric]:
        """
        Calculates personal baseline statistics (mean, std, median, min, max, n) for each metric over window.
        """
        summaries = BaselineEngine.get_daily_summaries(db, user_id=user_id, days=window_days)
        metrics_list = ["sleep_duration", "step_count", "screen_time", "resting_heart_rate", "active_minutes"]
        units = {
            "sleep_duration": "hours",
            "step_count": "steps",
            "screen_time": "hours",
            "resting_heart_rate": "bpm",
            "active_minutes": "minutes"
        }

        baselines: Dict[str, BaselineMetric] = {}
        for m in metrics_list:
            vals = [getattr(s, m) for s in summaries if getattr(s, m) is not None]
            if not vals:
                continue
            arr = np.array(vals, dtype=float)
            baselines[m] = BaselineMetric(
                metric=m,
                mean=round(float(np.mean(arr)), 2),
                std=round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 2),
                median=round(float(np.median(arr)), 2),
                min_val=round(float(np.min(arr)), 2),
                max_val=round(float(np.max(arr)), 2),
                unit=units.get(m, "units"),
                n_days=len(arr),
                window_days=window_days,
                last_updated=datetime.utcnow()
            )

        return baselines
