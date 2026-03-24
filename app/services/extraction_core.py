from __future__ import annotations

from time import perf_counter

from pydantic import ValidationError

from app.llm.base import ProviderRequestError, ProviderTimeoutError
from app.llm.prompts import build_low_confidence_retry_prompt, build_repair_prompt
from app.llm.types import (
    ConfidenceLevel,
    ExtractionAttempt,
    ExtractionFailureCode,
    ExtractionPipelineFailure,
    ExtractionPipelineResult,
    ExtractionPipelineSuccess,
    AttemptStage,
    PreparedDocument,
    StructuredExtraction,
    confidence_rank,
)
from app.utils.json_extractor import extract_json_object


class ExtractionCoreService:
    def __init__(
        self,
        *,
        provider,
        prompt_version: str,
        extraction_timeout_seconds: int = 30,
        repair_timeout_seconds: int = 15,
    ):
        self.provider = provider
        self.prompt_version = prompt_version
        self.extraction_timeout_seconds = extraction_timeout_seconds
        self.repair_timeout_seconds = repair_timeout_seconds

    async def run(self, *, document: PreparedDocument, prompt: str) -> ExtractionPipelineResult:
        started_at = perf_counter()
        attempts: list[ExtractionAttempt] = []

        try:
            initial_raw = await self.provider.extract_document(
                document=document,
                prompt=prompt,
                timeout_seconds=self.extraction_timeout_seconds,
            )
            initial_parsed = self._parse_raw_response(initial_raw)
            attempts.append(
                ExtractionAttempt(
                    stage=AttemptStage.INITIAL,
                    prompt=prompt,
                    raw_response=initial_raw,
                    parsed_extraction=initial_parsed,
                )
            )
        except ProviderTimeoutError as exc:
            attempts.append(
                ExtractionAttempt(
                    stage=AttemptStage.INITIAL,
                    prompt=prompt,
                    error_message=str(exc),
                )
            )
            return self._build_failure(
                attempts=attempts,
                error_code=ExtractionFailureCode.LLM_TIMEOUT,
                message=str(exc),
                retryable=True,
                started_at=started_at,
            )
        except ProviderRequestError as exc:
            attempts.append(
                ExtractionAttempt(
                    stage=AttemptStage.INITIAL,
                    prompt=prompt,
                    error_message=str(exc),
                )
            )
            return self._build_failure(
                attempts=attempts,
                error_code=ExtractionFailureCode.LLM_PROVIDER_ERROR,
                message=str(exc),
                retryable=getattr(exc, "retryable", False),
                started_at=started_at,
            )

        selected_extraction = initial_parsed
        selected_stage = AttemptStage.INITIAL

        if selected_extraction is None:
            repair_prompt = build_repair_prompt(initial_raw)
            repair_attempt = await self._run_repair_attempt(prompt=repair_prompt)
            attempts.append(repair_attempt)
            selected_extraction = repair_attempt.parsed_extraction
            selected_stage = AttemptStage.REPAIR

            if selected_extraction is None:
                return self._build_failure(
                    attempts=attempts,
                    error_code=ExtractionFailureCode.LLM_JSON_PARSE_FAIL,
                    message=(
                        "Document extraction failed after retry. The raw response has been stored for review."
                    ),
                    retryable=False,
                    started_at=started_at,
                )

        if selected_extraction.confidence == ConfidenceLevel.LOW:
            retry_prompt = build_low_confidence_retry_prompt(
                base_prompt=prompt,
                file_name=document.file_name,
                mime_type=document.mime_type,
            )
            retry_attempt = await self._run_retry_attempt(document=document, prompt=retry_prompt)
            attempts.append(retry_attempt)

            retried_extraction = retry_attempt.parsed_extraction
            if (
                retried_extraction is not None
                and confidence_rank(retried_extraction.confidence)
                > confidence_rank(selected_extraction.confidence)
            ):
                selected_extraction = retried_extraction
                selected_stage = AttemptStage.RETRY

        return ExtractionPipelineSuccess(
            extraction=selected_extraction,
            attempts=attempts,
            selected_stage=selected_stage,
            prompt_version=self.prompt_version,
            processing_time_ms=self._elapsed_ms(started_at),
        )

    async def _run_repair_attempt(self, *, prompt: str) -> ExtractionAttempt:
        try:
            raw_response = await self.provider.generate_text(
                prompt=prompt,
                timeout_seconds=self.repair_timeout_seconds,
            )
            return ExtractionAttempt(
                stage=AttemptStage.REPAIR,
                prompt=prompt,
                raw_response=raw_response,
                parsed_extraction=self._parse_raw_response(raw_response),
            )
        except ProviderRequestError as exc:
            return ExtractionAttempt(stage=AttemptStage.REPAIR, prompt=prompt, error_message=str(exc))

    async def _run_retry_attempt(
        self,
        *,
        document: PreparedDocument,
        prompt: str,
    ) -> ExtractionAttempt:
        try:
            raw_response = await self.provider.extract_document(
                document=document,
                prompt=prompt,
                timeout_seconds=self.extraction_timeout_seconds,
            )
            return ExtractionAttempt(
                stage=AttemptStage.RETRY,
                prompt=prompt,
                raw_response=raw_response,
                parsed_extraction=self._parse_raw_response(raw_response),
            )
        except ProviderRequestError as exc:
            return ExtractionAttempt(stage=AttemptStage.RETRY, prompt=prompt, error_message=str(exc))

    def _parse_raw_response(self, raw_response: str) -> StructuredExtraction | None:
        parsed_object = extract_json_object(raw_response)
        if parsed_object is None:
            return None

        try:
            return StructuredExtraction.model_validate(parsed_object)
        except ValidationError:
            return None

    def _build_failure(
        self,
        *,
        attempts: list[ExtractionAttempt],
        error_code: ExtractionFailureCode,
        message: str,
        retryable: bool,
        started_at: float,
    ) -> ExtractionPipelineFailure:
        return ExtractionPipelineFailure(
            error_code=error_code,
            message=message,
            retryable=retryable,
            attempts=attempts,
            prompt_version=self.prompt_version,
            processing_time_ms=self._elapsed_ms(started_at),
        )

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((perf_counter() - started_at) * 1000))

