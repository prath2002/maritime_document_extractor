from __future__ import annotations

import base64

from app.llm.types import PreparedDocument


def prepare_document(*, file_name: str, mime_type: str, content_bytes: bytes) -> PreparedDocument:
    if not file_name:
        raise ValueError("file_name is required")
    if not mime_type:
        raise ValueError("mime_type is required")
    if not content_bytes:
        raise ValueError("content_bytes must not be empty")

    return PreparedDocument(file_name=file_name, mime_type=mime_type, content_bytes=content_bytes)


def document_to_base64(document: PreparedDocument) -> str:
    return base64.b64encode(document.content_bytes).decode("ascii")
