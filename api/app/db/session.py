import logging
import time

import mysql.connector
from mysql.connector.connection import MySQLConnection
from app.core.config import settings

logger = logging.getLogger("project_atlas.database")


def get_db_connection(*, readonly: bool = False) -> MySQLConnection:
    """
    Open a transaction-capable MySQL connection with the requested DB role.
    """
    if readonly:
        username = settings.MYSQL_READONLY_USER
        password = settings.MYSQL_READONLY_PASSWORD
        role = "read-only"
    else:
        username = settings.MYSQL_USER
        password = settings.MYSQL_PASSWORD
        role = "read-write"

    if not username or not password:
        logger.error("database_connection_rejected reason=credentials_missing role=%s", role)
        raise RuntimeError(f"MySQL {role} credentials are not configured.")

    started_at = time.perf_counter()
    try:
        connection = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            database=settings.MYSQL_DATABASE,
            user=username,
            password=password,
            autocommit=False,
        )
    except Exception:
        logger.exception(
            "database_connection_failed role=%s host=%s port=%s database=%s",
            role,
            settings.MYSQL_HOST,
            settings.MYSQL_PORT,
            settings.MYSQL_DATABASE,
        )
        raise

    logger.info(
        "database_connection_opened role=%s duration_ms=%.1f",
        role,
        (time.perf_counter() - started_at) * 1000,
    )
    return connection
