"""
ML Service microservice.

Exposes:
  POST /classify  — classify clinical features and return severity result
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ml_service.config import validate_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    """
    Request body for POST /classify.

    features: dict mapping feature names to FeatureValue-compatible dicts.
    session_id: optional session identifier for logging / tracing.
    """

    features: dict[str, Any]
    session_id: str = ""


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------

@app.post("/classify")
async def classify(body: ClassifyRequest) -> JSONResponse:
    """
    Classify clinical features and return a severity result.

    Accepts a features dict (FeatureValue-compatible dicts keyed by feature
    name) and returns the full classification result including:
      - severity_label
      - confidence_score (after calibration + missing-feature penalties)
      - base_confidence (pre-penalty calibrated score)
      - low_confidence_warning
      - completeness_pct
      - data_sufficiency_warning
      - feature_importance
      - audit_trail
      - tnm_stage_detail (None for benign cases)

    Requirements: 4.1–4.10, 5.2, 6.1–6.4
    """
    try:
        from ml_service.severity_engine import SeverityEngine

        engine = SeverityEngine()
        result = engine.classify(body.features)
    except Exception as exc:
        logger.exception("Classification failed for session %s", body.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {exc}",
        )

    return JSONResponse(
        status_code=200,
        content={
            "session_id": body.session_id,
            **result,
        },
    )
