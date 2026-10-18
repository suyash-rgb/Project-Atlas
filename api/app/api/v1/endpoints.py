"""
Backward compatibility bridge.
Re-exports the consolidated api_router from app.api.v1.api as router.
"""
from app.api.v1.api import api_router as router

__all__ = ["router"]
