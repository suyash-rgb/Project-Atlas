"""AST-validated, entitlement-aware SQL access through MySQL's read-only role."""

import logging
import time
from typing import List, Dict, Any, Optional
import sqlglot
from sqlglot import exp

from app.core.config import settings
from app.core.observability import observe_with_tags
from app.db.session import get_db_connection
from app.agent.tools.utils import DATABASE_SCHEMA_DOC, DEFAULT_CLIENT_ENTITLEMENTS

logger = logging.getLogger("project_atlas.sql")

MAX_QUERY_ROWS = 100
DEFAULT_QUERY_TIMEOUT_SECONDS = 5.0

SCHEMA_DEFINITION = DATABASE_SCHEMA_DOC


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


def validate_read_only_ast(sql: str, max_rows: int = MAX_QUERY_ROWS) -> exp.Expression:
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

    # Enforce row limit
    limit_node = expression.find(exp.Limit)
    if limit_node and limit_node.expression:
        try:
            limit_val = int(str(limit_node.expression))
        except (ValueError, TypeError):
            raise SQLSecurityError("Invalid LIMIT clause.")

        if limit_val > max_rows:
            raise SQLSecurityError(
                f"Requested row limit {limit_val} exceeds maximum allowed limit of {max_rows}."
            )
    else:
        expression = expression.limit(max_rows)

    return expression


@observe_with_tags(
    name="read_only_sql",
    tags=["tool:sql", "data-access:read-only"],
)
def execute_safe_sql(
    sql: str,
    allowed_reports: Optional[List[str]] = None,
    timeout_seconds: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """
    Executes an AST-validated query through the restricted MySQL account.
    If allowed_reports is specified, verifies/filters results so unentitled paid reports
    are never returned. Enforces row limits and execution timeouts.
    """
    try:
        expression = validate_read_only_ast(sql)
    except SQLSecurityError as exc:
        logger.warning("read_only_query_rejected error_type=%s", type(exc).__name__)
        raise

    queried_tables = {table.name.lower() for table in expression.find_all(exp.Table)}
    if allowed_reports is not None:
        if not queried_tables or not queried_tables.issubset({"reports", "market_metrics"}):
            raise SQLSecurityError(
                "Entitlement-scoped queries may only read reports or market_metrics."
            )

    conn = get_db_connection(readonly=True)
    cursor = conn.cursor(dictionary=True)

    dialect = "sqlite" if getattr(settings, "DB_TYPE", "sqlite").lower() == "sqlite" else "mysql"
    sanitized_sql = expression.sql(dialect)
    started_at = time.perf_counter()
    deadline = time.monotonic() + timeout_seconds
    sqlite_timeout_enabled = False
    try:
        if dialect == "mysql":
            try:
                cursor.execute(f"SET SESSION max_execution_time = {int(timeout_seconds * 1000)}")
            except Exception as exc:
                logger.exception("read_only_query_timeout_setup_failed engine=mysql")
                raise RuntimeError("Could not configure the MySQL query timeout.") from exc
        else:
            conn.set_progress_handler(
                lambda: int(time.monotonic() >= deadline),
                1000,
            )
            sqlite_timeout_enabled = True

        try:
            cursor.execute(sanitized_sql)
            if hasattr(cursor, "fetchmany"):
                rows = cursor.fetchmany(MAX_QUERY_ROWS)
            else:
                rows = cursor.fetchall()[:MAX_QUERY_ROWS]
        except Exception as exc:
            if dialect == "sqlite" and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"SQL query execution exceeded timeout of {timeout_seconds}s."
                ) from exc
            raise

        if dialect == "sqlite" and time.monotonic() >= deadline:
            raise TimeoutError(
                f"SQL query execution exceeded timeout of {timeout_seconds}s."
            )
        results = [dict(row) for row in rows]
    except Exception as exc:
        logger.exception(
            "read_only_query_failed error_type=%s table_count=%s",
            type(exc).__name__,
            len(queried_tables) if queried_tables else 0,
        )
        raise
    finally:
        if sqlite_timeout_enabled:
            conn.set_progress_handler(None, 0)
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
            report_ref = r.get("report") or r.get("id") or r.get("report_id")
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
    try:
        conn = get_db_connection(readonly=True)
    except Exception as exc:
        logger.warning(
            "entitlement_lookup_fallback reason=connection_failed client_id=%s error_type=%s",
            client_id,
            type(exc).__name__,
        )
        return list(DEFAULT_CLIENT_ENTITLEMENTS.get(client_id, ["R-102", "R-105"]))

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT purchased_reports FROM clients WHERE id = %s", (client_id,))
        row = cursor.fetchone()
        purchased = []
        if row:
            raw_reports = row.get("purchased_reports") if isinstance(row, dict) else row[0]
            if raw_reports:
                purchased = [p.strip() for p in str(raw_reports).split(",") if p.strip()]

        # Public reports are always accessible
        cursor.execute("SELECT id FROM reports WHERE access LIKE %s", ("%public%",))
        public_rows = cursor.fetchall()
        for pr in public_rows:
            raw_id = pr.get("id") if isinstance(pr, dict) else pr[0]
            report_id = str(raw_id) if raw_id is not None else None
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
        return list(DEFAULT_CLIENT_ENTITLEMENTS.get(client_id, ["R-102", "R-105"]))
    finally:
        cursor.close()
        conn.close()

