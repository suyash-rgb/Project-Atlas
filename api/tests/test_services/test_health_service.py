from importlib import import_module
from unittest.mock import Mock

from app.schemas.chat import HealthResponse
from app.services.health_service import HealthService

health_module = import_module("app.services.health_service")


def test_health_checks_mysql_using_readonly_role(monkeypatch):
    connection = Mock()
    connection.cursor.return_value.fetchone.return_value = (1,)
    retriever = Mock()
    retriever._collection.count.return_value = 12
    roles = []
    monkeypatch.setattr(
        health_module,
        "get_db_connection",
        lambda *, readonly=False: roles.append(readonly) or connection,
    )
    monkeypatch.setattr(health_module, "get_retriever", lambda: retriever)

    health = HealthService().check_health()

    assert isinstance(health, HealthResponse)
    assert health.status == "healthy"
    assert health.database == "connected"
    assert health.vector_store == "ready (12 chunks indexed)"
    assert roles == [True]
    connection.cursor.return_value.execute.assert_called_once_with("SELECT 1")
    connection.cursor.return_value.close.assert_called_once()
    connection.close.assert_called_once()


def test_health_reports_database_unavailable(monkeypatch):
    monkeypatch.setattr(
        health_module,
        "get_db_connection",
        lambda **_: raise_connection_error(),
    )
    retriever = Mock()
    retriever._collection.count.return_value = 1
    monkeypatch.setattr(health_module, "get_retriever", lambda: retriever)

    health = HealthService().check_health()

    assert health.status == "degraded"
    assert health.database == "unavailable"


def raise_connection_error():
    raise ConnectionError("MySQL unavailable")


def test_health_degrades_when_vector_store_fails(monkeypatch):
    connection = Mock()
    connection.cursor.return_value.fetchone.return_value = (1,)
    monkeypatch.setattr(
        health_module,
        "get_db_connection",
        lambda **_: connection,
    )
    monkeypatch.setattr(
        health_module,
        "get_retriever",
        Mock(side_effect=RuntimeError("ChromaDB connection refused")),
    )

    health = HealthService().check_health()

    assert health.status == "degraded"
    assert health.database == "connected"
    assert "error" in health.vector_store
