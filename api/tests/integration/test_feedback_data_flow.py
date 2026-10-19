import sqlite3


def test_feedback_submission_persists_and_invalid_requests_do_not(
    client,
    auth_headers,
    isolated_sqlite_database,
):
    payload = {
        "client_id": "C-01",
        "message_id": "integration-message-01",
        "rating": "up",
        "comment": "The answer cited the report scope clearly.",
    }

    unauthorized = client.post("/api/v1/feedback", json=payload)
    assert unauthorized.status_code == 403

    invalid = client.post(
        "/api/v1/feedback",
        json={**payload, "rating": "maybe"},
        headers=auth_headers,
    )
    assert invalid.status_code == 400

    response = client.post("/api/v1/feedback", json=payload, headers=auth_headers)
    assert response.status_code == 201

    with sqlite3.connect(isolated_sqlite_database) as connection:
        persisted = connection.execute(
            "SELECT client_id, message_id, rating, comment "
            "FROM feedback WHERE message_id = ?",
            (payload["message_id"],),
        ).fetchone()
        feedback_count = connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

    assert persisted == (
        payload["client_id"],
        payload["message_id"],
        payload["rating"],
        payload["comment"],
    )
    assert feedback_count == 1
