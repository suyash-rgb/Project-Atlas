"""
Shared utilities, canonical metadata registry, and database-backed catalog loaders
for Project Atlas agent tools.
"""

import logging
from typing import Any, Dict, List, Optional

from app.db.session import get_db_connection

logger = logging.getLogger("project_atlas.tools.utils")

# ==============================================================================
# 1. CANONICAL DATABASE SCHEMA REFERENCE
# ==============================================================================
DATABASE_SCHEMA_DOC = """
Database Schema:
1. reports (
    id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    published DATE NOT NULL,
    sector VARCHAR(128) NOT NULL,
    access VARCHAR(64) NOT NULL -- 'paid' or 'public excerpt'
);

2. market_metrics (
    id INTEGER PRIMARY KEY,
    report VARCHAR(32) NOT NULL, -- references reports(id)
    metric VARCHAR(128) NOT NULL, -- e.g. 'Market size', 'CAGR', 'Regional share'
    region VARCHAR(64) NOT NULL, -- e.g. 'Global', 'APAC', 'North America'
    year_period VARCHAR(64) NOT NULL, -- e.g. '2024', '2025-2030'
    value VARCHAR(64) NOT NULL, -- e.g. 'USD 4.21 B', '11.2 %'
    scope_note TEXT -- Methodology and scope details (e.g. Turnkey vs Hardware-only)
);

3. clients (
    id VARCHAR(32) PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    purchased_reports TEXT NOT NULL -- e.g. 'R-101, R-103'
);
"""

# ==============================================================================
# 2. CANONICAL FALLBACK DATA CATALOGS
# ==============================================================================
DEFAULT_REPORT_METADATA: Dict[str, Dict[str, Any]] = {
    "R-101": {
        "title": "Global Smart Water Meter Market 2025",
        "publisher": "CMR",
        "sector": "Utilities",
        "published": "2025-03-10",
        "year": 2025,
        "access": "paid",
        "coverage": "Turnkey solutions (hardware, AMI software, installation, maintenance)",
    },
    "R-102": {
        "title": "Smart Water Metering: Industry Outlook 2024",
        "publisher": "Aquila Insights (third party)",
        "sector": "Utilities",
        "published": "2024-06-18",
        "year": 2024,
        "access": "public excerpt",
        "coverage": "Hardware only (meter units and physical endpoints)",
    },
    "R-103": {
        "title": "Residential Water Purifier Market 2025",
        "publisher": "CMR",
        "sector": "Consumer Durables",
        "published": "2025-01-22",
        "year": 2025,
        "access": "paid",
        "coverage": "Point-of-use residential filtration systems and RO membranes",
    },
    "R-104": {
        "title": "Commercial & Industrial RO Membrane Systems 2025",
        "publisher": "CMR",
        "sector": "Industrial Equipment",
        "published": "2025-02-14",
        "year": 2025,
        "access": "paid",
        "coverage": "High-volume industrial RO and membrane separation systems",
    },
    "R-105": {
        "title": "Smart Multi-Utility Metering Infrastructure 2024",
        "publisher": "Apex Grid Insights (third party)",
        "sector": "Utilities",
        "published": "2024-08-05",
        "year": 2024,
        "access": "public excerpt",
        "coverage": "Combined electric, water, and gas AMI infrastructure",
    },
    "R-106": {
        "title": "Decentralized Wastewater Recycling Systems 2025",
        "publisher": "CMR",
        "sector": "Cleantech",
        "published": "2025-02-28",
        "year": 2025,
        "access": "paid",
        "coverage": "Modular MBR/MBBR packaged wastewater treatment plants",
    },
}

DEFAULT_CLIENT_ENTITLEMENTS: Dict[str, List[str]] = {
    "C-01": ["R-101", "R-103", "R-102", "R-105"],
    "C-02": ["R-103", "R-102", "R-105"],
    "C-03": ["R-104", "R-106", "R-102", "R-105"],
    "C-04": ["R-101", "R-102", "R-105"],
    "C-05": ["R-105", "R-102"],
    "C-06": ["R-102", "R-105"],
}

# In-memory registry for dynamically ingested reports
_DYNAMIC_REPORT_REGISTRY: Dict[str, Dict[str, Any]] = {}


