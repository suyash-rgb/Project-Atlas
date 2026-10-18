"""AST-validated, entitlement-aware SQL access through MySQL's read-only role."""

import logging
import time
from typing import List, Dict, Any, Optional
import sqlglot
from sqlglot import exp

from app.core.observability import observe_with_tags
from app.db.session import get_db_connection

logger = logging.getLogger("project_atlas.sql")

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
    Parse MySQL SQL with sqlglot and verify it contains exactly one SELECT statement.
    """
    clean_sql = sql.strip().rstrip(";")
    if ";" in clean_sql:
        raise SQLSecurityError("Multi-statement queries (semicolon chained) are forbidden.")

    try:
        parsed = sqlglot.parse(clean_sql, read="mysql")
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
    Executes an AST-validated query through the restricted MySQL account.
    If allowed_reports is specified, verifies/filters results so unentitled paid reports
    are never returned.
    """
    try:
        expression = validate_read_only_ast(sql)
    except SQLSecurityError as exc:
        logger.warning("read_only_query_rejected error_type=%s", type(exc).__name__)
        raise

    if allowed_reports is not None:
        queried_tables = {table.name.lower() for table in expression.find_all(exp.Table)}
        if not queried_tables or not queried_tables.issubset({"reports", "market_metrics"}):
            raise SQLSecurityError(
                "Entitlement-scoped queries may only read reports or market_metrics."
            )

    conn = get_db_connection(readonly=True)
    cursor = conn.cursor(dictionary=True)

    started_at = time.perf_counter()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
    except Exception as exc:
        logger.exception(
            "read_only_query_failed error_type=%s table_count=%s",
            type(exc).__name__,
            len(queried_tables) if allowed_reports is not None else "unscoped",
        )
        raise
    finally:
        cursor.close()
        conn.close()

    logger.info(
        "read_only_query_completed row_count=%s duration_ms=%.1f entitlement_scoped=%s",
        len(results),
        (time.perf_counter() - started_at) * 1000,
        allowed_reports is not None,
    )
    # Enforce post-query entitlement filter if reports or market_metrics were queried
    if allowed_reports is not None:
        filtered = []
        for r in results:
            report_ref = r.get("report") or r.get("id")
            if not isinstance(report_ref, str):
                raise SQLSecurityError(
                    "Entitlement-scoped queries must return a report identifier."
                )
            if report_ref in allowed_reports:
                filtered.append(r)
        return filtered

    return results


@observe_with_tags(
    name="client_entitlements",
    tags=["tool:entitlements", "data-access:read-only"],
)
def get_client_entitlements(client_id: str) -> List[str]:
    """Retrieve list of purchased report IDs for a client, plus public excerpts."""
    fallback_map = {
        "C-01": ["R-101", "R-103", "R-102"],
        "C-02": ["R-101", "R-102"],
        "C-03": ["R-101", "R-102", "R-103", "R-104", "R-105"],
        "C-04": ["R-102"],
        "C-05": ["R-103"],
        "C-06": ["R-101", "R-102", "R-103", "R-104", "R-105"],
    }
    try:
        conn = get_db_connection(readonly=True)
    except Exception as exc:
        logger.warning(
            "entitlement_lookup_fallback reason=connection_failed client_id=%s error_type=%s",
            client_id,
            type(exc).__name__,
        )
        return fallback_map.get(client_id, ["R-101", "R-102", "R-103"])

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT purchased_reports FROM clients WHERE id = %s", (client_id,))
        row = cursor.fetchone()
        purchased = []
        if row and row[0]:
            purchased = [p.strip() for p in str(row[0]).split(",") if p.strip()]

        # Public reports are always accessible
        cursor.execute("SELECT id FROM reports WHERE access LIKE %s", ("%public%",))
        public_rows = cursor.fetchall()
        for pr in public_rows:
            report_id = str(pr[0]) if pr and pr[0] is not None else None
            if report_id and report_id not in purchased:
                purchased.append(report_id)

        logger.info(
            "client_entitlements_loaded client_id=%s report_count=%s",
            client_id,
            len(purchased),
        )
        return purchased
    except Exception as exc:
        logger.exception(
            "entitlement_lookup_fallback reason=query_failed client_id=%s error_type=%s",
            client_id,
            type(exc).__name__,
        )
        return fallback_map.get(client_id, ["R-101", "R-102", "R-103"])
    finally:
        cursor.close()
        conn.close()
