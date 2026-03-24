from __future__ import annotations

import json

from app.llm.base import LLMProvider, ProviderRequestError, ProviderTimeoutError
from app.llm.prompts import EXTRACTION_PROMPT
from app.llm.types import (
    AttemptStage,
    ConfidenceLevel,
    ExtractionFailureCode,
    ExtractionPipelineFailure,
    ExtractionPipelineSuccess,
    PreparedDocument,
)
from app.services.extraction_core import ExtractionCoreService


class StubProvider(LLMProvider):
    provider_name = "stub"
    model_name = "stub-model"

    def __init__(self, *, document_responses=None, text_responses=None):
        self._document_responses = list(document_responses or [])
        self._text_responses = list(text_responses or [])

    async def extract_document(self, *, document: PreparedDocument, prompt: str, timeout_seconds: int = 30) -> str:
        response = self._document_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def generate_text(self, *, prompt: str, timeout_seconds: int = 15) -> str:
        response = self._text_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def health_check(self) -> tuple[str, str | None]:
        return "OK", None



def _document() -> PreparedDocument:
    return PreparedDocument(
        file_name="sample.pdf",
        mime_type="application/pdf",
        content_bytes=b"sample-pdf-bytes",
    )



def _payload(*, confidence: str = "HIGH") -> dict[str, object]:
    return {
        "detection": {
            "documentType": "PEME",
            "documentName": "Pre-Employment Medical Examination",
            "category": "MEDICAL",
            "applicableRole": "BOTH",
            "isRequired": True,
            "confidence": confidence,
            "detectionReason": "The form title references PEME.",
        },
        "holder": {
            "fullName": "Samuel P. Samoya",
            "dateOfBirth": "12/03/1988",
            "nationality": "Filipino",
            "passportNumber": None,
            "sirbNumber": "C0869326",
            "rank": "Engine Cadet",
            "photo": "PRESENT",
        },
        "fields": [
            {
                "key": "certificate_number",
                "label": "Certificate Number",
                "value": "PEME-123",
                "importance": "HIGH",
                "status": "OK",
            }
        ],
        "validity": {
            "dateOfIssue": "06/01/2025",
            "dateOfExpiry": "06/01/2027",
            "isExpired": False,
            "daysUntilExpiry": 660,
            "revalidationRequired": False,
        },
        "compliance": {
            "issuingAuthority": "Maritime Health Center",
            "regulationReference": None,
            "imoModelCourse": None,
            "recognizedAuthority": True,
            "limitations": None,
        },
        "medicalData": {
            "fitnessResult": "FIT",
            "drugTestResult": "NEGATIVE",
            "restrictions": None,
            "specialNotes": "Cleared by physician.",
            "expiryDate": "06/01/2027",
        },
        "flags": [{"severity": "LOW", "message": "No material concerns."}],
        "summary": "The holder is medically fit for deployment.",
    }


async def test_extraction_core_returns_success_for_clean_json():
    provider = StubProvider(document_responses=[json.dumps(_payload())])
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineSuccess)
    assert result.extraction.detection.document_type == "PEME"
    assert result.extraction.confidence == ConfidenceLevel.HIGH
    assert result.selected_stage == AttemptStage.INITIAL
    assert len(result.attempts) == 1


async def test_malformed_json_triggers_repair_and_returns_repaired_result():
    provider = StubProvider(
        document_responses=['```json\n{"broken": true\n```'],
        text_responses=[json.dumps(_payload())],
    )
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineSuccess)
    assert result.selected_stage == AttemptStage.REPAIR
    assert [attempt.stage for attempt in result.attempts] == [AttemptStage.INITIAL, AttemptStage.REPAIR]


async def test_repair_failure_returns_parse_fail():
    provider = StubProvider(
        document_responses=['not-json-at-all'],
        text_responses=['still not json'],
    )
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineFailure)
    assert result.error_code == ExtractionFailureCode.LLM_JSON_PARSE_FAIL
    assert result.retryable is False
    assert len(result.attempts) == 2


async def test_timeout_returns_retryable_failure():
    provider = StubProvider(document_responses=[ProviderTimeoutError()])
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineFailure)
    assert result.error_code == ExtractionFailureCode.LLM_TIMEOUT
    assert result.retryable is True


async def test_low_confidence_retry_selects_higher_confidence_result():
    provider = StubProvider(
        document_responses=[json.dumps(_payload(confidence="LOW")), json.dumps(_payload(confidence="HIGH"))],
    )
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineSuccess)
    assert result.extraction.confidence == ConfidenceLevel.HIGH
    assert result.selected_stage == AttemptStage.RETRY
    assert len(result.attempts) == 2


async def test_low_confidence_retry_keeps_original_when_retry_is_not_better():
    provider = StubProvider(
        document_responses=[
            json.dumps(_payload(confidence="LOW")),
            json.dumps(_payload(confidence="LOW")),
        ],
    )
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineSuccess)
    assert result.extraction.confidence == ConfidenceLevel.LOW
    assert result.selected_stage == AttemptStage.INITIAL
    assert len(result.attempts) == 2


async def test_provider_error_returns_controlled_failure():
    provider = StubProvider(document_responses=[ProviderRequestError("provider rejected request")])
    service = ExtractionCoreService(provider=provider, prompt_version="v1.0")

    result = await service.run(document=_document(), prompt=EXTRACTION_PROMPT)

    assert isinstance(result, ExtractionPipelineFailure)
    assert result.error_code == ExtractionFailureCode.LLM_PROVIDER_ERROR
    assert result.retryable is False
