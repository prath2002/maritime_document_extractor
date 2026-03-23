import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.repos.extraction_repo import ExtractionRepo
from app.db.repos.job_repo import JobRepo
from app.db.repos.session_repo import SessionRepo
from app.db.repos.validation_repo import ValidationRepo
from tests.support.builders import extraction_payload, job_payload, typed_expiry_date, validation_payload


async def test_session_repo_create_get_and_exists(db_session):
    repo = SessionRepo(db_session)

    record = await repo.create()
    fetched = await repo.get_by_id(record.id)

    assert fetched is not None
    assert fetched.id == record.id
    assert await repo.exists(record.id) is True


async def test_session_repo_returns_none_for_missing_session(db_session):
    repo = SessionRepo(db_session)

    missing = await repo.get_by_id(uuid.uuid4())

    assert missing is None


async def test_extraction_repo_create_and_get(db_session):
    session_repo = SessionRepo(db_session)
    extraction_repo = ExtractionRepo(db_session)
    session = await session_repo.create()

    record = await extraction_repo.create(
        session_id=session.id,
        **extraction_payload(
            file_hash="hash-a",
            document_type="PEME",
            applicable_role="ENGINE",
            confidence="HIGH",
        ),
    )
    fetched = await extraction_repo.get_by_id(record.id)

    assert fetched is not None
    assert fetched.id == record.id
    assert fetched.file_name == "sample.pdf"


async def test_extraction_repo_create_or_get_existing_handles_deduplication(db_session):
    session_repo = SessionRepo(db_session)
    extraction_repo = ExtractionRepo(db_session)
    session = await session_repo.create()

    first, first_created = await extraction_repo.create_or_get_existing(
        session_id=session.id,
        **extraction_payload(file_hash="hash-dup"),
    )
    second, second_created = await extraction_repo.create_or_get_existing(
        session_id=session.id,
        **extraction_payload(file_hash="hash-dup"),
    )
    records = await extraction_repo.list_by_session(session.id)

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert len(records) == 1


async def test_extraction_repo_duplicate_insert_hits_unique_constraint(db_session):
    session_repo = SessionRepo(db_session)
    extraction_repo = ExtractionRepo(db_session)
    session = await session_repo.create()

    await extraction_repo.create(
        session_id=session.id,
        **extraction_payload(file_hash="hash-direct-dup"),
    )

    with pytest.raises(IntegrityError):
        await extraction_repo.create(
            session_id=session.id,
            **extraction_payload(file_name="sample-2.pdf", file_hash="hash-direct-dup"),
        )


async def test_extraction_repo_lists_session_records_in_creation_order(db_session):
    session_repo = SessionRepo(db_session)
    extraction_repo = ExtractionRepo(db_session)
    session = await session_repo.create()
    first_created_at = datetime(2026, 3, 20, tzinfo=UTC)
    second_created_at = first_created_at + timedelta(minutes=1)

    first = await extraction_repo.create(
        session_id=session.id,
        **extraction_payload(file_name="first.pdf", file_hash="hash-order-1", created_at=first_created_at),
    )
    second = await extraction_repo.create(
        session_id=session.id,
        **extraction_payload(file_name="second.pdf", file_hash="hash-order-2", created_at=second_created_at),
    )
    records = await extraction_repo.list_by_session(session.id)

    assert [record.id for record in records] == [first.id, second.id]


async def test_extraction_repo_supports_typed_expiry_dates(db_session):
    session_repo = SessionRepo(db_session)
    extraction_repo = ExtractionRepo(db_session)
    session = await session_repo.create()

    record = await extraction_repo.create(
        session_id=session.id,
        **extraction_payload(file_name="expiry.pdf", file_hash="hash-date", date_of_expiry=typed_expiry_date()),
    )

    assert record.date_of_expiry == typed_expiry_date()


async def test_job_repo_create_get_and_pending_lookup(db_session):
    session_repo = SessionRepo(db_session)
    job_repo = JobRepo(db_session)
    session = await session_repo.create()

    queued = await job_repo.create(session_id=session.id, **job_payload(status="QUEUED"))
    await job_repo.create(session_id=session.id, **job_payload(status="PROCESSING"))
    await job_repo.create(session_id=session.id, **job_payload(status="COMPLETE"))

    fetched = await job_repo.get_by_id(queued.id)
    pending = await job_repo.list_pending_for_session(session.id)

    assert fetched is not None
    assert fetched.id == queued.id
    assert {job.status for job in pending} == {"QUEUED", "PROCESSING"}


async def test_job_repo_returns_none_for_missing_job(db_session):
    job_repo = JobRepo(db_session)

    assert await job_repo.get_by_id(uuid.uuid4()) is None


async def test_validation_repo_create_and_get_latest(db_session):
    session_repo = SessionRepo(db_session)
    validation_repo = ValidationRepo(db_session)
    session = await session_repo.create()

    older = await validation_repo.create(
        session_id=session.id,
        **validation_payload(result_json={"summary": "older"}, created_at=datetime(2026, 3, 20, tzinfo=UTC)),
    )
    newer = await validation_repo.create(
        session_id=session.id,
        **validation_payload(
            overall_status="APPROVED",
            overall_score=91,
            result_json={"summary": "newer"},
            created_at=datetime(2026, 3, 21, tzinfo=UTC),
        ),
    )

    latest = await validation_repo.get_latest_for_session(session.id)
    listed = await validation_repo.list_by_session(session.id)

    assert latest is not None
    assert latest.id == newer.id
    assert [record.id for record in listed] == [newer.id, older.id]


async def test_validation_repo_returns_none_for_missing_validation(db_session):
    validation_repo = ValidationRepo(db_session)

    assert await validation_repo.get_latest_for_session(uuid.uuid4()) is None
