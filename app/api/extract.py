from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database_session, get_llm_provider
from app.llm import LLMProvider
from app.schemas import ExtractionErrorResponse, SyncExtractionResponse
from app.services import SyncExtractionService, UnknownSessionError

router = APIRouter(tags=["extraction"])

_ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/extract", response_model=SyncExtractionResponse)
async def extract_document(
    request: Request,
    document: UploadFile | None = File(default=None),
    session_id_text: str | None = Form(default=None, alias="sessionId"),
    mode: str = Query(default="sync"),
    db_session: AsyncSession = Depends(get_database_session),
    llm_provider: LLMProvider | None = Depends(get_llm_provider),
) -> JSONResponse:
    if mode != "sync":
        return _error_response(
            status_code=400,
            error="UNSUPPORTED_MODE",
            message="Component 5 currently supports only mode=sync. Async flow begins in Component 6.",
        )

    if document is None:
        return _error_response(
            status_code=400,
            error="MISSING_FILE",
            message="A multipart file field named 'document' is required.",
        )

    if document.content_type not in _ALLOWED_MIME_TYPES:
        return _error_response(
            status_code=400,
            error="UNSUPPORTED_FORMAT",
            message="Supported file types are application/pdf, image/jpeg, and image/png.",
        )

    content_bytes = await document.read()
    if not content_bytes:
        return _error_response(
            status_code=400,
            error="EMPTY_FILE",
            message="Uploaded document is empty.",
        )

    if len(content_bytes) > _MAX_UPLOAD_SIZE_BYTES:
        return _error_response(
            status_code=413,
            error="FILE_TOO_LARGE",
            message="Uploaded document exceeds the 10 MB limit.",
        )

    session_id: UUID | None = None
    if session_id_text is not None:
        try:
            session_id = UUID(session_id_text)
        except ValueError:
            return _error_response(
                status_code=400,
                error="INVALID_SESSION_ID",
                message="Provided sessionId is not a valid UUID.",
            )

    service = SyncExtractionService(
        db_session=db_session,
        provider=llm_provider,
        prompt_version=request.app.state.settings.prompt_version,
        provider_error_message=getattr(request.app.state, "llm_provider_error", None),
    )

    try:
        outcome = await service.run(
            file_name=document.filename or "uploaded-document",
            mime_type=document.content_type,
            content_bytes=content_bytes,
            session_id=session_id,
        )
    except UnknownSessionError:
        await db_session.rollback()
        return _error_response(
            status_code=404,
            error="SESSION_NOT_FOUND",
            message="Provided sessionId does not exist.",
        )
    except Exception:
        await db_session.rollback()
        raise

    if outcome.error_code is None:
        payload = SyncExtractionResponse.from_extraction(outcome.extraction)
        return JSONResponse(
            status_code=outcome.status_code,
            content=payload.model_dump(mode="json", by_alias=True),
            headers=outcome.headers,
        )

    return _error_response(
        status_code=outcome.status_code,
        error=outcome.error_code,
        message=outcome.message or "Document extraction failed.",
        extraction_id=outcome.extraction.id,
        headers=outcome.headers,
    )


def _error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    extraction_id: UUID | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ExtractionErrorResponse(
        error=error,
        message=message,
        extractionId=extraction_id,
        retryAfterMs=None,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", by_alias=True),
        headers=headers or {},
    )
