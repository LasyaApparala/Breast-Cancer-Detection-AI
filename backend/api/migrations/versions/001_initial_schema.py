"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("mime_type", sa.Text, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("idx_documents_session_id", "documents", ["session_id"])

    # --- classification_results ---
    op.create_table(
        "classification_results",
        sa.Column("result_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("severity_label", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("base_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("completeness_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("model_version", sa.Text, nullable=False),
        sa.Column("features_json", postgresql.JSONB, nullable=False),
        sa.Column("classified_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_classification_results_session_id",
        "classification_results",
        ["session_id"],
    )

    # --- audit_trail ---
    op.create_table(
        "audit_trail",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("feature_name", sa.Text, nullable=False),
        sa.Column("value_used", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("document_ref", sa.Text, nullable=True),
        sa.Column("original_extracted", sa.Text, nullable=True),
        sa.Column(
            "corrected_by_user",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("imaging_confidence", sa.Numeric(4, 3), nullable=True),
    )
    op.create_index("idx_audit_trail_session_id", "audit_trail", ["session_id"])

    # --- override_log ---
    op.create_table(
        "override_log",
        sa.Column("override_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_label", sa.Text, nullable=False),
        sa.Column("override_label", sa.Text, nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("idx_override_log_session_id", "override_log", ["session_id"])

    # --- model_versions ---
    op.create_table(
        "model_versions",
        sa.Column("model_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_tag", sa.Text, nullable=False, unique=True),
        sa.Column("training_datasets", postgresql.JSONB, nullable=False),
        sa.Column("auc", sa.Numeric(5, 4), nullable=True),
        sa.Column("sensitivity", sa.Numeric(5, 4), nullable=True),
        sa.Column("specificity", sa.Numeric(5, 4), nullable=True),
        sa.Column("accuracy", sa.Numeric(5, 4), nullable=True),
        sa.Column("ece", sa.Numeric(5, 4), nullable=True),
        sa.Column("temperature", sa.Numeric(6, 4), nullable=True),
        sa.Column("deployed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "regression_passed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.create_index("idx_model_versions_is_active", "model_versions", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_model_versions_is_active", table_name="model_versions")
    op.drop_table("model_versions")

    op.drop_index("idx_override_log_session_id", table_name="override_log")
    op.drop_table("override_log")

    op.drop_index("idx_audit_trail_session_id", table_name="audit_trail")
    op.drop_table("audit_trail")

    op.drop_index(
        "idx_classification_results_session_id", table_name="classification_results"
    )
    op.drop_table("classification_results")

    op.drop_index("idx_documents_session_id", table_name="documents")
    op.drop_table("documents")

    op.drop_table("sessions")
