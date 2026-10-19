import logging
from typing import List, Dict, Any, Optional, cast
from app.db.session import get_db_connection

logger = logging.getLogger("project_atlas.client_service")


def _row_to_dict(row: Any, cursor: Any = None) -> Dict[str, Any]:
    """Safely converts DB row to a dictionary avoiding type checker overload mismatch."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {str(k): row[k] for k in row.keys()}
    if cursor and hasattr(cursor, "description") and cursor.description:
        cols = [col[0] for col in cursor.description]
        return dict(zip(cols, row))
    return dict(cast(Any, row))


class ClientService:
    """
    Business logic layer for corporate client directory and report entitlement lookups.
    Enforces strict access filtering ensuring clients only view their licensed reports
    and authorized public excerpts.
    """

    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Retrieves list of all registered corporate clients."""
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, company, contact_email FROM clients ORDER BY id ASC")
            rows = cursor.fetchall()
            return [_row_to_dict(r, cursor) for r in rows]
        except Exception as exc:
            logger.exception("get_all_clients_query_failed error=%s", exc)
            raise
        finally:
            cursor.close()
            conn.close()

    def get_client_entitled_reports(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves company profile and accessible reports for a given client_id.
        Returns None if client does not exist.
        """
        if not client_id or not client_id.strip():
            raise ValueError("client_id is required")

        cid = client_id.strip().upper()
        conn = get_db_connection(readonly=True)
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Fetch client record
            cursor.execute("SELECT id, company, purchased_reports FROM clients WHERE id = %s", (cid,))
            client_row = cursor.fetchone()
            if not client_row:
                return None

            client_dict = _row_to_dict(client_row, cursor)
            raw_purchased = client_dict.get("purchased_reports") or ""
            purchased_ids = [p.strip() for p in str(raw_purchased).split(",") if p.strip()]

            # 2. Fetch all published reports from catalog
            cursor.execute("SELECT id, title, publisher, published, sector, access FROM reports ORDER BY id ASC")
            all_reports = [_row_to_dict(r, cursor) for r in cursor.fetchall()]

            # 3. Filter strictly: licensed/purchased reports + public excerpts
            accessible_reports = []
            for r in all_reports:
                rid = r["id"]
                access_tier = str(r.get("access", "")).lower()
                is_purchased = rid in purchased_ids
                is_public = "public" in access_tier

                if is_purchased or is_public:
                    accessible_reports.append({
                        "id": rid,
                        "title": r.get("title", ""),
                        "publisher": r.get("publisher", ""),
                        "published": str(r.get("published", "")),
                        "sector": r.get("sector", ""),
                        "access": r.get("access", ""),
                        "entitlement_type": "Full Turnkey (Purchased)" if is_purchased else "Public Excerpt",
                        "licensed": is_purchased or is_public,
                        "is_purchased": is_purchased,
                    })

            logger.info(
                "client_entitlements_resolved client_id=%s purchased_count=%d total_accessible=%d",
                cid,
                len(purchased_ids),
                len(accessible_reports),
            )

            return {
                "client_id": cid,
                "company": client_dict.get("company", ""),
                "accessible_count": len(accessible_reports),
                "reports": accessible_reports,
            }
        except Exception as exc:
            logger.exception("get_client_entitled_reports_failed client_id=%s error=%s", cid, exc)
            raise
        finally:
            cursor.close()
            conn.close()


client_service = ClientService()
