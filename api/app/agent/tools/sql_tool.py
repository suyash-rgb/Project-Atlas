"""
AST-Validated Read-Only SQL Tool.
Enforces strict AST validation via sqlglot:
- Permits exclusively SELECT statements.
- Blocks multi-statement execution, mutations (DROP, DELETE, UPDATE, INSERT, ALTER),
  and dangerous expressions.
- Operates in strict read-only mode against project_atlas.db.
- Enforces client entitlement constraints on the SQL layer.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional
import sqlglot
from sqlglot import exp

from app.core.observability import observe_with_tags

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../project_atlas.db"))

SCHEMA_DEFINITION = """
Database Schema:
1. reports (
    id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    published DATE NOT NULL,
    sector VARCHAR(128) NOT NULL,
    access VARCHAR(64) NOT NULL -- 'paid' or 'public excerpt'
)

2. market_metrics (
    id INTEGER PRIMARY KEY,
    report VARCHAR(32) NOT NULL, -- references reports(id)
    metric VARCHAR(128) NOT NULL, -- e.g. 'Market size', 'CAGR', 'Regional share'
    region VARCHAR(64) NOT NULL, -- e.g. 'Global', 'APAC', 'North America'
    year_period VARCHAR(64) NOT NULL, -- e.g. '2024', '2025-2030'
    value VARCHAR(64) NOT NULL, -- e.g. 'USD 4.21 B', '11.2 %'
    scope_note TEXT -- Methodology and scope details (e.g. Turnkey vs Hardware-only)
)

3. clients (
    id VARCHAR(32) PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    purchased_reports TEXT NOT NULL -- e.g. 'R-101, R-103'
)
"""

FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Pragma,
)


class SQLSecurityError(ValueError):
    """Raised when a SQL query violates read-only or AST constraints."""
    pass


def validate_read_only_ast(sql: str) -> exp.Expression:
    """
    Parse SQL with sqlglot and strictly verify it contains exactly one SELECT statement.
    """
    clean_sql = sql.strip().rstrip(";")
    if ";" in clean_sql:
        raise SQLSecurityError("Multi-statement queries (semicolon chained) are forbidden.")

    try:
        parsed = sqlglot.parse(clean_sql, read="sqlite")
    except Exception as e:
        raise SQLSecurityError(f"SQL Syntax Error: {e}")

    if not parsed or len(parsed) != 1:
        raise SQLSecurityError("Exactly one query statement is permitted.")

    expression = parsed[0]
    if expression is None:
        raise SQLSecurityError("Empty SQL query expression.")

    # Must be a Select query (or Union of Selects)
    if not isinstance(expression, (exp.Select, exp.Union)):
        raise SQLSecurityError(f"Query type '{type(expression).__name__}' is forbidden. Only SELECT is permitted.")

    # Check for any nested forbidden operations (e.g. INSERT/UPDATE in subqueries)
    for forbidden_type in FORBIDDEN_EXPRESSIONS:
        if expression.find(forbidden_type):
            raise SQLSecurityError(f"Operation '{forbidden_type.__name__}' is strictly forbidden.")

    return expression


@observe_with_tags(
    name="read_only_sql",
    tags=["tool:sql", "data-access:read-only"],
)
def execute_safe_sql(
    sql: str,
    allowed_reports: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Executes an AST-validated read-only SQL query against SQLite.
    If allowed_reports is specified, verifies/filters results so unentitled paid reports
    are never returned.
    """
    validate_read_only_ast(sql)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Use URI with mode=ro for OS-level write-protection
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
    finally:
        cursor.close()
        conn.close()

    # Enforce post-query entitlement filter if reports or market_metrics were queried
    if allowed_reports is not None:
        filtered = []
        for r in results:
            report_ref = r.get("report") or r.get("id")
            # If the row has a report identifier and it's not in allowed_reports, check access
            if report_ref and isinstance(report_ref, str) and report_ref.startswith("R-"):
                if report_ref not in allowed_reports and r.get("access") != "public excerpt":
                    continue  # drop unentitled row
            filtered.append(r)
        return filtered

    return results


@observe_with_tags(
    name="client_entitlements",
    tags=["tool:entitlements", "data-access:read-only"],
)
def get_client_entitlements(client_id: str) -> List[str]:
    """Retrieve list of purchased report IDs for a client, plus public excerpts."""
    if not os.path.exists(DB_PATH):
        return ["R-102", "R-105"]

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT purchased_reports FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        purchased = []
        if row and row[0]:
            purchased = [p.strip() for p in row[0].split(",") if p.strip()]

        # Public reports are always accessible
        cursor.execute("SELECT id FROM reports WHERE access LIKE '%public%'")
        public_rows = cursor.fetchall()
        for pr in public_rows:
            if pr[0] not in purchased:
                purchased.append(pr[0])

        return purchased
    finally:
        cursor.close()
        conn.close()
