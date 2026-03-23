from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine


async def test_initial_migration_creates_core_tables(migrated_database):
    engine = create_async_engine(migrated_database, future=True)

    async with engine.connect() as connection:
        table_names = await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

    await engine.dispose()

    assert {"sessions", "extractions", "jobs", "validations"} <= set(table_names)


async def test_initial_migration_creates_required_indexes(migrated_database):
    engine = create_async_engine(migrated_database, future=True)

    async with engine.connect() as connection:
        extraction_indexes = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("extractions")
        )
        job_indexes = await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_indexes("jobs"))
        validation_indexes = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("validations")
        )

    await engine.dispose()

    extraction_index_names = {index["name"] for index in extraction_indexes}
    job_index_names = {index["name"] for index in job_indexes}
    validation_index_names = {index["name"] for index in validation_indexes}

    assert "idx_extractions_dedup" in extraction_index_names
    assert "idx_extractions_session_id" in extraction_index_names
    assert "idx_extractions_date_of_expiry" in extraction_index_names
    assert "idx_extractions_document_type" in extraction_index_names
    assert "idx_extractions_is_expired" in extraction_index_names
    assert "idx_jobs_status" in job_index_names
    assert "idx_jobs_status_queued_at" in job_index_names
    assert "idx_jobs_session_id" in job_index_names
    assert "idx_validations_session_id" in validation_index_names
