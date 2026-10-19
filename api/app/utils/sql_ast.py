"""
SQL AST parsing, read-only validation, and injection prevention using sqlglot.
"""

import logging
from typing import Optional
import sqlglot
from sqlglot import exp

logger = logging.getLogger("project_atlas.utils.sql_ast")

MAX_QUERY_ROWS = 100

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
    Disallows chained statements, non-SELECT expressions, forbidden DDL/DML,
    and enforces maximum row limits.
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
