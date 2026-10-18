import pytest

from app.agent.tools import sql_tool


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)
        self.closed = False
        self.cursor_options = None

    def cursor(self, **kwargs):
        self.cursor_options = kwargs
        return self.fake_cursor

    def close(self):
        self.closed = True


def test_validate_read_only_ast_accepts_select_and_trailing_semicolon():
    expression = sql_tool.validate_read_only_ast(" SELECT id FROM reports; ")
    assert expression is not None


@pytest.mark.parametrize(
    "query",
    [
        "",
        "DELETE FROM reports",
        "SELECT * FROM reports; DROP TABLE reports",
        "SELECT * FROM reports WHERE id IN (SELECT id FROM reports); SELECT 1",
        "PRAGMA table_info(reports)",
    ],
)
def test_validate_read_only_ast_rejects_invalid_or_mutating_sql(query):
    with pytest.raises(sql_tool.SQLSecurityError):
        sql_tool.validate_read_only_ast(query)


def test_execute_safe_sql_uses_readonly_role_and_filters_unentitled_rows(monkeypatch):
    connection = FakeConnection([
        {"report": "R-101", "metric": "CAGR", "value": "11.2%"},
        {"report": "R-104", "metric": "Market size", "value": "USD 4B"},
        {"report": "R-105", "metric": "Market size", "value": "USD 9B"},
    ])
    roles = []
    monkeypatch.setattr(
        sql_tool,
        "get_db_connection",
        lambda *, readonly=False: roles.append(readonly) or connection,
    )

    rows = sql_tool.execute_safe_sql(
        "SELECT report, metric, value FROM market_metrics",
        allowed_reports=["R-101", "R-104"],
    )

    assert roles == [True]
    assert [row["report"] for row in rows] == ["R-101", "R-104"]
    assert connection.cursor_options == {"dictionary": True}
    assert connection.fake_cursor.closed
    assert connection.closed


def test_execute_safe_sql_rejects_non_report_tables_when_scoped():
    with pytest.raises(sql_tool.SQLSecurityError, match="may only read reports"):
        sql_tool.execute_safe_sql(
            "SELECT id, contact_email FROM clients",
            allowed_reports=["R-101"],
        )


def test_execute_safe_sql_rejects_results_without_report_identity(monkeypatch):
    connection = FakeConnection([{"report_count": 3}])
    monkeypatch.setattr(sql_tool, "get_db_connection", lambda **_: connection)

    with pytest.raises(sql_tool.SQLSecurityError, match="must return a report identifier"):
        sql_tool.execute_safe_sql(
            "SELECT COUNT(*) AS report_count FROM reports",
            allowed_reports=["R-101"],
        )


def test_execute_safe_sql_rejects_write_query_without_connecting(monkeypatch):
    monkeypatch.setattr(
        sql_tool,
        "get_db_connection",
        lambda **_: pytest.fail("A rejected write query must not connect."),
    )

    with pytest.raises(sql_tool.SQLSecurityError):
        sql_tool.execute_safe_sql("DELETE FROM reports")


def test_get_client_entitlements_uses_readonly_role_and_includes_public_reports(monkeypatch):
    connection = FakeConnection([("R-101, R-103",)])
    connection.fake_cursor.fetchall = lambda: [("R-104",), ("R-101",)]
    roles = []
    monkeypatch.setattr(
        sql_tool,
        "get_db_connection",
        lambda *, readonly=False: roles.append(readonly) or connection,
    )

    assert sql_tool.get_client_entitlements("C-01") == ["R-101", "R-103", "R-104"]
    assert roles == [True]
    assert connection.closed


def test_validate_read_only_ast_rejects_limit_exceeding_max_rows():
    with pytest.raises(sql_tool.SQLSecurityError, match="exceeds maximum allowed limit"):
        sql_tool.validate_read_only_ast("SELECT * FROM reports LIMIT 500")


def test_validate_read_only_ast_injects_default_limit():
    expression = sql_tool.validate_read_only_ast("SELECT * FROM reports")
    sql = expression.sql("mysql")
    assert f"LIMIT {sql_tool.MAX_QUERY_ROWS}" in sql


def test_execute_safe_sql_truncates_to_max_rows(monkeypatch):
    many_rows = [{"report": "R-101", "val": i} for i in range(150)]
    connection = FakeConnection(many_rows)
    monkeypatch.setattr(sql_tool, "get_db_connection", lambda **_: connection)

    rows = sql_tool.execute_safe_sql(
        "SELECT report, val FROM market_metrics",
        allowed_reports=["R-101"]
    )
    assert len(rows) == sql_tool.MAX_QUERY_ROWS


def test_execute_safe_sql_timeout_raises_timeout_error(monkeypatch):
    import time
    connection = FakeConnection([])
    def slow_execute(*args, **kwargs):
        time.sleep(0.2)
    connection.fake_cursor.execute = slow_execute
    monkeypatch.setattr(sql_tool, "get_db_connection", lambda **_: connection)

    with pytest.raises(TimeoutError, match="exceeded timeout"):
        sql_tool.execute_safe_sql("SELECT report FROM reports", allowed_reports=["R-101"], timeout_seconds=0.05)

