"""
Celery tasks for the ML service.

Tasks:
  - run_classification: classify a session's features and persist the result
  - check_retraining_trigger_task: daily beat task to check override rate

Requirements: 11.1, 11.4, 12.3
"""

import os
import uuid
from datetime import datetime, timezone

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from ml_service.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="ml_service.tasks.run_classification",
    queue="classification_tasks",
    max_retries=3,
    time_limit=60,
    soft_time_limit=55,
)
def run_classification(self: Task, session_id: str, payload: dict) -> dict:
    """
    Classify a session's clinical features and persist the result to the DB.

    Retry policy: max 3 retries with exponential backoff (30s, 60s, 120s).
    On SoftTimeLimitExceeded: mark session as 'delayed' and retry after 30s.

    Requirements: 11.1, 11.4
    """
    try:
        from ml_service.severity_engine import SeverityEngine

        features = payload.get("features", {})
        if not features and "document_ids" in payload:
            # Features not yet extracted — call document parser
            features = _extract_features_from_documents(
                payload.get("document_ids", []), session_id
            )

        engine = SeverityEngine()
        result = engine.classify(features)

        # Persist result to DB
        _persist_result(session_id, result)

        return {"session_id": session_id, **result}

    except SoftTimeLimitExceeded:
        _update_session_status(session_id, "delayed")
        raise self.retry(countdown=30)

    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    name="ml_service.tasks.check_retraining_trigger_task",
    queue="classification_tasks",
)
def check_retraining_trigger_task() -> dict:
    """
    Daily Celery beat task: check override rate and notify admin if > 10%.

    Requirements: 12.3
    """
    try:
        from backend.db import SessionLocal
        from backend.services.override_monitor import check_retraining_trigger

        db = SessionLocal()
        try:
            triggered = check_retraining_trigger(db)
            return {"triggered": triggered}
        finally:
            db.close()
    except Exception as exc:
        return {"triggered": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_features_from_documents(document_ids: list, session_id: str) -> dict:
    """Call document parser service to extract features."""
    import httpx

    parser_url = os.environ.get("DOCUMENT_PARSER_URL", "http://document_parser:8002")
    try:
        resp = httpx.post(
            f"{parser_url}/parse",
            json={"document_ids": document_ids, "session_id": session_id},
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json().get("features", {})
    except Exception:
        pass
    return {}


def _persist_result(session_id: str, result: dict) -> None:
    """Persist classification result to PostgreSQL."""
    try:
        from backend.db import SessionLocal
        from backend.models.db_models import (
            ClassificationResult,
            Session as SessionModel,
        )

        db = SessionLocal()
        try:
            session = db.get(SessionModel, uuid.UUID(session_id))
            if session:
                session.status = "complete"
                session.completed_at = datetime.now(tz=timezone.utc)

            cr = ClassificationResult(
                result_id=uuid.uuid4(),
                session_id=uuid.UUID(session_id),
                severity_label=result["severity_label"],
                confidence_score=result["confidence_score"],
                base_confidence=result["base_confidence"],
                completeness_pct=result["completeness_pct"],
                model_version="v1.0",
                features_json=result.get("audit_trail", []),
                classified_at=datetime.now(tz=timezone.utc),
            )
            db.add(cr)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # DB persistence failure should not fail the task


def _update_session_status(session_id: str, status: str) -> None:
    """Update session status in DB."""
    try:
        from backend.db import SessionLocal
        from backend.models.db_models import Session as SessionModel

        db = SessionLocal()
        try:
            session = db.get(SessionModel, uuid.UUID(session_id))
            if session:
                session.status = status
                db.commit()
        finally:
            db.close()
    except Exception:
        pass
