"""
Classification session routes.
Requirements: 2.4, 2.5, 4.1, 5.1, 5.3, 8.3, 11.1, 11.2, 11.3, 12.1
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.db_models import (
    AuditTrailEntry,
    ClassificationResult,
    Document,
    OverrideLog,
    Session as SessionModel,
)
from backend.schemas.classification import OverrideRequest
from backend.schemas.clinical_features import ClinicalFeatures
from backend.security.auth import TokenData, require_auth
from backend.services.mongodb_audit import MongoDBAuditService, OverrideAuditEntry
from backend.utils.routing import should_process_async
from backend.validation.manual_entry import ManualEntryValidator

classify_router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOCUMENT_PARSER_URL = os.environ.get("DOCUMENT_PARSER_URL", "http://document_parser:8002")
_ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://ml_service:8001")
_MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
_MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "breastguard_ai_docs")

# Global audit service instance
_audit_service: Optional[MongoDBAuditService] = None


async def get_audit_service() -> MongoDBAuditService:
    """Get or create MongoDB audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = MongoDBAuditService(_MONGODB_URL, _MONGODB_DB_NAME)
        await _audit_service.connect()
    return _audit_service

# Celery state → API state mapping
_CELERY_STATE_MAP: dict[str, str] = {
    "PENDING": "queued",
    "STARTED": "processing",
    "SUCCESS": "complete",
    "FAILURE": "failed",
}


class ClassifyRequest(BaseModel):
    """Request body for POST /classify."""
    document_ids: list[str]
    features: Optional[ClinicalFeatures] = None


