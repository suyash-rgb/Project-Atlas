import pytest

from app.core.config import settings
from app.core.telemetry import telemetry
from app.db.session import get_db_connection


@pytest.fixture
def seed_report(isolated_sqlite_database):
    def add_report(report_id, access="paid"):
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO reports (id, title, publisher, published, sector, access) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    report_id,
                    "Integration Chart Report",
                    "Atlas Test Publisher",
                    "2025-06-01",
                    "Utilities",
                    access,
                ),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    return add_report


@pytest.fixture
def isolated_sqlite_database(tmp_path, monkeypatch):
    database_path = tmp_path / "project-atlas-integration.sqlite3"
    monkeypatch.setattr(settings, "DB_TYPE", "sqlite")
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(database_path))

    connection = get_db_connection()
    connection.close()
    telemetry.cache.clear()

    yield database_path

    telemetry.cache.clear()
