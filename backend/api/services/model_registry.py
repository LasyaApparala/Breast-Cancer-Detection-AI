"""
Model registry service: regression gate and model deployment logic.

The regression gate checks that a candidate model meets minimum performance
thresholds before activating it. If the candidate passes, the current active
model is deactivated and the candidate is activated.

Thresholds (Requirements 7.1–7.3):
  - sensitivity >= 0.95
  - specificity >= 0.90
  - accuracy    >= 0.93

Requirements: 7.5, 7.6
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.db_models import ModelVersion

THRESHOLDS = {
    "sensitivity": 0.95,
    "specificity": 0.90,
    "accuracy": 0.93,
}


def deploy_model(candidate_id: str, db: Session) -> bool:
    """
    Run regression gate and activate model if it passes.

    Checks that the candidate model's sensitivity, specificity, and accuracy
    all meet the minimum thresholds defined in THRESHOLDS. If any metric falls
    below its threshold, the candidate is marked regression_passed=False and
    deployment is blocked.

    On success:
      - All existing models are deactivated (is_active=False).
      - The candidate is activated (is_active=True, regression_passed=True).
      - deployed_at is set to the current UTC timestamp.

    Returns:
        True if the model was deployed, False if blocked by the regression gate.

    Requirements: 7.5, 7.6
    """
    candidate = db.get(ModelVersion, UUID(candidate_id))
    if candidate is None:
        return False

    # Check thresholds
    metrics = {
        "sensitivity": float(candidate.sensitivity or 0),
        "specificity": float(candidate.specificity or 0),
        "accuracy": float(candidate.accuracy or 0),
    }

    for metric, threshold in THRESHOLDS.items():
        if metrics[metric] < threshold:
            candidate.regression_passed = False
            db.commit()
            return False

    # All thresholds passed: deactivate current active model, activate candidate
    all_models = db.execute(select(ModelVersion)).scalars().all()
    for m in all_models:
        m.is_active = False

    candidate.is_active = True
    candidate.regression_passed = True
    candidate.deployed_at = datetime.now(tz=timezone.utc)
    db.commit()
    return True
