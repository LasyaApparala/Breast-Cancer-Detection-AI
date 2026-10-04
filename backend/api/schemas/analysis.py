from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SeverityLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"

class CancerStage(str, Enum):
    BENIGN = "Benign"
    STAGE_I = "Stage I"
    STAGE_II = "Stage II"
    STAGE_III = "Stage III"
    STAGE_IV = "Stage IV"

class FeatureContribution(BaseModel):
    feature: str = Field(..., description="Name of the clinical feature")
    contribution: float = Field(..., description="Contribution percentage to prediction")
    importance: str = Field(..., description="Importance level: high, medium, or low")

class AuditTrail(BaseModel):
    timestamp: datetime = Field(..., description="When analysis was performed")
    model_version: str = Field(..., description="Version of AI models used")
    input_hash: str = Field(..., description="Hash of input data for audit")
    clinician_review_required: bool = Field(..., description="Whether clinician review is required")

class PredictionResult(BaseModel):
    id: str = Field(..., description="Unique result identifier")
    severity: SeverityLevel = Field(..., description="Predicted severity level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    uncertainty: float = Field(..., ge=0.0, le=1.0, description="Prediction uncertainty")
    stage: Optional[CancerStage] = Field(None, description="Predicted cancer stage")
    feature_contributions: List[FeatureContribution] = Field(..., description="Feature importance analysis")
    image_heatmap: Optional[str] = Field(None, description="URL to Grad-CAM heatmap")
    audit_trail: AuditTrail = Field(..., description="Audit and traceability information")

class ClinicalData(BaseModel):
    tumor_size: float = Field(..., gt=0, le=20, description="Tumor size in cm")
    tumor_grade: int = Field(..., ge=1, le=3, description="Tumor grade (1-3)")
    er_status: str = Field(..., description="Estrogen receptor status")
    pr_status: str = Field(..., description="Progesterone receptor status")
    her2_status: str = Field(..., description="HER2 receptor status")
    ki67_index: Optional[float] = Field(None, ge=0, le=100, description="Ki-67 proliferation index")
    lymph_node_involvement: bool = Field(..., description="Lymph node involvement")
    distant_metastasis: bool = Field(..., description="Distant metastasis present")
    bi_rads_score: Optional[int] = Field(None, ge=1, le=6, description="BI-RADS assessment score")

class UploadedFile(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    name: str = Field(..., description="Original filename")
    type: str = Field(..., description="File type (mammogram, ultrasound, etc.)")
    size: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    url: str = Field(..., description="File storage URL")

class AnalysisCreate(BaseModel):
    clinical_data: ClinicalData = Field(..., description="Clinical assessment data")
    files: List[UploadedFile] = Field(default_factory=list, description="Uploaded medical files")

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"

class AnalysisResponse(BaseModel):
    id: str = Field(..., description="Analysis identifier")
    user_id: str = Field(..., description="User who requested analysis")
    clinical_data: ClinicalData = Field(..., description="Clinical data provided")
    files: List[UploadedFile] = Field(default_factory=list, description="Uploaded files")
    result: Optional[PredictionResult] = Field(None, description="AI analysis results")
    status: AnalysisStatus = Field(..., description="Current analysis status")
    created_at: datetime = Field(..., description="Analysis creation time")
    completed_at: Optional[datetime] = Field(None, description="Analysis completion time")
    reviewed_by: Optional[str] = Field(None, description="Clinician who reviewed")
    reviewed_at: Optional[datetime] = Field(None, description="Review completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @classmethod
    def from_orm(cls, obj) -> "AnalysisResponse":
        """Convert ORM object to Pydantic model"""
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            clinical_data=obj.clinical_data,
            files=obj.files or [],
            result=obj.result,
            status=obj.status,
            created_at=obj.created_at,
            completed_at=obj.completed_at,
            reviewed_by=obj.reviewed_by,
            reviewed_at=obj.reviewed_at,
            error_message=getattr(obj, 'error_message', None)
        )

class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse] = Field(..., description="List of analyses")
    total: int = Field(..., description="Total number of analyses")
    skip: int = Field(..., description="Number of analyses skipped")
    limit: int = Field(..., description="Maximum number of analyses returned")

class ClinicianReviewRequest(BaseModel):
    analysis_id: str = Field(..., description="Analysis to review")
    notes: Optional[str] = Field(None, description="Review notes")
    approved: bool = Field(..., description="Whether analysis is approved")

class ClinicianReviewResponse(BaseModel):
    success: bool = Field(..., description="Review submission status")
    message: str = Field(..., description="Response message")
    analysis_id: str = Field(..., description="Reviewed analysis ID")
