import ssl

from sqlalchemy.engine import make_url

from app.db.base import build_ssl_connect_arg, normalize_database_url, should_disable_statement_cache


def test_normalize_database_url_translates_sslmode_for_asyncpg():
    database_url, connect_args = normalize_database_url(
        "postgresql+asyncpg://user:pass@host/db?sslmode=require"
    )

    assert database_url == "postgresql+asyncpg://user:pass@host/db"
    assert isinstance(connect_args["ssl"], ssl.SSLContext)


def test_normalize_database_url_preserves_disable_sslmode():
    database_url, connect_args = normalize_database_url(
        "postgresql+asyncpg://user:pass@host/db?sslmode=disable"
    )

    assert database_url == "postgresql+asyncpg://user:pass@host/db"
    assert connect_args["ssl"] is False


def test_build_ssl_connect_arg_uses_non_verifying_context_for_require():
    connect_arg = build_ssl_connect_arg("require")

    assert isinstance(connect_arg, ssl.SSLContext)
    assert connect_arg.check_hostname is False
    assert connect_arg.verify_mode == ssl.CERT_NONE


def test_normalize_database_url_disables_statement_cache_for_pooler_hosts():
    _, connect_args = normalize_database_url(
        "postgresql+asyncpg://user:pass@project.pooler.supabase.com:6543/db?sslmode=require"
    )

    assert connect_args["statement_cache_size"] == 0


def test_should_disable_statement_cache_for_common_pgbouncer_ports():
    pooler_url = make_url("postgresql+asyncpg://user:pass@host:6432/db")
    regular_url = make_url("postgresql+asyncpg://user:pass@host:5432/db")

    assert should_disable_statement_cache(pooler_url) is True
    assert should_disable_statement_cache(regular_url) is False
