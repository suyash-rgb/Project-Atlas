import hmac
import logging

from fastapi import Request, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger("project_atlas.auth")


def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
) -> str:
    """
    Validates incoming requests against registered API keys.
    Protects client endpoints, escalations, and feedback submissions.
    """
    configured_key = settings.API_KEY
    if not configured_key:
        logger.error(
            "api_auth_rejected reason=server_key_not_configured request_id=%s method=%s path=%s",
            getattr(request.state, "request_id", "unavailable"),
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured"
        )

    if not api_key or not hmac.compare_digest(api_key, configured_key):
        reason = "missing_key" if not api_key else "invalid_key"
        logger.warning(
            "api_auth_rejected reason=%s request_id=%s method=%s path=%s",
            reason,
            getattr(request.state, "request_id", "unavailable"),
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key
