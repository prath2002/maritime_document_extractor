from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class DocumentCategory(StrEnum):
    IDENTITY = "IDENTITY"
    CERTIFICATION = "CERTIFICATION"
    STCW_ENDORSEMENT = "STCW_ENDORSEMENT"
    MEDICAL = "MEDICAL"
    TRAINING = "TRAINING"
    FLAG_STATE = "FLAG_STATE"
    OTHER = "OTHER"


class ApplicableRole(StrEnum):
    DECK = "DECK"
    ENGINE = "ENGINE"
    BOTH = "BOTH"
    NA = "N/A"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FieldImportance(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FieldStatus(StrEnum):
    OK = "OK"
    EXPIRED = "EXPIRED"
    WARNING = "WARNING"
    MISSING = "MISSING"
    NA = "N/A"


class PhotoPresence(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class FitnessResult(StrEnum):
    FIT = "FIT"
    UNFIT = "UNFIT"
    NA = "N/A"


class DrugTestResult(StrEnum):
    NEGATIVE = "NEGATIVE"
    POSITIVE = "POSITIVE"
    NA = "N/A"


class FlagSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AttemptStage(StrEnum):
    INITIAL = "initial"
    REPAIR = "repair"
    RETRY = "retry"


class ExtractionFailureCode(StrEnum):
    LLM_JSON_PARSE_FAIL = "LLM_JSON_PARSE_FAIL"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"


_CONFIDENCE_RANK = {
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MEDIUM: 2,
    ConfidenceLevel.HIGH: 3,
}


def confidence_rank(level: ConfidenceLevel) -> int:
    return _CONFIDENCE_RANK[level]


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    file_name: str
    mime_type: str
    content_bytes: bytes

    @property
    def byte_size(self) -> int:
        return len(self.content_bytes)


class DetectionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_type: str = Field(alias="documentType")
    document_name: str = Field(alias="documentName")
    category: DocumentCategory
    applicable_role: ApplicableRole = Field(alias="applicableRole")
    is_required: bool = Field(alias="isRequired")
    confidence: ConfidenceLevel
    detection_reason: str = Field(alias="detectionReason")


class HolderPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    full_name: str | None = Field(alias="fullName")
    date_of_birth: str | None = Field(alias="dateOfBirth")
    nationality: str | None = None
    passport_number: str | None = Field(alias="passportNumber")
    sirb_number: str | None = Field(alias="sirbNumber")
    rank: str | None = None
    photo: PhotoPresence


class ExtractedField(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    label: str
    value: str
    importance: FieldImportance
    status: FieldStatus


class ValidityPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    date_of_issue: str | None = Field(alias="dateOfIssue")
    date_of_expiry: str | None = Field(alias="dateOfExpiry")
    is_expired: bool = Field(alias="isExpired")
    days_until_expiry: int | None = Field(alias="daysUntilExpiry")
    revalidation_required: bool | None = Field(alias="revalidationRequired")


class CompliancePayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    issuing_authority: str | None = Field(alias="issuingAuthority")
    regulation_reference: str | None = Field(alias="regulationReference")
    imo_model_course: str | None = Field(alias="imoModelCourse")
    recognized_authority: bool | None = Field(alias="recognizedAuthority")
    limitations: str | None


class MedicalDataPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    fitness_result: FitnessResult = Field(alias="fitnessResult")
    drug_test_result: DrugTestResult = Field(alias="drugTestResult")
    restrictions: str | None
    special_notes: str | None = Field(alias="specialNotes")
    expiry_date: str | None = Field(alias="expiryDate")


class ComplianceFlag(BaseModel):
    model_config = ConfigDict(extra="ignore")

    severity: FlagSeverity
    message: str


class StructuredExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    detection: DetectionPayload
    holder: HolderPayload
    fields: list[ExtractedField]
    validity: ValidityPayload
    compliance: CompliancePayload
    medical_data: MedicalDataPayload = Field(alias="medicalData")
    flags: list[ComplianceFlag]
    summary: str

    @computed_field
    @property
    def confidence(self) -> ConfidenceLevel:
        return self.detection.confidence


class ExtractionAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: AttemptStage
    prompt: str
    raw_response: str | None = None
    parsed_extraction: StructuredExtraction | None = None
    error_message: str | None = None


class ExtractionPipelineSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["SUCCESS"] = "SUCCESS"
    extraction: StructuredExtraction
    attempts: list[ExtractionAttempt]
    selected_stage: AttemptStage
    prompt_version: str
    processing_time_ms: int

    @computed_field
    @property
    def raw_llm_response(self) -> str | None:
        for attempt in reversed(self.attempts):
            if attempt.stage == self.selected_stage:
                return attempt.raw_response
        return None


class ExtractionPipelineFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["FAILED"] = "FAILED"
    error_code: ExtractionFailureCode
    message: str
    retryable: bool
    attempts: list[ExtractionAttempt]
    prompt_version: str
    processing_time_ms: int

    @computed_field
    @property
    def raw_llm_response(self) -> str | None:
        for attempt in reversed(self.attempts):
            if attempt.raw_response:
                return attempt.raw_response
        return None


ExtractionPipelineResult = ExtractionPipelineSuccess | ExtractionPipelineFailure


def model_dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)

