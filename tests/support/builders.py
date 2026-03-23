from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


def extraction_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "file_name": "sample.pdf",
        "file_hash": "hash-default",
        "status": "COMPLETE",
        "prompt_version": "v1.0",
        "created_at": datetime(2026, 3, 20, tzinfo=UTC),
        "document_type": None,
        "applicable_role": None,
        "confidence": None,
        "is_expired": False,
        "date_of_expiry": None,
    }
    payload.update(overrides)
    return payload


def job_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "QUEUED",
    }
    payload.update(overrides)
    return payload


def validation_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "overall_status": "CONDITIONAL",
        "overall_score": 72,
        "result_json": {"summary": "validation"},
        "prompt_version": "v1.0",
        "created_at": datetime(2026, 3, 20, tzinfo=UTC),
    }
    payload.update(overrides)
    return payload


def typed_expiry_date() -> date:
    return date(2027, 1, 6)
