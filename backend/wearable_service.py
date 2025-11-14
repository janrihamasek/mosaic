from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from extensions import db
from models import (
    WearableCanonicalHR,
    WearableCanonicalSleepSession,
    WearableCanonicalSleepStage,
    WearableCanonicalSteps,
    WearableDailyAgg,
    WearableRaw,
)

logger = structlog.get_logger("wearable.service")


class WearableNormalizationError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Optional[str], *, field: str) -> datetime:
    if not value:
        raise WearableNormalizationError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise WearableNormalizationError(f"Invalid datetime for {field}: {value}") from exc
    return _as_utc(parsed)


def _day_start(dt: datetime) -> datetime:
    dt = _as_utc(dt)
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)


def _day_range(start: datetime, end: datetime) -> Iterable[datetime]:
    current = _day_start(start)
    final = _day_start(end)
    while current <= final:
        yield current
        current += timedelta(days=1)


@dataclass(frozen=True)
class DayScope:
    user_id: int
    source_id: Optional[int]
    day_start: datetime


class WearableETLService:
    def __init__(self, session=None, *, log=None):
        self.session = session or db.session
        self.log = log or logger

    def process_raw_by_ids(self, raw_ids: Sequence[int]) -> dict:
        if not raw_ids:
            return {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
        rows = (
            self.session.query(WearableRaw)
            .filter(WearableRaw.id.in_(list(raw_ids)))
            .all()
        )
        return self.process_raw_rows(rows)

    def process_raw_rows(self, rows: Sequence[WearableRaw]) -> dict:
        stats = {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
        affected_days: Set[DayScope] = set()
        for row in rows:
            try:
                affected_days.update(self._process_raw_row(row))
                stats["processed"] += 1
            except WearableNormalizationError as exc:
                stats["skipped"] += 1
                stats["errors"].append({"raw_id": row.id, "reason": str(exc)})
                self.log.warning("wearable.normalize.skipped", raw_id=row.id, reason=str(exc))
        if affected_days:
            aggregator = WearableAggregator(self.session, log=self.log)
            for scope in sorted(affected_days, key=lambda d: (d.user_id, d.source_id or 0, d.day_start)):
                aggregator.upsert_day(scope.user_id, scope.source_id, scope.day_start)
            stats["aggregated"] = len(affected_days)
        self.session.flush()
        self.log.info(
            "wearable.normalize.summary",
            processed=stats["processed"],
            skipped=stats["skipped"],
            aggregated=stats["aggregated"],
            errors=len(stats["errors"]),
        )
        return stats

    def _process_raw_row(self, row: WearableRaw) -> Set[DayScope]:
        payload = row.payload
        if isinstance(payload, str):
            payload = json.loads(payload)
        record_type = (payload.get("type") or "").lower()
        if not record_type:
            raise WearableNormalizationError("Missing record type")
        if "fields" not in payload or not isinstance(payload["fields"], dict):
            raise WearableNormalizationError("Missing fields object in payload")
        if record_type in {"steps", "step_count"}:
            return self._handle_steps(row, payload)
        if record_type in {"heart_rate", "hr"}:
            return self._handle_heart_rate(row, payload)
        if record_type in {"sleep_session", "sleep"}:
            return self._handle_sleep_session(row, payload)
        if record_type in {"sleep_stage", "sleep_segment"}:
            return self._handle_sleep_stage(row, payload)
        raise WearableNormalizationError(f"Unsupported record type '{record_type}'")

    def _handle_steps(self, row: WearableRaw, payload: Dict) -> Set[DayScope]:
        start = _parse_datetime(payload.get("start"), field="start")
        end = _parse_datetime(payload.get("end") or payload.get("start"), field="end")
        if end < start:
            raise WearableNormalizationError("end cannot precede start for steps")
        fields = payload["fields"]
        try:
            steps = int(fields.get("steps", 0))
        except (TypeError, ValueError) as exc:
            raise WearableNormalizationError("steps must be an integer") from exc
        if steps < 0:
            raise WearableNormalizationError("steps must be non-negative")
        distance = fields.get("distance_m")
        if distance is not None:
            try:
                distance = float(distance)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("distance_m must be numeric") from exc
        active_minutes = fields.get("active_minutes")
        if active_minutes is not None:
            try:
                active_minutes = int(active_minutes)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("active_minutes must be integer") from exc

        values = {
            "user_id": row.user_id,
            "source_id": row.source_id,
            "raw_id": row.id,
            "start_time_utc": start,
            "end_time_utc": end,
            "steps": steps,
            "distance_meters": distance,
            "active_minutes": active_minutes,
            "dedupe_key": payload.get("dedupe_key") or row.dedupe_key,
        }
        stmt = insert(WearableCanonicalSteps).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "start_time_utc": stmt.excluded.start_time_utc,
                "end_time_utc": stmt.excluded.end_time_utc,
                "steps": stmt.excluded.steps,
                "distance_meters": stmt.excluded.distance_meters,
                "active_minutes": stmt.excluded.active_minutes,
                "raw_id": stmt.excluded.raw_id,
                "source_id": stmt.excluded.source_id,
                "user_id": stmt.excluded.user_id,
            },
        )
        self.session.execute(stmt)
        return {
            DayScope(row.user_id, row.source_id, day_start)
            for day_start in _day_range(start, end)
        }

    def _handle_heart_rate(self, row: WearableRaw, payload: Dict) -> Set[DayScope]:
        timestamp = _parse_datetime(payload.get("start"), field="start")
        fields = payload["fields"]
        try:
            bpm = int(fields["bpm"])
        except KeyError as exc:
            raise WearableNormalizationError("bpm is required for heart_rate") from exc
        except (TypeError, ValueError) as exc:
            raise WearableNormalizationError("bpm must be integer") from exc
        if bpm <= 0:
            raise WearableNormalizationError("bpm must be positive")
        variability = fields.get("variability_ms")
        if variability is not None:
            try:
                variability = float(variability)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("variability_ms must be numeric") from exc
        confidence = fields.get("confidence")
        values = {
            "user_id": row.user_id,
            "source_id": row.source_id,
            "raw_id": row.id,
            "timestamp_utc": timestamp,
            "bpm": bpm,
            "confidence": confidence,
            "variability_ms": variability,
            "dedupe_key": payload.get("dedupe_key") or row.dedupe_key,
        }
        stmt = insert(WearableCanonicalHR).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "timestamp_utc": stmt.excluded.timestamp_utc,
                "bpm": stmt.excluded.bpm,
                "confidence": stmt.excluded.confidence,
                "variability_ms": stmt.excluded.variability_ms,
                "raw_id": stmt.excluded.raw_id,
                "source_id": stmt.excluded.source_id,
                "user_id": stmt.excluded.user_id,
            },
        )
        self.session.execute(stmt)
        return {DayScope(row.user_id, row.source_id, _day_start(timestamp))}

    def _handle_sleep_session(self, row: WearableRaw, payload: Dict) -> Set[DayScope]:
        start = _parse_datetime(payload.get("start"), field="start")
        end = _parse_datetime(payload.get("end"), field="end")
        if end <= start:
            raise WearableNormalizationError("sleep session must end after it starts")
        fields = payload["fields"]
        sleep_type = fields.get("sleep_type")
        score = fields.get("score")
        if score is not None:
            try:
                score = int(score)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("sleep score must be integer") from exc
        duration_seconds = fields.get("duration_seconds")
        if duration_seconds is not None:
            try:
                duration_seconds = int(duration_seconds)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("duration_seconds must be integer") from exc
        else:
            duration_seconds = int((end - start).total_seconds())
        dedupe_key = payload.get("dedupe_key") or row.dedupe_key
        values = {
            "user_id": row.user_id,
            "source_id": row.source_id,
            "raw_id": row.id,
            "start_time_utc": start,
            "end_time_utc": end,
            "duration_seconds": duration_seconds,
            "sleep_type": sleep_type,
            "score": score,
            "dedupe_key": dedupe_key,
        }
        stmt = insert(WearableCanonicalSleepSession).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "start_time_utc": stmt.excluded.start_time_utc,
                "end_time_utc": stmt.excluded.end_time_utc,
                "duration_seconds": stmt.excluded.duration_seconds,
                "sleep_type": stmt.excluded.sleep_type,
                "score": stmt.excluded.score,
                "raw_id": stmt.excluded.raw_id,
                "source_id": stmt.excluded.source_id,
                "user_id": stmt.excluded.user_id,
            },
        ).returning(WearableCanonicalSleepSession.id)
        session_id = self.session.execute(stmt).scalar_one()

        stages = fields.get("stages") or []
        for idx, stage in enumerate(stages):
            stage_dedupe = stage.get("dedupe_key") or f"{dedupe_key}:stage:{idx}"
            self._insert_sleep_stage(
                user_id=row.user_id,
                source_id=row.source_id,
                session_id=session_id,
                session_dedupe_key=dedupe_key,
                stage_payload=stage,
                dedupe_key=stage_dedupe,
            )

        return {
            DayScope(row.user_id, row.source_id, day_start)
            for day_start in _day_range(start, end)
        }

    def _handle_sleep_stage(self, row: WearableRaw, payload: Dict) -> Set[DayScope]:
        fields = payload["fields"]
        session_key = fields.get("session_dedupe_key")
        if not session_key:
            raise WearableNormalizationError("session_dedupe_key required for sleep_stage")
        session_row = (
            self.session.query(WearableCanonicalSleepSession)
            .filter(WearableCanonicalSleepSession.dedupe_key == session_key)
            .one_or_none()
        )
        if not session_row:
            raise WearableNormalizationError(f"sleep session '{session_key}' not found")
        dedupe_key = payload.get("dedupe_key") or row.dedupe_key
        stage_scope = self._insert_sleep_stage(
            user_id=row.user_id,
            source_id=row.source_id,
            session_id=session_row.id,
            session_dedupe_key=session_key,
            stage_payload=fields,
            dedupe_key=dedupe_key,
        )
        start = _parse_datetime(payload.get("start"), field="start")
        end = _parse_datetime(payload.get("end") or payload.get("start"), field="end")
        return {
            DayScope(row.user_id, row.source_id, day_start)
            for day_start in _day_range(start, end)
        } | stage_scope

    def _insert_sleep_stage(
        self,
        *,
        user_id: int,
        source_id: Optional[int],
        session_id: int,
        session_dedupe_key: str,
        stage_payload: Dict,
        dedupe_key: str,
    ) -> Set[DayScope]:
        start = _parse_datetime(stage_payload.get("start"), field="stage.start")
        end = _parse_datetime(stage_payload.get("end"), field="stage.end")
        if end <= start:
            raise WearableNormalizationError("sleep stage must end after it starts")
        stage_type = stage_payload.get("stage") or stage_payload.get("stage_type")
        if not stage_type:
            raise WearableNormalizationError("stage_type is required for sleep stage")
        duration_seconds = stage_payload.get("duration_seconds")
        if duration_seconds is not None:
            try:
                duration_seconds = int(duration_seconds)
            except (TypeError, ValueError) as exc:
                raise WearableNormalizationError("duration_seconds must be integer") from exc
        else:
            duration_seconds = int((end - start).total_seconds())
        values = {
            "session_id": session_id,
            "user_id": user_id,
            "stage_type": stage_type,
            "start_time_utc": start,
            "end_time_utc": end,
            "duration_seconds": duration_seconds,
            "dedupe_key": dedupe_key,
        }
        stmt = insert(WearableCanonicalSleepStage).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "stage_type": stmt.excluded.stage_type,
                "start_time_utc": stmt.excluded.start_time_utc,
                "end_time_utc": stmt.excluded.end_time_utc,
                "duration_seconds": stmt.excluded.duration_seconds,
                "session_id": stmt.excluded.session_id,
                "user_id": stmt.excluded.user_id,
            },
        )
        self.session.execute(stmt)
        return {
            DayScope(user_id, source_id, day_start)
            for day_start in _day_range(start, end)
        }


