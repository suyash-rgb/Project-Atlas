from app.api.v1.routers.clients import client_service


def test_client_catalog_requires_api_key(client):
    response = client.get("/api/v1/clients")

    assert response.status_code == 403


def test_client_entitlements_require_api_key(client):
    response = client.get("/api/v1/clients/C-01/reports")

    assert response.status_code == 403


def test_authenticated_client_entitlements_return_service_data(client, auth_headers, monkeypatch):
    expected = {
        "client_id": "C-01",
        "company": "Northwind Utilities",
        "accessible_count": 1,
        "reports": [{"id": "R-102", "is_purchased": False}],
    }
    monkeypatch.setattr(
        client_service,
        "get_client_entitled_reports",
        lambda client_id: expected if client_id == "C-01" else None,
    )

    response = client.get("/api/v1/clients/C-01/reports", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == expected
