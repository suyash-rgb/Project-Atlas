"""
Relational Database Session Management for Project Atlas.
Supports high-performance SQLite (default) and enterprise MySQL with role-based access.
"""

import logging
import os
import socket
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.config import settings

logger = logging.getLogger("project_atlas.database")

_DB_HOST_RESOLVABLE: Optional[bool] = None

SQLITE_INIT_SQL = """
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    published DATE NOT NULL,
    sector VARCHAR(128) NOT NULL,
    access VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS market_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report VARCHAR(32) NOT NULL,
    metric VARCHAR(128) NOT NULL,
    region VARCHAR(64) NOT NULL,
    year_period VARCHAR(64) NOT NULL,
    value VARCHAR(64) NOT NULL,
    scope_note TEXT,
    FOREIGN KEY (report) REFERENCES reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR(32) PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    purchased_reports TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id VARCHAR(32) NOT NULL,
    question TEXT NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id VARCHAR(32) NOT NULL,
    message_id VARCHAR(128) NOT NULL,
    rating VARCHAR(16) NOT NULL,
    query TEXT,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) NOT NULL,
    client_id VARCHAR(32) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    escalated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO reports (id, title, publisher, published, sector, access) VALUES
('R-101', 'Global Smart Water Meter Market 2025', 'CMR', '2025-03-10', 'Utilities', 'paid'),
('R-102', 'Smart Water Metering: Industry Outlook 2024', 'Aquila Insights (third party)', '2024-06-18', 'Utilities', 'public excerpt'),
('R-103', 'Residential Water Purifier Market 2025', 'CMR', '2025-01-22', 'Consumer Durables', 'paid'),
('R-104', 'Commercial & Industrial RO Membrane Systems 2025', 'CMR', '2025-02-14', 'Industrial Equipment', 'paid'),
('R-105', 'Smart Multi-Utility Metering Infrastructure 2024', 'Apex Grid Insights (third party)', '2024-08-05', 'Utilities', 'paid'),
('R-106', 'Decentralized Wastewater Recycling Systems 2025', 'CMR', '2025-02-28', 'Cleantech', 'paid');

INSERT OR IGNORE INTO market_metrics (id, report, metric, region, year_period, value, scope_note) VALUES
(1, 'R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
(2, 'R-101', 'CAGR', 'Global', '2025-2030', '11.2 %', 'Forecast period stated as 2025-2030'),
(3, 'R-101', 'Regional share', 'APAC', '2024', '38 %', 'Share of global market size'),
(4, 'R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR / AMI hardware only'),
(5, 'R-102', 'CAGR', 'Global', '2024-2029', '9.8 %', 'Different forecast window from R-101'),
(6, 'R-102', 'Regional share', 'APAC', '2024', '41 %', 'Share of hardware market'),
(7, 'R-103', 'Market size', 'Global', '2024', 'USD 9.85 B', 'Point-of-use residential filtration systems'),
(8, 'R-103', 'CAGR', 'Global', '2025-2030', '8.9 %', 'Forecast period 2025-2030'),
(9, 'R-103', 'Regional share', 'APAC', '2024', '48 %', 'Largest regional consumer market'),
(10, 'R-104', 'Market size', 'Global', '2024', 'USD 14.20 B', 'High-capacity industrial RO and membrane separation'),
(11, 'R-104', 'CAGR', 'Global', '2024-2030', '7.4 %', 'Forecast period 2024-2030'),
(12, 'R-104', 'Regional share', 'North America', '2024', '36 %', 'Pharma and energy sector capex dominance'),
(13, 'R-105', 'Market size', 'Global', '2024', 'USD 11.50 B', 'Combined electric, water, and gas AMI systems'),
(14, 'R-105', 'CAGR', 'Global', '2024-2029', '10.1 %', '5-year multi-utility outlook'),
(15, 'R-105', 'Regional share', 'Europe', '2024', '35 %', 'Mandated multi-commodity smart grid rollouts'),
(16, 'R-106', 'Market size', 'Global', '2024', 'USD 7.60 B', 'Modular MBR/MBBR packaged wastewater plants'),
(17, 'R-106', 'CAGR', 'Global', '2025-2030', '12.5 %', 'Highest growth segment in water cleantech'),
(18, 'R-106', 'Regional share', 'APAC', '2024', '44 %', 'Municipal effluent reuse mandates');

INSERT OR IGNORE INTO clients (id, company, contact_email, purchased_reports) VALUES
('C-01', 'Northwind Utilities', 'ops@northwind.example.com', 'R-101, R-103'),
('C-02', 'Blue Delta Infra', 'procurement@bluedelta.example.com', 'R-103'),
('C-03', 'AquaTech Industrial Corp', 'research@aquatech.example.com', 'R-104, R-106'),
('C-04', 'City of Austin Water Utility', 'ami-lead@austin.gov.example.com', 'R-101'),
('C-05', 'Global Grid Analytics', 'subs@globalgrid.example.com', 'R-105'),
('C-06', 'Public Tier Evaluation', 'visitor@cmr-trial.example.com', '');

CREATE TABLE IF NOT EXISTS client_accounts (
    client_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO client_accounts (client_id, email, password_hash) VALUES
('C-01', 'ops@northwind.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02'),
('C-02', 'procurement@bluedelta.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02'),
('C-03', 'research@aquatech.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02'),
('C-04', 'ami-lead@austin.gov.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02'),
('C-05', 'subs@globalgrid.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02'),
('C-06', 'visitor@cmr-trial.example.com', '$2y$10$TRZw8Pwu5nZ7lB8eg7GVh.dLEgxkHCiVfUHszO3Zoz3ZknTC6az02');
"""


