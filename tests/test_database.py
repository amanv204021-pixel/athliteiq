from app.database import _normalize_database_url


def test_database_url_normalizes_render_postgres_schemes():
    assert _normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )
    assert _normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_database_url_preserves_sqlite_scheme():
    url = "sqlite:///./sports_talent.db"
    assert _normalize_database_url(url) == url
