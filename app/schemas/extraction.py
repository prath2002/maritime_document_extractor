from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Extraction


class ExtractionErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error: str
    message: str
    extraction_id: UUID | None = Field(default=None, alias="extractionId")
    retry_after_ms: int | None = Field(default=None, alias="retryAfterMs")


class SyncExtractionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    session_id: UUID = Field(alias="sessionId")
    file_name: str = Field(alias="fileName")
    document_type: str | None = Field(alias="documentType")
    document_name: str | None = Field(alias="documentName")
    applicable_role: str | None = Field(alias="applicableRole")
    category: str | None
    confidence: str | None
    holder_name: str | None = Field(alias="holderName")
    date_of_birth: str | None = Field(alias="dateOfBirth")
    sirb_number: str | None = Field(alias="sirbNumber")
    passport_number: str | None = Field(alias="passportNumber")
    fields: list[dict[str, Any]]
    validity: dict[str, Any]
    compliance: dict[str, Any]
    medical_data: dict[str, Any] = Field(alias="medicalData")
    flags: list[dict[str, Any]]
    is_expired: bool = Field(alias="isExpired")
    processing_time_ms: int | None = Field(alias="processingTimeMs")
    summary: str | None
    created_at: datetime = Field(alias="createdAt")

    @classmethod
    def from_extraction(cls, extraction: Extraction) -> "SyncExtractionResponse":
        validity = extraction.validity_json or {
            "dateOfIssue": None,
            "dateOfExpiry": None,
            "isExpired": extraction.is_expired,
            "daysUntilExpiry": None,
            "revalidationRequired": None,
        }
        compliance = extraction.compliance_json or {
            "issuingAuthority": None,
            "regulationReference": None,
            "imoModelCourse": None,
            "recognizedAuthority": None,
            "limitations": None,
        }
        medical_data = extraction.medical_data_json or {
            "fitnessResult": "N/A",
            "drugTestResult": "N/A",
            "restrictions": None,
            "specialNotes": None,
            "expiryDate": None,
        }

        return cls(
            id=extraction.id,
            sessionId=extraction.session_id,
            fileName=extraction.file_name,
            documentType=extraction.document_type,
            documentName=extraction.document_name,
            applicableRole=extraction.applicable_role,
            category=extraction.category,
            confidence=extraction.confidence,
            holderName=extraction.holder_name,
            dateOfBirth=extraction.date_of_birth,
            sirbNumber=extraction.sirb_number,
            passportNumber=extraction.passport_number,
            fields=extraction.fields_json or [],
            validity=validity,
            compliance=compliance,
            medicalData=medical_data,
            flags=extraction.flags_json or [],
            isExpired=extraction.is_expired,
            processingTimeMs=extraction.processing_time_ms,
            summary=extraction.summary,
            createdAt=extraction.created_at,
        )
