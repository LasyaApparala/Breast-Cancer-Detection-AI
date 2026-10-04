from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from backend.db import Base

class AnalysisStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Clinical and file data
    clinical_data = Column(JSON, nullable=False)
    files = Column(JSON, default=list)
    
    # AI results
    result = Column(JSON, nullable=True)
    
    # Status tracking
    status = Column(String(20), nullable=False, default=AnalysisStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)
    
    # Review workflow
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_requested_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    input_hash = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, status={self.status}, user_id={self.user_id})>"