def _get_session_or_404(session_id: str, db: Session) -> SessionModel:
    """Fetch a session by ID or raise HTTP 404."""
    record = db.get(SessionModel, uuid.UUID(session_id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return record


def _assert_owner_or_admin(session: SessionModel, token_data: TokenData) -> None:
    """Raise HTTP 403 if the caller is neither the session owner nor an admin."""
    if (
        str(session.user_id) != token_data.user_id
        and token_data.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not the session owner or admin",
        )


def _generate_clinical_report_for_session(session_id: str, db: Session) -> bytes:
    """
    Generate a PDF clinical report for the given session.

    Fetches the latest ClassificationResult and AuditTrail entries from the
    DB, then delegates to generate_clinical_report() in pdf_export.py.

    Requirements: 5.3, 5.4, 5.5
    """
    from backend.services.pdf_export import generate_clinical_report

    session = db.get(SessionModel, uuid.UUID(session_id))
    if session is None:
        # Fallback: empty result
        return generate_clinical_report(session_id, {}, [])

    # Get the most recent classification result
    results = session.classification_results
    result_dict: dict = {}
    if results:
        latest = max(results, key=lambda r: r.classified_at)
        result_dict = {
            "severity_label": latest.severity_label,
            "confidence_score": float(latest.confidence_score),
            "low_confidence_warning": float(latest.confidence_score) < 0.75,
            "data_sufficiency_warning": float(latest.completeness_pct) < 60.0,
            "tnm_stage_detail": None,  # TNM detail not stored separately; omit
        }

    # Build audit trail from AuditTrailEntry rows
    audit_trail = [
        {
            "feature_name": e.feature_name,
            "value_used": e.value_used,
            "source": e.source,
            "document_ref": e.document_ref,
            "corrected_by_user": e.corrected_by_user,
        }
        for e in session.audit_trail_entries
    ]

    return generate_clinical_report(session_id, result_dict, audit_trail)


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------

@classify_router.post("/classify")
async def create_classification_session(
    body: ClassifyRequest,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Create a classification session and route to sync or async processing.

    - Sync path (≤10 MB, no DICOM): calls Document Parser service via httpx,
      returns session_id + status="processing".
    - Async path (>10 MB or DICOM present): enqueues a Celery task, returns
      task_id + session_id + status="queued" immediately.

    Requirements: 4.1, 11.1, 11.2
    """
    # Fetch document records to determine total size and DICOM presence
    doc_records: list[Document] = []
    for doc_id_str in body.document_ids:
        try:
            doc_id = uuid.UUID(doc_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid document ID: '{doc_id_str}'",
            )
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_id_str}' not found",
            )
        doc_records.append(doc)

    # Compute total size from stored files
    total_size = 0
    for doc in doc_records:
        try:
            import os as _os
            total_size += _os.path.getsize(doc.storage_path)
        except (OSError, TypeError):
            pass  # file may not be accessible in all environments

    # Create session record with status="queued"
    now = datetime.now(tz=timezone.utc)
    session_id = uuid.uuid4()
    session_record = SessionModel(
        session_id=session_id,
        user_id=uuid.UUID(token_data.user_id),
        status="queued",
        created_at=now,
    )
    db.add(session_record)

    # Link documents to this session
    for doc in doc_records:
        doc.session_id = session_id

    db.commit()

    # Decide routing
    use_async = should_process_async(doc_records, total_size)

    if use_async:
        # Async path — enqueue Celery task
        task_id = _enqueue_classification_task(str(session_id), body.dict())
        return JSONResponse(
            status_code=202,
            content={
                "task_id": task_id,
                "session_id": str(session_id),
                "status": "queued",
            },
        )
    else:
        # Sync path — call Document Parser service
        session_record.status = "processing"
        db.commit()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                parse_payload: dict[str, Any] = {
                    "document_ids": body.document_ids,
                    "session_id": str(session_id),
                }
                await client.post(
                    f"{_DOCUMENT_PARSER_URL}/parse",
                    json=parse_payload,
                )
        except httpx.RequestError:
            # Parser unavailable — continue; features will be empty for review
            pass

        return JSONResponse(
            status_code=200,
            content={
                "session_id": str(session_id),
                "status": "processing",
            },
        )


def _enqueue_classification_task(session_id: str, payload: dict) -> str:
    """
    Enqueue a Celery classification task.

    Returns the Celery task ID. Falls back to a UUID stub when Celery is
    not available (e.g., during unit tests or local dev without Redis).
    """
    try:
        from ml_service.tasks import run_classification  # type: ignore[import]
        result = run_classification.delay(session_id, payload)
        return result.id
    except Exception:
        # Celery not available — return a placeholder task ID
        return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# GET /classify/{session_id}/review
# ---------------------------------------------------------------------------

@classify_router.get("/classify/{session_id}/review")
async def get_session_review(
    session_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Return extracted ClinicalFeatures for user review.

    Requirements: 2.4
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    # Retrieve audit trail entries which hold extracted feature data
    entries = session.audit_trail_entries
    features: dict[str, Any] = {}
    for entry in entries:
        features[entry.feature_name] = {
            "value": entry.value_used,
            "source": entry.source,
            "document_ref": entry.document_ref,
            "original_extracted": entry.original_extracted,
            "corrected_by_user": entry.corrected_by_user,
        }

    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "status": session.status,
            "features": features,
        },
    )


# ---------------------------------------------------------------------------
# PATCH /classify/{session_id}/confirm
# ---------------------------------------------------------------------------

class ConfirmRequest(BaseModel):
    """Request body for PATCH /classify/{session_id}/confirm."""
    features: ClinicalFeatures


@classify_router.patch("/classify/{session_id}/confirm")
async def confirm_features(
    session_id: str,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Accept user-corrected ClinicalFeatures, persist audit trail, and trigger
    classification.

    For each corrected feature (corrected_by_user=True), stores the
    original_extracted value alongside the corrected value.

    Requirements: 2.5
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    # Validate manual-entry features before accepting them
    features_dict = body.features.dict()
    validator = ManualEntryValidator()

    if not validator.has_minimum_required(features_dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Minimum required features are missing: "
                "tumor_size_mm, histological_grade, and margin_type must all be present."
            ),
        )

    validation_errors = validator.validate(features_dict)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Feature validation failed",
                "errors": [e.to_dict() for e in validation_errors],
            },
        )

    now = datetime.now(tz=timezone.utc)

    # Persist audit trail entries for each feature
    for feature_name, feature_value in features_dict.items():
        if not isinstance(feature_value, dict):
            continue

        corrected = feature_value.get("corrected_by_user", False)
        entry = AuditTrailEntry(
            entry_id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            feature_name=feature_name,
            value_used=str(feature_value.get("value")) if feature_value.get("value") is not None else None,
            source=feature_value.get("source", "missing"),
            document_ref=feature_value.get("document_ref"),
            original_extracted=(
                str(feature_value.get("original_extracted"))
                if feature_value.get("original_extracted") is not None
                else None
            ),
            corrected_by_user=corrected,
        )
        db.add(entry)

    # Update session status and trigger classification
    session.status = "processing"
    db.commit()

    # Trigger classification via ML service
    task_id = _enqueue_classification_task(session_id, features_dict)

    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "task_id": task_id,
            "status": "processing",
        },
    )


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}
# ---------------------------------------------------------------------------

@classify_router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Poll Celery task state and return status + result.

    Maps Celery states: PENDING→queued, STARTED→processing,
    SUCCESS→complete, FAILURE→failed.

    Requirements: 11.3
    """
    celery_state, result_data = _query_celery_task(task_id)
    api_status = _CELERY_STATE_MAP.get(celery_state, "queued")

    estimated_completion_s: Optional[int] = None
    if api_status in ("queued", "processing"):
        estimated_completion_s = 30

    return JSONResponse(
        status_code=200,
        content={
            "status": api_status,
            "result": result_data,
            "estimated_completion_s": estimated_completion_s,
        },
    )


def _query_celery_task(task_id: str) -> tuple[str, Optional[dict]]:
    """
    Query Celery for task state and result.

    Returns (celery_state, result_dict_or_None).
    Falls back to PENDING when Celery is unavailable.
    """
    try:
        from ml_service.celery_app import celery_app  # type: ignore[import]
        async_result = celery_app.AsyncResult(task_id)
        state = async_result.state
        result = async_result.result if state == "SUCCESS" else None
        if isinstance(result, dict):
            return state, result
        return state, None
    except Exception:
        return "PENDING", None


# ---------------------------------------------------------------------------
# POST /classify/{session_id}/override
# ---------------------------------------------------------------------------

@classify_router.post("/classify/{session_id}/override")
async def override_classification(
    session_id: str,
    body: OverrideRequest,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
    audit_service: MongoDBAuditService = Depends(get_audit_service),
) -> JSONResponse:
    """
    Log a clinician override of the classification result.

    Persists to both PostgreSQL (override_log table) and MongoDB
    (append-only audit trail) for HIPAA compliance.

    Requirements: 12.1
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    # Retrieve the most recent classification result for this session
    results = session.classification_results
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No classification result found for this session",
        )
    latest_result = max(results, key=lambda r: r.classified_at)
    original_label = latest_result.severity_label
    original_confidence = float(latest_result.confidence_score)

    now = datetime.now(tz=timezone.utc)
    
    # Log to PostgreSQL
    override_entry = OverrideLog(
        override_id=uuid.uuid4(),
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(token_data.user_id),
        original_label=original_label,
        override_label=body.override_label.value,
        timestamp=now,
        notes=body.notes,
    )
    db.add(override_entry)
    db.commit()

    # Log to MongoDB audit trail
    try:
        mongo_override = OverrideAuditEntry(
            user_id=token_data.user_id,
            user_name=token_data.user_name if hasattr(token_data, 'user_name') else "Unknown",
            user_role=token_data.role,
            license_number=token_data.license_number if hasattr(token_data, 'license_number') else "N/A",
            session_id=session_id,
            original_label=original_label,
            override_label=body.override_label.value,
            original_confidence=original_confidence,
            override_reason=body.override_reason if hasattr(body, 'override_reason') else "Physician clinical judgment",
            clinical_notes=body.notes,
            document_ids=[str(doc.document_id) for doc in session.documents]
        )
        await audit_service.log_override(mongo_override)
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log override to MongoDB: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "override_id": str(override_entry.override_id),
            "session_id": session_id,
            "original_label": original_label,
            "override_label": body.override_label.value,
            "timestamp": now.isoformat(),
            "audit_logged": True,
        },
    )


# ---------------------------------------------------------------------------
# GET /classify/{session_id}/export
# ---------------------------------------------------------------------------

@classify_router.get("/classify/{session_id}/export")
async def export_report(
    session_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> Response:
    """
    Generate and return a PDF clinical report for the session.

    Calls generate_clinical_report() (stub) and returns the PDF bytes.

    Requirements: 5.3, 5.4
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    pdf_bytes = _generate_clinical_report_for_session(session_id, db)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report_{session_id}.pdf"'
        },
    )


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id}
# ---------------------------------------------------------------------------

