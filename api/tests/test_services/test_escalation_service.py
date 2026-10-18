from datetime import datetime
from importlib import import_module
from unittest.mock import Mock

import pytest

from app.schemas.chat import EscalationItem
from app.services.escalation_service import EscalationService

escalation_module = import_module("app.services.escalation_service")


def make_connection(rows=None, lastrowid=42):
    cursor = Mock()
    cursor.fetchall.return_value = rows or []
    cursor.lastrowid = lastrowid
    connection = Mock()
    connection.cursor.return_value = cursor
    return connection, cursor


def test_log_escalation_commits_transaction_and_closes_resources(monkeypatch):
    connection, cursor = make_connection()
    monkeypatch.setattr(escalation_module, "get_db_connection", lambda: connection)

    ticket_id = EscalationService().log_escalation(
        "C-01", "Question", "Low confidence"
    )

    assert ticket_id == 42
    connection.start_transaction.assert_called_once()
    cursor.execute.assert_called_once_with(
        "INSERT INTO escalations (client_id, question, reason, status) "
        "VALUES (%s, %s, %s, %s)",
        ("C-01", "Question", "Low confidence", "pending"),
    )
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_log_escalation_rolls_back_failure(monkeypatch):
    connection, cursor = make_connection()
    cursor.execute.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(escalation_module, "get_db_connection", lambda: connection)

    with pytest.raises(RuntimeError, match="database unavailable"):
        EscalationService().log_escalation("C-01", "Question", "Reason")

    connection.rollback.assert_called_once()
    connection.start_transaction.assert_called_once()
    connection.commit.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_get_escalations_reads_rows_and_closes_resources(monkeypatch):
    connection, cursor = make_connection(
        [{
            "id": 7,
            "client_id": "C-01",
            "question": "Question",
            "reason": "Reason",
            "status": "pending",
            "created_at": datetime(2025, 1, 2, 3, 4),
        }]
    )
    monkeypatch.setattr(escalation_module, "get_db_connection", lambda: connection)

    items = EscalationService().get_all_escalations(limit=3)

    assert len(items) == 1
    assert isinstance(items[0], EscalationItem)
    assert items[0].id == 7
    assert cursor.execute.call_args.args[1] == (3,)
    assert connection.cursor.call_args.kwargs == {"dictionary": True}
    cursor.close.assert_called_once()
    connection.close.assert_called_once()
