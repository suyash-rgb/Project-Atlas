"""
Database Schema & Initialization for Project Atlas.
Supports both SQLite (in-memory or file) and MySQL.
Tables matching Appendix A + Operational requirements:
- reports
- market_metrics
- clients
- escalations
- feedback
"""

import sqlite3
from typing import Optional


SCHEMA_SQL = """
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
    FOREIGN KEY (report) REFERENCES reports(id)
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
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Complete 6 Reports (Appendix A + 3 Extended Sectors)
INITIAL_REPORTS = [
    ("R-101", "Global Smart Water Meter Market 2025", "CMR", "2025-03-10", "Utilities", "paid"),
    ("R-102", "Smart Water Metering: Industry Outlook 2024", "Aquila Insights (third party)", "2024-06-18", "Utilities", "public excerpt"),
    ("R-103", "Residential Water Purifier Market 2025", "CMR", "2025-01-22", "Consumer Durables", "paid"),
    ("R-104", "Commercial & Industrial RO Membrane Systems 2025", "CMR", "2025-02-14", "Industrial Equipment", "paid"),
    ("R-105", "Smart Multi-Utility Metering Infrastructure 2024", "Apex Grid Insights (third party)", "2024-08-05", "Utilities", "public excerpt"),
    ("R-106", "Decentralized Wastewater Recycling Systems 2025", "CMR", "2025-02-28", "Cleantech", "paid"),
]

INITIAL_METRICS = [
    # R-101
    ("R-101", "Market size", "Global", "2024", "USD 4.21 B", "Includes hardware, software and services"),
    ("R-101", "CAGR", "Global", "2025-2030", "11.2 %", "Forecast period stated as 2025-2030"),
    ("R-101", "Regional share", "APAC", "2024", "38 %", "Share of global market size"),
    # R-102
    ("R-102", "Market size", "Global", "2024", "USD 3.87 B", "AMR / AMI hardware only"),
    ("R-102", "CAGR", "Global", "2024-2029", "9.8 %", "Different forecast window from R-101"),
    ("R-102", "Regional share", "APAC", "2024", "41 %", "Share of hardware market"),
    # R-103
    ("R-103", "Market size", "Global", "2024", "USD 9.85 B", "Point-of-use residential filtration systems"),
    ("R-103", "CAGR", "Global", "2025-2030", "8.9 %", "Forecast period 2025-2030"),
    ("R-103", "Regional share", "APAC", "2024", "48 %", "Largest regional consumer market"),
    # R-104
    ("R-104", "Market size", "Global", "2024", "USD 14.20 B", "High-capacity industrial RO and membrane separation"),
    ("R-104", "CAGR", "Global", "2024-2030", "7.4 %", "Forecast period 2024-2030"),
    ("R-104", "Regional share", "North America", "2024", "36 %", "Pharma and energy sector capex dominance"),
    # R-105
    ("R-105", "Market size", "Global", "2024", "USD 11.50 B", "Combined electric, water, and gas AMI systems"),
    ("R-105", "CAGR", "Global", "2024-2029", "10.1 %", "5-year multi-utility outlook"),
    ("R-105", "Regional share", "Europe", "2024", "35 %", "Mandated multi-commodity smart grid rollouts"),
    # R-106
    ("R-106", "Market size", "Global", "2024", "USD 7.60 B", "Modular MBR/MBBR packaged wastewater plants"),
    ("R-106", "CAGR", "Global", "2025-2030", "12.5 %", "Highest growth segment in water cleantech"),
    ("R-106", "Regional share", "APAC", "2024", "44 %", "Municipal effluent reuse mandates"),
]

INITIAL_CLIENTS = [
    ("C-01", "Northwind Utilities", "ops@example.com", "R-101, R-103"),
    ("C-02", "Blue Delta Infra", "procurement@example.com", "R-103")
]


def init_sqlite_db(db_path: str = "project_atlas.db") -> sqlite3.Connection:
    """Initializes SQLite database with schema and full initial seed data."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    
    # Insert initial reports if not present
    cursor.executemany(
        "INSERT OR IGNORE INTO reports (id, title, publisher, published, sector, access) VALUES (?, ?, ?, ?, ?, ?)",
        INITIAL_REPORTS
    )
    
    # Insert initial metrics if not present
    for metric in INITIAL_METRICS:
        cursor.execute(
            "SELECT id FROM market_metrics WHERE report = ? AND metric = ? AND region = ? AND year_period = ?",
            (metric[0], metric[1], metric[2], metric[3])
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO market_metrics (report, metric, region, year_period, value, scope_note) VALUES (?, ?, ?, ?, ?, ?)",
                metric
            )
            
    # Insert initial clients if not present
    cursor.executemany(
        "INSERT OR IGNORE INTO clients (id, company, contact_email, purchased_reports) VALUES (?, ?, ?, ?)",
        INITIAL_CLIENTS
    )
    
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_sqlite_db("project_atlas.db")
    cur = conn.cursor()
    print("Database updated successfully with 6 reports!")
    print("\n--- Reports Catalog ---")
    for r in cur.execute("SELECT id, title, publisher, sector, access FROM reports"):
        print(f"[{r['id']}] {r['title']} | Sector: {r['sector']} | Access: {r['access']}")
    print("\n--- Total Metrics Tracked ---")
    count = cur.execute("SELECT COUNT(*) as c FROM market_metrics").fetchone()['c']
    print(f"Total metrics rows in DB: {count}")
