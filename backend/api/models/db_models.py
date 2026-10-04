"""SQLAlchemy ORM models mirroring the PostgreSQL schema."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB  # Use generic JSON; works for both SQLite and PostgreSQL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class Session(Base):
    """Represents a classification session."""

    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # status values: queued, processing, complete, failed, delayed
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="session", cascade="all, delete-orphan"
    )
    classification_results: Mapped[list["ClassificationResult"]] = relationship(
        "ClassificationResult", back_populates="session", cascade="all, delete-orphan"
    )
    audit_trail_entries: Mapped[list["AuditTrailEntry"]] = relationship(
        "AuditTrailEntry", back_populates="session", cascade="all, delete-orphan"
    )
    override_logs: Mapped[list["OverrideLog"]] = relationship(
        "OverrideLog", back_populates="session", cascade="all, delete-orphan"
    )


class Document(Base):
    """Represents an uploaded document associated with a session."""

    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    # Relationship
    session: Mapped[Optional["Session"]] = relationship(
        "Session", back_populates="documents"
    )


class ClassificationResult(Base):
    """Stores the output of a classification run for a session."""

    __tablename__ = "classification_results"

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=True,
    )
    severity_label: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    base_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    completeness_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    # features_json is encrypted at the application layer before insert
    features_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    classified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    # Relationship
    session: Mapped[Optional["Session"]] = relationship(
        "Session", back_populates="classification_results"
    )


class AuditTrailEntry(Base):
    """Records the provenance of each feature used in a classification."""

    __tablename__ = "audit_trail"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=True,
    )
    feature_name: Mapped[str] = mapped_column(Text, nullable=False)
    value_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # source values: document, manual_entry, imaging, missing
    source: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_extracted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_by_user: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="FALSE"
    )
    imaging_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 3), nullable=True
    )

    # Relationship
    session: Mapped[Optional["Session"]] = relationship(
        "Session", back_populates="audit_trail_entries"
    )


class OverrideLog(Base):
    """Records clinician overrides of classification results."""

    __tablename__ = "override_log"

    override_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    original_label: Mapped[str] = mapped_column(Text, nullable=False)
    override_label: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    session: Mapped[Optional["Session"]] = relationship(
        "Session", back_populates="override_logs"
    )


class ModelVersion(Base):
    """Tracks registered ML model versions and their performance metrics."""

    __tablename__ = "model_versions"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_tag: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    training_datasets: Mapped[Any] = mapped_column(JSONB, nullable=False)
    auc: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    sensitivity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    specificity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    ece: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="FALSE"
    )
    regression_passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="FALSE"
    )
