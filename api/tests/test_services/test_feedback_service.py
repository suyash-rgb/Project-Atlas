from importlib import import_module
from unittest.mock import Mock

import pytest

from app.schemas.chat import FeedbackResponse
from app.services.feedback_service import FeedbackService

feedback_module = import_module("app.services.feedback_service")


def test_record_feedback_commits_to_shared_write_connection(monkeypatch):
    connection = Mock()
    cursor = connection.cursor.return_value
    monkeypatch.setattr(feedback_module, "get_db_connection", lambda: connection)

    result = FeedbackService().record_feedback(
        client_id=" C-01 ",
        rating="UP",
        message_id="msg-1",
        comment="Useful answer",
    )

    assert isinstance(result, FeedbackResponse)
    assert result.status == "success"
    connection.start_transaction.assert_called_once()
    cursor.execute.assert_called_once_with(
        "INSERT INTO feedback (client_id, message_id, rating, comment) "
        "VALUES (%s, %s, %s, %s)",
        ("C-01", "msg-1", "up", "Useful answer"),
    )
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_record_feedback_rolls_back_write_failure(monkeypatch):
    connection = Mock()
    connection.cursor.return_value.execute.side_effect = RuntimeError("write failed")
    monkeypatch.setattr(feedback_module, "get_db_connection", lambda: connection)

    with pytest.raises(RuntimeError, match="Failed to persist feedback") as error:
        FeedbackService().record_feedback(client_id="C-01", rating="up")

    assert isinstance(error.value.__cause__, RuntimeError)
    connection.start_transaction.assert_called_once()
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    connection.cursor.return_value.close.assert_called_once()
    connection.close.assert_called_once()


def test_empty_client_id_raises_value_error():
    with pytest.raises(ValueError, match="client_id is required"):
        FeedbackService().record_feedback(client_id="", rating="up")


def test_invalid_rating_raises_value_error():
    with pytest.raises(ValueError, match="Invalid rating 'neutral'"):
        FeedbackService().record_feedback(client_id="C-01", rating="neutral")
