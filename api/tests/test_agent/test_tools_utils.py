"""
Unit tests for agent tools shared utilities, canonical catalogs, and dynamic resolvers.
"""

import pytest
from app.agent.tools.utils import (
    DATABASE_SCHEMA_DOC,
    DEFAULT_CLIENT_ENTITLEMENTS,
    DEFAULT_REPORT_METADATA,
    _row_to_dict,
    fetch_all_reports_metadata,
    fetch_report_metadata,
    get_public_report_ids,
    register_runtime_report,
)


def test_database_schema_doc_contains_key_tables():
    """Verify that schema documentation defines reports, market_metrics, and clients."""
    assert "reports (" in DATABASE_SCHEMA_DOC
    assert "market_metrics (" in DATABASE_SCHEMA_DOC
    assert "clients (" in DATABASE_SCHEMA_DOC


def test_default_client_entitlements_mappings():
    """Verify standard default entitlements for test clients."""
    assert "R-101" in DEFAULT_CLIENT_ENTITLEMENTS["C-01"]
    assert "R-103" in DEFAULT_CLIENT_ENTITLEMENTS["C-02"]
    assert "R-104" in DEFAULT_CLIENT_ENTITLEMENTS["C-03"]
    assert "R-101" in DEFAULT_CLIENT_ENTITLEMENTS["C-04"]
    assert "R-105" in DEFAULT_CLIENT_ENTITLEMENTS["C-05"]
    assert DEFAULT_CLIENT_ENTITLEMENTS["C-06"] == ["R-102", "R-105"]


def test_row_to_dict_conversion():
    """Verify _row_to_dict helper handles dict, tuple, list, and None."""
    assert _row_to_dict(None) == {}
    assert _row_to_dict({"a": 1, "b": 2}) == {"a": 1, "b": 2}
    assert _row_to_dict(("val1", "val2"), keys=["k1", "k2"]) == {"k1": "val1", "k2": "val2"}
    assert _row_to_dict(["val1", "val2"], keys=["k1", "k2"]) == {"k1": "val1", "k2": "val2"}


def test_fetch_report_metadata_fallback():
    """Verify fallback metadata retrieval for known and unknown reports."""
    r101 = fetch_report_metadata("R-101")
    assert r101["title"] == "Global Smart Water Meter Market 2025"
    assert r101["access"] == "paid"
    assert r101["sector"] == "Utilities"

    unknown = fetch_report_metadata("R-UNKNOWN")
    assert unknown["title"] == "R-UNKNOWN"
    assert unknown["publisher"] == "Unknown"


def test_register_runtime_report_priority():
    """Verify runtime registered reports take precedence in metadata resolution."""
    custom_meta = {
        "title": "Custom Hydrogen Grid Report",
        "publisher": "CleanGrid Institute",
        "sector": "Energy",
        "published": "2026-01-15",
        "year": 2026,
        "access": "paid",
        "coverage": "Green hydrogen pipeline infrastructure",
    }
    register_runtime_report("R-901", custom_meta)

    resolved = fetch_report_metadata("R-901")
    assert resolved["title"] == "Custom Hydrogen Grid Report"
    assert resolved["publisher"] == "CleanGrid Institute"
    assert resolved["year"] == 2026

    all_reports = fetch_all_reports_metadata()
    assert "R-901" in all_reports
    assert all_reports["R-901"]["sector"] == "Energy"


def test_get_public_report_ids():
    """Verify that get_public_report_ids includes R-102 and R-105."""
    public_ids = get_public_report_ids()
    assert "R-102" in public_ids
    assert "R-105" in public_ids
    assert "R-101" not in public_ids
    assert "R-103" not in public_ids
