from unittest.mock import Mock

import pytest

from app.core.config import settings
from app.db import session


@pytest.mark.parametrize(
    ("readonly", "user_attr", "password_attr", "expected_user", "expected_password"),
    [
        (False, "MYSQL_USER", "MYSQL_PASSWORD", "atlas_rw", "rw-secret"),
        (
            True,
            "MYSQL_READONLY_USER",
            "MYSQL_READONLY_PASSWORD",
            "atlas_ro",
            "ro-secret",
        ),
    ],
)
def test_connection_uses_requested_database_role(
    monkeypatch,
    readonly,
    user_attr,
    password_attr,
    expected_user,
    expected_password,
):
    monkeypatch.setattr(settings, "DB_TYPE", "mysql")
    monkeypatch.setattr(settings, user_attr, expected_user)
    monkeypatch.setattr(settings, password_attr, expected_password)
    connect = Mock(return_value=object())
    monkeypatch.setattr(session.mysql.connector, "connect", connect)

    result = session.get_db_connection(readonly=readonly)

    assert result is connect.return_value
    assert connect.call_args.kwargs["user"] == expected_user
    assert connect.call_args.kwargs["password"] == expected_password
    assert connect.call_args.kwargs["autocommit"] is False
    assert connect.call_args.kwargs["database"] == settings.MYSQL_DATABASE


@pytest.mark.parametrize(
    ("readonly", "user_attr", "password_attr"),
    [
        (False, "MYSQL_USER", "MYSQL_PASSWORD"),
        (True, "MYSQL_READONLY_USER", "MYSQL_READONLY_PASSWORD"),
    ],
)
def test_connection_fails_explicitly_when_role_credentials_are_missing(
    monkeypatch, readonly, user_attr, password_attr
):
    monkeypatch.setattr(settings, "DB_TYPE", "mysql")
    monkeypatch.setattr(settings, user_attr, None)
    monkeypatch.setattr(settings, password_attr, None)
    connect = Mock()
    monkeypatch.setattr(session.mysql.connector, "connect", connect)

    with pytest.raises(RuntimeError, match="credentials are not configured"):
        session.get_db_connection(readonly=readonly)

    connect.assert_not_called()


def test_sqlite_connection_read_write(tmp_path, monkeypatch):
    import sqlite3
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "DB_TYPE", "sqlite")
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", db_file)

    conn = session.get_db_connection(readonly=False)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT count(*) AS cnt FROM reports")
    row = cursor.fetchone()
    assert row["cnt"] == 6
    cursor.close()
    conn.close()


def test_sqlite_connection_read_only_blocks_mutations(tmp_path, monkeypatch):
    import sqlite3
    db_file = str(tmp_path / "test_ro.db")
    monkeypatch.setattr(settings, "DB_TYPE", "sqlite")
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", db_file)

    # Initialize by opening read-write once
    init_conn = session.get_db_connection(readonly=False)
    init_conn.close()

    # Open in read-only mode
    ro_conn = session.get_db_connection(readonly=True)
    cur = ro_conn.cursor()
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        cur.execute("INSERT INTO reports (id, title, publisher, published, sector, access) VALUES ('R-999', 'T', 'P', '2025-01-01', 'S', 'paid')")
    cur.close()
    ro_conn.close()

