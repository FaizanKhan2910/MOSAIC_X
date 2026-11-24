import io
import json
import csv
from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.schema import DataRecordBase
from backend.app.models.db_models import DataRecordDB, PrivacyLogDB

METRIC_RANGES = {
    "sleep_duration": {"min": 1.0, "max": 18.0, "unit": "hours", "default_source": "smartwatch"},
    "step_count": {"min": 0.0, "max": 60000.0, "unit": "steps", "default_source": "smartphone"},
    "screen_time": {"min": 0.0, "max": 20.0, "unit": "hours", "default_source": "smartphone"},
    "resting_heart_rate": {"min": 35.0, "max": 160.0, "unit": "bpm", "default_source": "smartwatch"},
    "active_minutes": {"min": 0.0, "max": 720.0, "unit": "minutes", "default_source": "fitness_tracker"}
}

class IngestionPipeline:
    @staticmethod
    def validate_and_normalize(record: DataRecordBase) -> Tuple[bool, str, float]:
        """
        Validates record schema, ranges, and computes data quality score.
        Returns: (is_valid, error_reason, quality_score)
        """
        metric = record.metric.strip().lower()
        if metric not in METRIC_RANGES:
            # Allow custom metrics but with modest quality score
            return True, "", 0.75

        rule = METRIC_RANGES[metric]
        if record.value < rule["min"] or record.value > rule["max"]:
            return False, f"Value {record.value} for {metric} out of expected physiological range [{rule['min']}, {rule['max']}] {rule['unit']}", 0.0

        # Normalization of units
        unit = record.unit.strip().lower()
        norm_value = record.value

        # Example normalization: minutes to hours for sleep if given in minutes
        if metric == "sleep_duration" and unit in ["min", "minutes", "mins"] and norm_value > 24:
            norm_value = norm_value / 60.0
            unit = "hours"

        # Quality scoring
        quality = 1.0
        # Device source confidence weighting
        if record.source.lower() in ["smartwatch", "health_connect", "apple_health"]:
            quality = 0.95
        elif record.source.lower() in ["smartphone", "fitness_tracker"]:
            quality = 0.90
        elif record.source.lower() == "manual":
            quality = 0.80
        else:
            quality = 0.70

        return True, "", quality

    @classmethod
    def ingest_record(cls, db: Session, record_data: DataRecordBase) -> DataRecordDB:
        is_valid, reason, quality = cls.validate_and_normalize(record_data)
        if not is_valid:
            raise ValueError(f"Data ingestion rejected: {reason}")

        db_record = DataRecordDB(
            user_id=record_data.user_id,
            source=record_data.source,
            metric=record_data.metric.strip().lower(),
            value=record_data.value,
            unit=record_data.unit,
            timestamp=record_data.timestamp or datetime.utcnow(),
            quality=quality,
            consent_scope=record_data.consent_scope,
            meta_info=json.dumps(record_data.metadata or {})
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return db_record

    @classmethod
    def ingest_batch(cls, db: Session, records: List[DataRecordBase]) -> List[DataRecordDB]:
        db_records = []
        for r in records:
            is_valid, _, quality = cls.validate_and_normalize(r)
            if is_valid:
                db_record = DataRecordDB(
                    user_id=r.user_id,
                    source=r.source,
                    metric=r.metric.strip().lower(),
                    value=r.value,
                    unit=r.unit,
                    timestamp=r.timestamp or datetime.utcnow(),
                    quality=quality,
                    consent_scope=r.consent_scope,
                    meta_info=json.dumps(r.metadata or {})
                )
                db.add(db_record)
                db_records.append(db_record)
        db.commit()
        for r in db_records:
            db.refresh(r)

        # Log to privacy audit
        audit = PrivacyLogDB(
            user_id=records[0].user_id if records else "user_default",
            action="DATA_INGESTION_BATCH",
            target="data_records",
            details=json.dumps({"count": len(db_records)})
        )
        db.add(audit)
        db.commit()

        return db_records

    @classmethod
    def parse_csv(cls, user_id: str, csv_content: str, default_source: str = "csv_import") -> List[DataRecordBase]:
        """
        Parses CSV with header detection for columns:
        timestamp/date, metric, value, unit, source
        or wide format: date, sleep_duration, step_count, screen_time, resting_heart_rate
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        records = []
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]

        is_wide_format = any(m in headers for m in METRIC_RANGES.keys())

        if is_wide_format:
            date_col = next((c for c in headers if c in ["date", "timestamp", "time", "day"]), "date")
            for row in reader:
                ts_str = row.get(date_col, "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except Exception:
                    try:
                        ts = datetime.strptime(ts_str, "%Y-%m-%d")
                    except Exception:
                        ts = datetime.utcnow()

                for metric, config in METRIC_RANGES.items():
                    if metric in row and row[metric] not in [None, "", "null", "NaN"]:
                        try:
                            val = float(row[metric])
                            records.append(DataRecordBase(
                                user_id=user_id,
                                source=config["default_source"],
                                metric=metric,
                                value=val,
                                unit=config["unit"],
                                timestamp=ts,
                                quality=0.9,
                                consent_scope="vital_analytics"
                            ))
                        except ValueError:
                            continue
        else:
            for row in reader:
                metric = row.get("metric", "").strip().lower()
                val_str = row.get("value", "")
                if not metric or not val_str:
                    continue
                try:
                    val = float(val_str)
                    ts_str = row.get("timestamp") or row.get("date") or ""
                    try:
                        ts = datetime.fromisoformat(ts_str)
                    except Exception:
                        ts = datetime.utcnow()

                    records.append(DataRecordBase(
                        user_id=user_id,
                        source=row.get("source", default_source),
                        metric=metric,
                        value=val,
                        unit=row.get("unit", METRIC_RANGES.get(metric, {}).get("unit", "units")),
                        timestamp=ts,
                        quality=float(row.get("quality", 0.9)),
                        consent_scope=row.get("consent_scope", "vital_analytics")
                    ))
                except ValueError:
                    continue

        return records