class WearableAggregator:
    def __init__(self, session=None, *, log=None):
        self.session = session or db.session
        self.log = log or logger

    def upsert_day(self, user_id: int, source_id: Optional[int], day_start: datetime) -> None:
        day_start = _day_start(day_start)
        day_end = day_start + timedelta(days=1)

        filters = [
            WearableCanonicalSteps.user_id == user_id,
            WearableCanonicalSteps.start_time_utc < day_end,
            WearableCanonicalSteps.end_time_utc >= day_start,
        ]
        if source_id is not None:
            filters.append(WearableCanonicalSteps.source_id == source_id)

        step_row = self.session.execute(
            select(
                func.coalesce(func.sum(WearableCanonicalSteps.steps), 0),
                func.coalesce(func.sum(WearableCanonicalSteps.distance_meters), 0.0),
            ).where(*filters)
        ).one()
        steps_total = int(step_row[0] or 0)
        distance_total = float(step_row[1] or 0.0) if step_row[1] is not None else None

        hr_filters = [
            WearableCanonicalHR.user_id == user_id,
            WearableCanonicalHR.timestamp_utc >= day_start,
            WearableCanonicalHR.timestamp_utc < day_end,
        ]
        if source_id is not None:
            hr_filters.append(WearableCanonicalHR.source_id == source_id)
        hr_row = self.session.execute(
            select(
                func.min(WearableCanonicalHR.bpm),
                func.avg(WearableCanonicalHR.variability_ms),
            ).where(*hr_filters)
        ).one()
        resting_hr = hr_row[0]
        hrv_avg = float(hr_row[1]) if hr_row[1] is not None else None

        sleep_filters = [
            WearableCanonicalSleepSession.user_id == user_id,
            WearableCanonicalSleepSession.start_time_utc < day_end,
            WearableCanonicalSleepSession.end_time_utc >= day_start,
        ]
        if source_id is not None:
            sleep_filters.append(WearableCanonicalSleepSession.source_id == source_id)
        sleep_row = self.session.execute(
            select(func.coalesce(func.sum(WearableCanonicalSleepSession.duration_seconds), 0)).where(*sleep_filters)
        ).one()
        sleep_seconds = int(sleep_row[0] or 0)

        payload = {
            "day": day_start.isoformat(),
            "source_id": source_id,
            "steps_records": steps_total,
            "resting_hr_samples": resting_hr is not None,
        }

        dedupe_key = f"{user_id}:{source_id or 'all'}:{day_start.date().isoformat()}"

        if steps_total == 0 and not distance_total and resting_hr is None and hrv_avg is None and sleep_seconds == 0:
            self.session.query(WearableDailyAgg).filter(
                WearableDailyAgg.user_id == user_id,
                WearableDailyAgg.day_start_utc == day_start,
                (WearableDailyAgg.source_id == source_id)
                if source_id is not None
                else WearableDailyAgg.source_id.is_(None),
            ).delete(synchronize_session=False)
            return

        values = {
            "user_id": user_id,
            "source_id": source_id,
            "day_start_utc": day_start,
            "steps": steps_total if steps_total else None,
            "distance_meters": distance_total,
            "resting_heart_rate": resting_hr,
            "hrv_rmssd_ms": hrv_avg,
            "sleep_seconds": sleep_seconds if sleep_seconds else None,
            "payload": payload,
            "dedupe_key": dedupe_key,
        }
        stmt = insert(WearableDailyAgg).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["dedupe_key"],
            set_={
                "steps": stmt.excluded.steps,
                "distance_meters": stmt.excluded.distance_meters,
                "resting_heart_rate": stmt.excluded.resting_heart_rate,
                "hrv_rmssd_ms": stmt.excluded.hrv_rmssd_ms,
                "sleep_seconds": stmt.excluded.sleep_seconds,
                "payload": stmt.excluded.payload,
                "source_id": stmt.excluded.source_id,
                "day_start_utc": stmt.excluded.day_start_utc,
            },
        )
        self.session.execute(stmt)
        self.log.info(
            "wearable.aggregate.upsert",
            user_id=user_id,
            source_id=source_id,
            day=day_start.date().isoformat(),
        )

    def rebuild_range(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        source_id: Optional[int] = None,
    ) -> None:
        cursor = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        stop = datetime.combine(end_date, time.min).replace(tzinfo=timezone.utc)
        while cursor <= stop:
            self.upsert_day(user_id, source_id, cursor)
            cursor += timedelta(days=1)
