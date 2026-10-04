"""
Override monitoring service.

Computes the rolling 30-day clinician override rate and triggers a retraining
notification to the admin when the rate exceeds 10%.

Requirements: 12.2, 12.3
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.db_models import ClassificationResult, OverrideLog

logger = logging.getLogger(__name__)


def compute_override_rate(db: Session, window_days: int = 30) -> float:
    """
    Compute rolling override rate as override_count / total_count.

    Counts classification results and override log entries within the
    specified rolling window (default: 30 days).

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 when there are no classifications.

    Requirements: 12.2
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=window_days)

    total = db.execute(
        select(func.count(ClassificationResult.result_id)).where(
            ClassificationResult.classified_at >= since
        )
    ).scalar_one()

    overrides = db.execute(
        select(func.count(OverrideLog.override_id)).where(
            OverrideLog.timestamp >= since
        )
    ).scalar_one()

    return overrides / total if total > 0 else 0.0


def check_retraining_trigger(db: Session) -> bool:
    """
    Check if override rate exceeds 10% and notify admin if so.

    Computes the rolling 30-day override rate. If the rate exceeds 0.10
    (10%), sends a retraining notification to the admin exactly once per
    invocation.

    Returns:
        True if the retraining trigger was fired, False otherwise.

    Requirements: 12.3
    """
    rate = compute_override_rate(db)
    if rate > 0.10:
        _notify_admin_retraining(rate)
        return True
    return False


def _notify_admin_retraining(rate: float) -> None:
    """
    Send retraining notification to admin (log + optional webhook).

    Logs a WARNING-level message. In production, this can be extended to
    send an email, Slack message, or webhook to the admin.

    Requirements: 12.3
    """
    logger.warning(
        "RETRAINING TRIGGER: Rolling 30-day override rate is %.1f%% (threshold: 10%%)",
        rate * 100,
    )
