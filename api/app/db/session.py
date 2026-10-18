import os
import sqlite3
from typing import Generator
from app.core.config import settings

# Canonical absolute path to SQLite database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../project_atlas.db"))


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    Configures row_factory for dict-like access.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
