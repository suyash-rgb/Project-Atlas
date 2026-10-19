"""
Project Atlas Service Layer.
Encapsulates business logic, data persistence, and agent workflow orchestration.
"""
from app.services.chat_service import ChatService, chat_service
from app.services.client_service import ClientService, client_service
from app.services.escalation_service import EscalationService, escalation_service
from app.services.feedback_service import FeedbackService, feedback_service
from app.services.health_service import HealthService, health_service

__all__ = [
    "ChatService",
    "chat_service",
    "ClientService",
    "client_service",
    "EscalationService",
    "escalation_service",
    "FeedbackService",
    "feedback_service",
    "HealthService",
    "health_service",
]