def _initialize_sqlite_db(db_path: str):
    """Seed the SQLite database with the reference catalog and metrics."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SQLITE_INIT_SQL)
        conn.commit()
        logger.info("sqlite_db_initialized path=%s", db_path)
    finally:
        conn.close()


class SQLiteCursorWrapper:
    """Wrapper around sqlite3.Cursor providing compatibility with MySQL driver expectations."""

    def __init__(self, cursor: sqlite3.Cursor, dictionary: bool = False):
        self._cursor = cursor
        self.dictionary = dictionary

    @property
    def column_names(self) -> List[str]:
        if self._cursor.description:
            return [d[0] for d in self._cursor.description]
        return []

    @property
    def lastrowid(self) -> Optional[int]:
        return self._cursor.lastrowid

    def execute(self, query: str, params: Optional[Union[Tuple, List, Dict]] = None):
        clean_q = query.strip()
        # Ignore MySQL-specific session variables or optimizer comments
        if clean_q.upper().startswith("SET SESSION") or clean_q.upper().startswith("SET @@"):
            return self

        # Automatically translate MySQL %s placeholders to SQLite ?
        if params is not None and "%s" in query:
            query = query.replace("%s", "?")

        if params is not None:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        return self

    def fetchone(self) -> Any:
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self.dictionary:
            return dict(row)
        return row

    def fetchall(self) -> List[Any]:
        rows = self._cursor.fetchall()
        if self.dictionary:
            return [dict(r) for r in rows]
        return rows

    def fetchmany(self, size: Optional[int] = None) -> List[Any]:
        if size is None:
            rows = self._cursor.fetchall()
        else:
            rows = self._cursor.fetchmany(size)
        if self.dictionary:
            return [dict(r) for r in rows]
        return rows

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass


class SQLiteConnectionWrapper:
    """Wrapper around sqlite3.Connection providing transaction and cursor compatibility."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def cursor(self, dictionary: bool = False, **kwargs) -> SQLiteCursorWrapper:
        cur = self._conn.cursor()
        return SQLiteCursorWrapper(cur, dictionary=dictionary)

    def start_transaction(self):
        pass  # SQLite automatically begins transactions on DML statements

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def set_progress_handler(self, handler, instruction_interval: int):
        self._conn.set_progress_handler(handler, instruction_interval)

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def _resolve_host(host: str) -> str:
    global _DB_HOST_RESOLVABLE
    if host != "db":
        return host
    if _DB_HOST_RESOLVABLE is False:
        return "127.0.0.1"
    if _DB_HOST_RESOLVABLE is True:
        return "db"
    try:
        socket.gethostbyname("db")
        _DB_HOST_RESOLVABLE = True
        return "db"
    except Exception:
        _DB_HOST_RESOLVABLE = False
        return "127.0.0.1"


def _get_mysql_connection(*, readonly: bool = False):
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

    target_host = _resolve_host(settings.MYSQL_HOST)
    started_at = time.perf_counter()
    try:
        connection = mysql.connector.connect(
            host=target_host,
            port=settings.MYSQL_PORT,
            database=settings.MYSQL_DATABASE,
            user=username,
            password=password,
            autocommit=False,
            connection_timeout=2,
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


def get_db_connection(*, readonly: bool = False):
    """
    Open a transaction-capable database connection with the requested role.
    Defaults to SQLite for self-contained, offline-first operation.
    Supports MySQL when DB_TYPE is set to 'mysql'.
    """
    if getattr(settings, "DB_TYPE", "sqlite").lower() == "mysql":
        return _get_mysql_connection(readonly=readonly)

    # SQLite connection
    db_path = getattr(settings, "SQLITE_DB_PATH", None) or os.path.join("data", "atlas.db")
    abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    if not os.path.exists(abs_path):
        _initialize_sqlite_db(abs_path)

    started_at = time.perf_counter()
    try:
        if readonly:
            # Enforce database engine-level read-only mode in SQLite via URI
            uri_path = f"file:{abs_path}?mode=ro"
            raw_conn = sqlite3.connect(uri_path, uri=True, timeout=5.0, check_same_thread=False)
            role = "read-only"
        else:
            raw_conn = sqlite3.connect(abs_path, timeout=10.0, check_same_thread=False)
            role = "read-write"
    except Exception:
        logger.exception("sqlite_connection_failed path=%s readonly=%s", abs_path, readonly)
        raise

    logger.info(
        "database_connection_opened engine=sqlite role=%s duration_ms=%.1f",
        role,
        (time.perf_counter() - started_at) * 1000,
    )
    return SQLiteConnectionWrapper(raw_conn)


def upsert_report_metadata(
    report_id: str,
    title: str,
    publisher: str,
    published_date: str,
    sector: str,
    access_tier: str,
) -> None:
    """Persist report metadata without granting client entitlements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM reports WHERE id = %s", (report_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE reports SET title = %s, publisher = %s, published = %s, "
                "sector = %s, access = %s WHERE id = %s",
                (title, publisher, published_date, sector, access_tier, report_id),
            )
        else:
            cursor.execute(
                "INSERT INTO reports (id, title, publisher, published, sector, access) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (report_id, title, publisher, published_date, sector, access_tier),
            )
        conn.commit()
        logger.info("report_metadata_persisted report_id=%s", report_id)
    except Exception:
        conn.rollback()
        logger.exception("report_metadata_persist_failed report_id=%s", report_id)
        raise
    finally:
        cursor.close()
        conn.close()
