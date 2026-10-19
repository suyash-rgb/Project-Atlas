import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Security, status

from app.api.deps import verify_api_key
from app.services.client_service import client_service

logger = logging.getLogger("project_atlas.clients_api")

router = APIRouter(prefix="/clients", tags=["Clients & Entitlements"])


@router.get(
    "",
    summary="List all registered corporate clients",
    status_code=status.HTTP_200_OK,
)
def list_clients(_auth: str = Security(verify_api_key)) -> List[Dict[str, Any]]:
    """HTTP endpoint returning list of all registered corporate clients."""
    try:
        return client_service.get_all_clients()
    except Exception as exc:
        logger.exception("list_clients_failed error=%s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve clients catalog.",
        ) from exc


@router.get(
    "/{client_id}/reports",
    summary="Get reports owned and accessible by a client",
    status_code=status.HTTP_200_OK,
)
def get_client_reports(
    client_id: str,
    _auth: str = Security(verify_api_key),
) -> Dict[str, Any]:
    """
    HTTP endpoint returning only the licensed reports purchased by this client,
    plus standard public excerpts permitted under their contract.
    """
    try:
        data = client_service.get_client_entitled_reports(client_id)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client '{client_id.strip().upper()}' not found.",
            )
        return data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_client_reports_failed client_id=%s error=%s", client_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve client entitled reports.",
        ) from exc
