from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from backend.db import Base

class UserRole:
    CLINICIAN = "clinician"
    ADMIN = "admin"
    RESEARCHER = "researcher"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.CLINICIAN)
    department = Column(String(100), nullable=True)
    license_number = Column(String(100), nullable=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(String(10), default="0", nullable=False)
    
    # Security
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
