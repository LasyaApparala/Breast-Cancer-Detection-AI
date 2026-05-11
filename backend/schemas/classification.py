"""Pydantic schemas for classification requests, results, and related models."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel

from backend.schemas.clinical_features import ClinicalFeatures


class SeverityLabel(str, Enum):
    BENIGN = "Benign"
    MALIGNANT_STAGE_I = "Malignant — Stage I"
    MALIGNANT_STAGE_II = "Malignant — Stage II"
    MALIGNANT_STAGE_III = "Malignant — Stage III"
    MALIGNANT_STAGE_IV = "Malignant — Stage IV"


class TNMDetail(BaseModel):
    t_value: str   # T1 / T2 / T3 / T4
    n_value: str   # N0 / N1 / N2 / N3
    m_value: str   # M0 / M1
    ajcc_stage: str  # I / II / III / IV
    staging_source: Literal["tnm_rule_engine"]


class FeatureImportanceEntry(BaseModel):
    feature_name: str
    importance_score: float
    direction: Literal["increases_risk", "decreases_risk"]


class AuditTrailEntry(BaseModel):
    feature_name: str
    value_used: Optional[float | str] = None
    source: Literal["document", "manual_entry", "imaging", "missing"]
    document_ref: Optional[str] = None
    original_extracted: Optional[float | str] = None
    corrected_by_user: bool = False
    imaging_confidence: Optional[float] = None


class AuditTrail(BaseModel):
    session_id: str
    entries: list[AuditTrailEntry]
    completeness_pct: float
    created_at: datetime


class ClassificationRequest(BaseModel):
    session_id: str
    user_id: str
    document_ids: list[str]
    features: ClinicalFeatures
    requires_async: bool
    created_at: datetime


class ClassificationResult(BaseModel):
    session_id: str
    severity_label: SeverityLabel
    confidence_score: float
    base_confidence: float
    low_confidence_warning: bool
    completeness_pct: float
    data_sufficiency_warning: bool
    feature_importance: list[FeatureImportanceEntry]
    audit_trail: list[AuditTrailEntry]
    model_version: str
    classified_at: datetime
    tnm_stage_detail: Optional[TNMDetail] = None


class OverrideRequest(BaseModel):
    override_label: SeverityLabel
    notes: Optional[str] = None


class OverrideLog(BaseModel):
    override_id: str
    session_id: str
    user_id: str
    original_label: SeverityLabel
    override_label: SeverityLabel
    timestamp: datetime
    notes: Optional[str] = None


class ModelVersion(BaseModel):
    model_id: str
    version_tag: str
    training_datasets: list[str]
    auc: Optional[float] = None
    sensitivity: Optional[float] = None
    specificity: Optional[float] = None
    accuracy: Optional[float] = None
    ece: Optional[float] = None
    temperature: Optional[float] = None
    deployed_at: Optional[datetime] = None
    is_active: bool = False
    regression_passed: bool = False