# ==============================================================================
# 3. DYNAMIC METADATA LOADERS & RESOLVERS
# ==============================================================================
def register_runtime_report(report_id: str, metadata: Dict[str, Any]) -> None:
    """Register or update runtime report metadata (e.g. from /ingest API)."""
    _DYNAMIC_REPORT_REGISTRY[report_id] = metadata
    logger.info("runtime_report_registered report_id=%s", report_id)


def _row_to_dict(row: Any, keys: Optional[List[str]] = None) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    if keys and isinstance(row, (tuple, list)):
        return dict(zip(keys, row))
    return {}


def fetch_report_metadata(report_id: str) -> Dict[str, Any]:
    """
    Fetch authoritative metadata for a given report ID.
    Resolution order:
    1. Runtime dynamic registry
    2. Relational database 'reports' table
    3. Canonical fallback dictionary
    """
    if report_id in _DYNAMIC_REPORT_REGISTRY:
        return dict(_DYNAMIC_REPORT_REGISTRY[report_id])

    cols = ["id", "title", "publisher", "published", "sector", "access"]
    try:
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, title, publisher, published, sector, access FROM reports WHERE id = %s", (report_id,))
            row = cursor.fetchone()
            if row:
                row_dict = _row_to_dict(row, cols)
                pub_date = str(row_dict.get("published", ""))
                year_val = int(pub_date[:4]) if len(pub_date) >= 4 and pub_date[:4].isdigit() else 2024
                fallback = DEFAULT_REPORT_METADATA.get(report_id, {})
                return {
                    "title": row_dict.get("title") or fallback.get("title", report_id),
                    "publisher": row_dict.get("publisher") or fallback.get("publisher", "Unknown"),
                    "sector": row_dict.get("sector") or fallback.get("sector", "General"),
                    "published": pub_date or fallback.get("published", "2024-01-01"),
                    "year": year_val,
                    "access": row_dict.get("access") or fallback.get("access", "paid"),
                    "coverage": fallback.get("coverage", f"{row_dict.get('sector', 'Market')} study"),
                }
        finally:
            cursor.close()
            conn.close()
    except Exception as exc:
        logger.debug("db_metadata_lookup_failed report_id=%s reason=%s", report_id, type(exc).__name__)

    # Fallback to default catalog
    return dict(DEFAULT_REPORT_METADATA.get(report_id, {
        "title": report_id,
        "publisher": "Unknown",
        "sector": "General",
        "published": "2024-01-01",
        "year": 2024,
        "access": "paid",
        "coverage": "Market study",
    }))


def fetch_all_reports_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Fetch all report metadata, merging relational DB entries with canonical defaults
    and any runtime registrations.
    """
    catalog = {k: dict(v) for k, v in DEFAULT_REPORT_METADATA.items()}
    cols = ["id", "title", "publisher", "published", "sector", "access"]

    try:
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, title, publisher, published, sector, access FROM reports")
            rows = cursor.fetchall()
            for row in rows:
                row_dict = _row_to_dict(row, cols)
                rid = row_dict.get("id")
                if not rid:
                    continue
                pub_date = str(row_dict.get("published", ""))
                year_val = int(pub_date[:4]) if len(pub_date) >= 4 and pub_date[:4].isdigit() else 2024
                fallback = DEFAULT_REPORT_METADATA.get(rid, {})
                catalog[rid] = {
                    "title": row_dict.get("title") or fallback.get("title", rid),
                    "publisher": row_dict.get("publisher") or fallback.get("publisher", "Unknown"),
                    "sector": row_dict.get("sector") or fallback.get("sector", "General"),
                    "published": pub_date or fallback.get("published", "2024-01-01"),
                    "year": year_val,
                    "access": row_dict.get("access") or fallback.get("access", "paid"),
                    "coverage": fallback.get("coverage", f"{row_dict.get('sector', 'Market')} study"),
                }
        finally:
            cursor.close()
            conn.close()
    except Exception as exc:
        logger.debug("db_all_reports_lookup_failed reason=%s", type(exc).__name__)

    # Overlay runtime additions
    catalog.update(_DYNAMIC_REPORT_REGISTRY)
    return catalog



def get_public_report_ids() -> List[str]:
    """Retrieve list of all public report IDs."""
    all_reports = fetch_all_reports_metadata()
    return [
        rid for rid, meta in all_reports.items()
        if "public" in str(meta.get("access", "")).lower()
    ]