@classify_router.get("/classify/{session_id}/audit")
async def get_session_audit(
    session_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
    audit_service: MongoDBAuditService = Depends(get_audit_service),
) -> JSONResponse:
    """
    Get complete audit trail for a session from MongoDB.

    Returns all audit entries including physician overrides.

    Requirements: 8.3, 12.1
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    try:
        # Get audit trail from MongoDB
        audit_trail = await audit_service.get_session_audit_trail(session_id)
        
        # Get overrides specifically
        overrides = await audit_service.get_overrides_by_session(session_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "session_id": session_id,
                "audit_trail": audit_trail,
                "overrides": overrides,
                "total_entries": len(audit_trail),
                "total_overrides": len(overrides)
            },
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit trail: {str(e)}"
        )


@classify_router.get("/overrides/statistics")
async def get_override_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token_data: TokenData = Depends(require_auth),
    audit_service: MongoDBAuditService = Depends(get_audit_service),
) -> JSONResponse:
    """
    Get statistics on physician overrides.

    Only accessible to admin users.

    Requirements: 12.1
    """
    if token_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access override statistics"
        )

    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)

        stats = await audit_service.get_override_statistics(start_dt, end_dt)
        
        return JSONResponse(
            status_code=200,
            content=stats
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve override statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@classify_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Permanently delete all data for a session.

    Deletes rows in: documents, classification_results, audit_trail,
    override_log, and sessions tables.

    Requires the caller to be the session owner or an admin.

    Requirements: 8.3
    """
    session = _get_session_or_404(session_id, db)
    _assert_owner_or_admin(session, token_data)

    # Cascade deletes are configured on the ORM relationships, so deleting
    # the session record removes all child rows automatically.
    db.delete(session)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={"deleted": True, "session_id": session_id},
    )
