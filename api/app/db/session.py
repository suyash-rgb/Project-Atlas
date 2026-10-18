import mysql.connector
from mysql.connector.connection import MySQLConnection
from app.core.config import settings


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
        raise RuntimeError(f"MySQL {role} credentials are not configured.")

    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        database=settings.MYSQL_DATABASE,
        user=username,
        password=password,
        autocommit=False,
    )
