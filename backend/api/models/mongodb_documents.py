from typing import Dict, List, Any, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class AuditLog(Document):
    """MongoDB document for comprehensive audit logging"""
    
    # Collection settings
    collection_name = "audit_logs"
    
    # Fields
    event_type: str = Field(..., description="Type of audit event")
    analysis_id: Optional[str] = Field(None, description="Associated analysis ID")
    user_id: Optional[str] = Field(None, description="User who performed action")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    # Event-specific fields
    input_hash: Optional[str] = Field(None, description="Hash of input data")
    result_hash: Optional[str] = Field(None, description="Hash of analysis result")
    severity: Optional[str] = Field(None, description="Analysis severity level")
    confidence: Optional[float] = Field(None, description="Analysis confidence score")
    clinician_review_required: Optional[bool] = Field(None, description="If clinician review needed")
    model_version: Optional[str] = Field(None, description="AI model version used")
    
    # Authentication events
    auth_event: Optional[str] = Field(None, description="Authentication event type")
    success: Optional[bool] = Field(None, description="Whether auth was successful")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    # Data access events
    resource_type: Optional[str] = Field(None, description="Type of resource accessed")
    resource_id: Optional[str] = Field(None, description="ID of resource accessed")
    action: Optional[str] = Field(None, description="Action performed")
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if event failed")
    
    # Review events
    clinician_id: Optional[str] = Field(None, description="Clinician who reviewed")
    approved: Optional[bool] = Field(None, description="Whether analysis was approved")
    review_notes: Optional[str] = Field(None, description="Review notes")
    
    # Indexes for performance
    class Settings:
        name = "audit_logs"
        indexes = [
            "analysis_id",
            "user_id", 
            "event_type",
            "timestamp"
        ]

class DocumentProcessingLog(Document):
    """MongoDB document for document processing tracking"""
    
    collection_name = "document_processing_logs"
    
    # Document metadata
    document_id: str = Field(..., description="Unique document identifier")
    analysis_id: str = Field(..., description="Associated analysis ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Document type (pdf, dicom, etc.)")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    
    # Processing details
    processing_started: datetime = Field(default_factory=datetime.utcnow)
    processing_completed: Optional[datetime] = Field(None)
    processing_status: str = Field(..., description="Processing status")
    processing_duration_ms: Optional[int] = Field(None)
    
    # Extraction results
    extracted_entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted medical entities")
    extraction_confidence: float = Field(..., description="Confidence in extraction accuracy")
    extraction_method: str = Field(..., description="Method used for extraction")
    
    # OCR results
    ocr_text: Optional[str] = Field(None, description="OCR extracted text")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence score")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Processing error if any")
    retry_count: int = Field(default=0, description="Number of processing retries")
    
    class Settings:
        name = "document_processing_logs"
        indexes = [
            "analysis_id",
            "document_id",
            "processing_status",
            "processing_started"
        ]

class ModelPerformanceLog(Document):
    """MongoDB document for ML model performance tracking"""
    
    collection_name = "model_performance_logs"
    
    # Model identification
    model_name: str = Field(..., description="Name of the model")
    model_version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Type: image, tabular, text, ensemble")
    
    # Performance metrics
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_type: str = Field(..., description="Type of input processed")
    processing_time_ms: int = Field(..., description="Time taken for prediction")
    
    # Accuracy metrics
    accuracy: Optional[float] = Field(None, description="Prediction accuracy")
    confidence_score: float = Field(..., description="Model confidence")
    uncertainty_score: float = Field(..., description="Prediction uncertainty")
    
    # Input characteristics
    input_size_mb: Optional[float] = Field(None, description="Size of input in MB")
    input_complexity: Optional[str] = Field(None, description="Complexity assessment")
    
    # System metrics
    cpu_usage_percent: Optional[float] = Field(None)
    memory_usage_mb: Optional[float] = Field(None)
    gpu_usage_percent: Optional[float] = Field(None)
    
    # Error tracking
    error_occurred: bool = Field(default=False)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    
    class Settings:
        name = "model_performance_logs"
        indexes = [
            "model_name",
            "model_version", 
            "model_type",
            "prediction_timestamp"
        ]

