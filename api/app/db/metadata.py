"""
Authoritative Report Metadata & Access Registry.

Extracts DB operations for report metadata and public tier access away from
vector retriever tools to maintain clean Single Responsibility.
"""

import hashlib
import logging
from typing import Dict, Any, List
from app.db.session import get_db_connection

logger = logging.getLogger("project_atlas.db.metadata")

_RUNTIME_REPORT_REGISTRY: Dict[str, Dict[str, Any]] = {}


def stable_document_id(report_id: str, page: int, text: str, kind: str = "text") -> str:
    """Computes a deterministic hash identifier for an ingested chunk."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
    return f"{report_id}_{page}_{kind}_{digest}"


def register_runtime_report(report_id: str, metadata: Dict[str, Any]) -> None:
    """Store dynamically ingested report metadata in memory."""
    _RUNTIME_REPORT_REGISTRY[report_id] = metadata


def fetch_report_metadata(report_id: str) -> Dict[str, Any]:
    """Fetch authoritative report metadata directly from the database 'reports' table."""
    if report_id in _RUNTIME_REPORT_REGISTRY:
        return dict(_RUNTIME_REPORT_REGISTRY[report_id])

    try:
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, title, publisher, published, sector, access FROM reports WHERE id = %s",
                (report_id,)
            )
            row = cursor.fetchone()
            if row:
                row_dict = dict(row) if isinstance(row, dict) else {
                    "id": row[0], "title": row[1], "publisher": row[2],
                    "published": row[3], "sector": row[4], "access": row[5]
                }
                pub_date = str(row_dict.get("published", ""))
                year_val = int(pub_date[:4]) if len(pub_date) >= 4 and pub_date[:4].isdigit() else 2024
                return {
                    "title": str(row_dict.get("title") or report_id),
                    "publisher": str(row_dict.get("publisher") or "Unknown"),
                    "sector": str(row_dict.get("sector") or "General"),
                    "published": pub_date,
                    "year": year_val,
                    "access": str(row_dict.get("access") or "paid"),
                }
        finally:
            cursor.close()
            conn.close()
    except Exception as exc:
        logger.warning("db_metadata_lookup_failed report_id=%s error=%s", report_id, exc)

    return {
        "title": report_id,
        "publisher": "Unknown",
        "sector": "General",
        "published": "2024-01-01",
        "year": 2024,
        "access": "paid",
    }


def get_public_report_ids() -> List[str]:
    """Retrieve public report IDs directly from the database 'reports' table."""
    try:
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM reports WHERE access LIKE %s", ("%public%",))
            rows = cursor.fetchall()
            return [
                str(r.get("id") if isinstance(r, dict) else r[0])
                for r in rows
                if (r.get("id") if isinstance(r, dict) else r[0]) is not None
            ]
        finally:
            cursor.close()
            conn.close()
    except Exception as exc:
        logger.warning("db_public_reports_lookup_failed error=%s", exc)
        return []
