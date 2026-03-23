import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    extractions: Mapped[list["Extraction"]] = relationship(back_populates="session")
    jobs: Mapped[list["Job"]] = relationship(back_populates="session")
    validations: Mapped[list["Validation"]] = relationship(back_populates="session")


class Extraction(Base):
    __tablename__ = "extractions"
    __table_args__ = (
        UniqueConstraint("session_id", "file_hash", name="idx_extractions_dedup"),
        Index("idx_extractions_session_id", "session_id"),
        Index("idx_extractions_date_of_expiry", "date_of_expiry"),
        Index("idx_extractions_document_type", "document_type"),
        Index("idx_extractions_is_expired", "is_expired"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="COMPLETE")

    document_type: Mapped[str | None] = mapped_column(Text)
    document_name: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    applicable_role: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    holder_name: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[str | None] = mapped_column(Text)
    nationality: Mapped[str | None] = mapped_column(Text)
    sirb_number: Mapped[str | None] = mapped_column(Text)
    passport_number: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[str | None] = mapped_column(Text)
    date_of_issue: Mapped[date | None] = mapped_column(Date)
    date_of_expiry: Mapped[date | None] = mapped_column(Date)
    is_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    days_until_expiry: Mapped[int | None] = mapped_column(Integer)
    issuing_authority: Mapped[str | None] = mapped_column(Text)
    fitness_result: Mapped[str | None] = mapped_column(Text)
    drug_test_result: Mapped[str | None] = mapped_column(Text)

    fields_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    validity_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    medical_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    compliance_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    flags_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    raw_llm_response: Mapped[str | None] = mapped_column(Text)

    summary: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1.0")
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[Session] = relationship(back_populates="extractions")
    jobs: Mapped[list["Job"]] = relationship(back_populates="extraction")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_status_queued_at", "status", "queued_at"),
        Index("idx_jobs_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
    )
    extraction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extractions.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="QUEUED")
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    queue_position: Mapped[int | None] = mapped_column(Integer)
    webhook_url: Mapped[str | None] = mapped_column(Text)
    webhook_delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[Session | None] = relationship(back_populates="jobs")
    extraction: Mapped[Extraction | None] = relationship(back_populates="jobs")


class Validation(Base):
    __tablename__ = "validations"
    __table_args__ = (
        Index("idx_validations_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_status: Mapped[str] = mapped_column(Text, nullable=False)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[Session] = relationship(back_populates="validations")