class PHIAccessLog(Document):
    """MongoDB document for PHI (Protected Health Information) access tracking"""
    
    collection_name = "phi_access_logs"
    
    # Access details
    access_id: str = Field(..., description="Unique access identifier")
    user_id: str = Field(..., description="User accessing PHI")
    patient_id: Optional[str] = Field(None, description="Patient identifier if applicable")
    analysis_id: Optional[str] = Field(None, description="Analysis ID if applicable")
    
    # PHI details
    phi_type: str = Field(..., description="Type of PHI accessed")
    phi_fields: List[str] = Field(default_factory=list, description="Specific PHI fields accessed")
    data_volume: int = Field(..., description="Volume of data accessed in bytes")
    
    # Access context
    access_timestamp: datetime = Field(default_factory=datetime.utcnow)
    access_reason: str = Field(..., description="Purpose of access")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Client user agent")
    
    # Session details
    session_id: Optional[str] = Field(None, description="Session identifier")
    session_duration_minutes: Optional[int] = Field(None)
    
    # Compliance
    consent_obtained: bool = Field(default=False, description="Patient consent on file")
    retention_policy_applied: str = Field(..., description="Data retention policy")
    data_deletion_scheduled: Optional[datetime] = Field(None)
    
    class Settings:
        name = "phi_access_logs"
        indexes = [
            "user_id",
            "patient_id",
            "analysis_id",
            "phi_type",
            "access_timestamp"
        ]

class SystemMetricsLog(Document):
    """MongoDB document for system performance and health metrics"""
    
    collection_name = "system_metrics_logs"
    
    # Metrics identification
    metric_timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_name: str = Field(..., description="Service generating metrics")
    environment: str = Field(..., description="Environment (prod, staging, dev)")
    
    # Performance metrics
    request_count: int = Field(default=0)
    response_time_avg_ms: float = Field(default=0.0)
    error_rate_percent: float = Field(default=0.0)
    
    # Resource usage
    cpu_usage_percent: float = Field(default=0.0)
    memory_usage_percent: float = Field(default=0.0)
    disk_usage_percent: float = Field(default=0.0)
    network_io_mb_per_sec: float = Field(default=0.0)
    
    # Queue metrics
    active_tasks: int = Field(default=0)
    queued_tasks: int = Field(default=0)
    failed_tasks_last_hour: int = Field(default=0)
    
    # Database metrics
    db_connections_active: int = Field(default=0)
    db_query_time_avg_ms: float = Field(default=0.0)
    
    # Health checks
    health_check_passed: bool = Field(default=True)
    alerts_triggered: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "system_metrics_logs"
        indexes = [
            "service_name",
            "metric_timestamp",
            "environment"
        ]

class DataRetentionLog(Document):
    """MongoDB document for data retention and deletion tracking"""
    
    collection_name = "data_retention_logs"
    
    # Deletion details
    deletion_id: str = Field(..., description="Unique deletion identifier")
    data_type: str = Field(..., description="Type of data deleted")
    record_count: int = Field(..., description="Number of records deleted")
    data_size_mb: float = Field(..., description="Size of data deleted in MB")
    
    # Retention policy
    retention_policy: str = Field(..., description="Policy applied for deletion")
    retention_period_days: int = Field(..., description="Retention period in days")
    legal_hold: bool = Field(default=False, description="If legal hold prevented deletion")
    
    # Execution details
    deletion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    deletion_method: str = Field(..., description="Method used for deletion")
    executed_by: str = Field(..., description="User/system that performed deletion")
    
    # Verification
    verification_completed: bool = Field(default=False)
    verification_timestamp: Optional[datetime] = Field(None)
    verification_method: Optional[str] = Field(None)
    
    # Audit trail
    original_request_id: Optional[str] = Field(None, description="Original request triggering deletion")
    compliance_officer: Optional[str] = Field(None, description="Compliance officer approval")
    
    class Settings:
        name = "data_retention_logs"
        indexes = [
            "data_type",
            "deletion_timestamp",
            "retention_policy"
        ]
