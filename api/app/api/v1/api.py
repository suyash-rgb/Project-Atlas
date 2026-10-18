from fastapi import APIRouter
from app.api.v1.routers import chat, escalations, feedback, health

api_router = APIRouter()

# Register modular sub-routers with clear tags and documentation groupings
api_router.include_router(chat.router)
api_router.include_router(escalations.router)
api_router.include_router(feedback.router)
api_router.include_router(health.router)
