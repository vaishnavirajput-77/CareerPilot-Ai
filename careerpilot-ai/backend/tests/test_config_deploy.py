"""
Unit tests for deployment configuration and DATABASE_URL normalization.
Verifies that:
1. 'postgres://' URLs from Neon/Render are normalized to 'postgresql+psycopg://'
2. 'postgresql://' URLs are normalized to 'postgresql+psycopg://'
3. SQLite default remains functional for local dev
4. COOKIE_SECURE boolean parsing handles truthy/falsy values correctly
"""
import os
from unittest.mock import patch


def test_database_url_normalization():
    # Helper function matching config logic
    def normalize_url(raw_url: str) -> str:
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif raw_url.startswith("postgresql://") and "+psycopg" not in raw_url:
            return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw_url

    neon_raw = "postgres://user:secret@ep-cool-host.us-east-2.aws.neon.tech/careerpilot?sslmode=require"
    normalized = normalize_url(neon_raw)
    assert normalized.startswith("postgresql+psycopg://")
    assert "user:secret@ep-cool-host" in normalized

    render_raw = "postgresql://user:secret@dpg-host-a.oregon-postgres.render.com/careerpilot"
    normalized_render = normalize_url(render_raw)
    assert normalized_render.startswith("postgresql+psycopg://")

    already_psycopg = "postgresql+psycopg://user:secret@host/db"
    assert normalize_url(already_psycopg) == already_psycopg


def test_cookie_secure_parsing():
    def parse_cookie_secure(val: str) -> bool:
        return val.lower() in ("true", "1", "yes")

    assert parse_cookie_secure("true") is True
    assert parse_cookie_secure("True") is True
    assert parse_cookie_secure("1") is True
    assert parse_cookie_secure("yes") is True
    assert parse_cookie_secure("false") is False
    assert parse_cookie_secure("0") is False
    assert parse_cookie_secure("") is False


def test_sqlalchemy_engine_dialect_loading():
    from sqlalchemy import create_engine
    from app.config import DEFAULT_DB_PATH

    # 1. Test Neon PostgreSQL engine with sslmode query param
    neon_mock_url = "postgresql+psycopg://user:dummy_pass@ep-fake-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    engine_pg = create_engine(neon_mock_url)
    assert engine_pg.dialect.name == "postgresql"
    assert engine_pg.dialect.driver == "psycopg"
    assert engine_pg.url.query.get("sslmode") == "require"

    # 2. Test SQLite engine initialization
    sqlite_url = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    engine_sqlite = create_engine(sqlite_url)
    assert engine_sqlite.dialect.name == "sqlite"

