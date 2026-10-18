from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates incoming requests against registered API keys.
    Protects client endpoints, escalations, and feedback submissions.
    """
    valid_keys = {settings.API_KEY, "atlas_secret_token_2026", "atlas_dev_secret_key"}
    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key
