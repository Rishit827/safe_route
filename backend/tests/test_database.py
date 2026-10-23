from app.database import normalize_database_url

def test_postgres_legacy_url():
    assert normalize_database_url("postgres://u:p@host/db") == "postgresql+psycopg2://u:p@host/db"

def test_postgresql_url():
    assert normalize_database_url("postgresql://u:p@host/db") == "postgresql+psycopg2://u:p@host/db"

def test_sqlite_unchanged():
    assert normalize_database_url("sqlite:///./saferoute.db") == "sqlite:///./saferoute.db"
