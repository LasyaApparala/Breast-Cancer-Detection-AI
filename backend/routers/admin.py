"""
Admin routes for model registry and override monitoring.
Requirements: 7.5, 12.2, 12.4
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.db_models import (
    ClassificationResult,
    ModelVersion,
    OverrideLog,
)
from backend.security.auth import TokenData, require_admin

admin_router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class RegisterModelRequest(BaseModel):
    """Request body for POST /admin/models."""
    version_tag: str
    training_datasets: list[str]
    auc: Optional[float] = None
    sensitivity: Optional[float] = None
    specificity: Optional[float] = None
    accuracy: Optional[float] = None
    ece: Optional[float] = None
    temperature: Optional[float] = None
    regression_passed: bool = False


def _model_to_dict(model: ModelVersion) -> dict[str, Any]:
    """Serialize a ModelVersion ORM record to a JSON-safe dict."""
    return {
        "model_id": str(model.model_id),
        "version_tag": model.version_tag,
        "training_datasets": model.training_datasets,
        "auc": float(model.auc) if model.auc is not None else None,
        "sensitivity": float(model.sensitivity) if model.sensitivity is not None else None,
        "specificity": float(model.specificity) if model.specificity is not None else None,
        "accuracy": float(model.accuracy) if model.accuracy is not None else None,
        "ece": float(model.ece) if model.ece is not None else None,
        "temperature": float(model.temperature) if model.temperature is not None else None,
        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        "is_active": model.is_active,
        "regression_passed": model.regression_passed,
    }


# ---------------------------------------------------------------------------
# GET /admin/registry  (alias for GET /admin/models)
# ---------------------------------------------------------------------------

@admin_router.get("/admin/registry")
async def get_model_registry(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    Return all model_versions records.

    Requirements: 7.5
    """
    models = db.execute(select(ModelVersion)).scalars().all()
    return JSONResponse(
        status_code=200,
        content={"models": [_model_to_dict(m) for m in models]},
    )


# ---------------------------------------------------------------------------
# POST /admin/models
# ---------------------------------------------------------------------------

@admin_router.post("/admin/models")
async def register_model(
    body: RegisterModelRequest,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    Register a new model version in the registry.

    Requirements: 7.5
    """
    # Check for duplicate version_tag
    existing = db.execute(
        select(ModelVersion).where(ModelVersion.version_tag == body.version_tag)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model version '{body.version_tag}' already exists",
        )

    model = ModelVersion(
        model_id=uuid.uuid4(),
        version_tag=body.version_tag,
        training_datasets=body.training_datasets,
        auc=body.auc,
        sensitivity=body.sensitivity,
        specificity=body.specificity,
        accuracy=body.accuracy,
        ece=body.ece,
        temperature=body.temperature,
        regression_passed=body.regression_passed,
        is_active=False,
    )
    db.add(model)
    db.commit()

    return JSONResponse(
        status_code=201,
        content=_model_to_dict(model),
    )


# ---------------------------------------------------------------------------
# GET /admin/models
# ---------------------------------------------------------------------------

@admin_router.get("/admin/models")
async def list_models(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    List all model versions with their metrics.

    Requirements: 7.5
    """
    models = db.execute(select(ModelVersion)).scalars().all()
    return JSONResponse(
        status_code=200,
        content={"models": [_model_to_dict(m) for m in models]},
    )


# ---------------------------------------------------------------------------
# PATCH /admin/models/{model_id}/activate
# ---------------------------------------------------------------------------

@admin_router.patch("/admin/models/{model_id}/activate")
async def activate_model(
    model_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    Set is_active=True for the specified model and is_active=False for all others.

    Requirements: 7.5
    """
    try:
        model_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid model ID: '{model_id}'",
        )

    target = db.get(ModelVersion, model_uuid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    # Deactivate all models, then activate the target
    all_models = db.execute(select(ModelVersion)).scalars().all()
    for m in all_models:
        m.is_active = False

    target.is_active = True
    target.deployed_at = datetime.now(tz=timezone.utc)
    db.commit()

    return JSONResponse(
        status_code=200,
        content=_model_to_dict(target),
    )


# ---------------------------------------------------------------------------
# PATCH /admin/models/{model_id}/deactivate
# ---------------------------------------------------------------------------

@admin_router.patch("/admin/models/{model_id}/deactivate")
async def deactivate_model(
    model_id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    Set is_active=False for the specified model.

    Requirements: 7.5
    """
    try:
        model_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid model ID: '{model_id}'",
        )

    target = db.get(ModelVersion, model_uuid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    target.is_active = False
    db.commit()

    return JSONResponse(
        status_code=200,
        content=_model_to_dict(target),
    )


# ---------------------------------------------------------------------------
# GET /admin/overrides
# ---------------------------------------------------------------------------

@admin_router.get("/admin/overrides")
async def get_overrides(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_admin),
) -> JSONResponse:
    """
    Return override log entries and the rolling 30-day override rate.

    Requirements: 12.2, 12.4
    """
    # Fetch all override log entries
    overrides = db.execute(select(OverrideLog)).scalars().all()
    override_list = [
        {
            "override_id": str(o.override_id),
            "session_id": str(o.session_id) if o.session_id else None,
            "user_id": str(o.user_id),
            "original_label": o.original_label,
            "override_label": o.override_label,
            "timestamp": o.timestamp.isoformat(),
            "notes": o.notes,
        }
        for o in overrides
    ]

    # Compute rolling 30-day override rate (Requirement 12.2)
    since = datetime.now(tz=timezone.utc) - timedelta(days=30)

    total_classifications = db.execute(
        select(func.count(ClassificationResult.result_id)).where(
            ClassificationResult.classified_at >= since
        )
    ).scalar_one()

    total_overrides = db.execute(
        select(func.count(OverrideLog.override_id)).where(
            OverrideLog.timestamp >= since
        )
    ).scalar_one()

    override_rate = (
        total_overrides / total_classifications
        if total_classifications > 0
        else 0.0
    )

    return JSONResponse(
        status_code=200,
        content={
            "overrides": override_list,
            "rolling_30d_override_rate": override_rate,
            "total_classifications_30d": total_classifications,
            "total_overrides_30d": total_overrides,
        },
    )
