from sqlalchemy.engine import make_url
from tcg_persistence.configuration import database_url


def test_container_database_credentials_are_not_interpreted_as_url_syntax(monkeypatch):
    monkeypatch.delenv("TCG_DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.setenv("POSTGRES_USER", "tcg")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret@with:/#%symbols")
    monkeypatch.setenv("POSTGRES_DB", "catalog")
    monkeypatch.setenv("POSTGRES_PORT", "5544")
    url = make_url(database_url())
    assert url.host == "postgres"
    assert url.port == 5544
    assert url.database == "catalog"
    assert url.password == "secret@with:/#%symbols"


def test_explicit_database_url_takes_precedence_and_sqlite_remains_the_local_default(monkeypatch):
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("TCG_DATABASE_URL", raising=False)
    assert database_url() == "sqlite:///data/catalog.db"
    monkeypatch.setenv("TCG_DATABASE_URL", "sqlite:///example.db")
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    assert database_url() == "sqlite:///example.db"
