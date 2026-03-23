"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-22 19:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("document_name", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("applicable_role", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("holder_name", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Text(), nullable=True),
        sa.Column("nationality", sa.Text(), nullable=True),
        sa.Column("sirb_number", sa.Text(), nullable=True),
        sa.Column("passport_number", sa.Text(), nullable=True),
        sa.Column("rank", sa.Text(), nullable=True),
        sa.Column("date_of_issue", sa.Date(), nullable=True),
        sa.Column("date_of_expiry", sa.Date(), nullable=True),
        sa.Column("is_expired", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("days_until_expiry", sa.Integer(), nullable=True),
        sa.Column("issuing_authority", sa.Text(), nullable=True),
        sa.Column("fitness_result", sa.Text(), nullable=True),
        sa.Column("drug_test_result", sa.Text(), nullable=True),
        sa.Column("fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validity_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("medical_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("compliance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_llm_response", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False, server_default=sa.text("'v1.0'")),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_extractions_session_id", "extractions", ["session_id"], unique=False)
    op.create_index("idx_extractions_dedup", "extractions", ["session_id", "file_hash"], unique=True)
    op.create_index("idx_extractions_date_of_expiry", "extractions", ["date_of_expiry"], unique=False)
    op.create_index("idx_extractions_document_type", "extractions", ["document_type"], unique=False)
    op.create_index("idx_extractions_is_expired", "extractions", ["is_expired"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("queue_position", sa.Integer(), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("webhook_delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("processing_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["extraction_id"], ["extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("idx_jobs_status_queued_at", "jobs", ["status", "queued_at"], unique=False)
    op.create_index("idx_jobs_session_id", "jobs", ["session_id"], unique=False)

    op.create_table(
        "validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_status", sa.Text(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False, server_default=sa.text("'v1.0'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_validations_session_id", "validations", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_validations_session_id", table_name="validations")
    op.drop_table("validations")

    op.drop_index("idx_jobs_session_id", table_name="jobs")
    op.drop_index("idx_jobs_status_queued_at", table_name="jobs")
    op.drop_index("idx_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("idx_extractions_is_expired", table_name="extractions")
    op.drop_index("idx_extractions_document_type", table_name="extractions")
    op.drop_index("idx_extractions_date_of_expiry", table_name="extractions")
    op.drop_index("idx_extractions_dedup", table_name="extractions")
    op.drop_index("idx_extractions_session_id", table_name="extractions")
    op.drop_table("extractions")

    op.drop_table("sessions")
