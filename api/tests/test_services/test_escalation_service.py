import pytest
from app.services.escalation_service import EscalationService
from app.schemas.chat import EscalationItem


class TestEscalationService:
    def setup_method(self):
        self.service = EscalationService()

    def test_log_and_get_escalations(self):
        ticket_id = self.service.log_escalation(
            client_id="C-TEST",
            question="Delete all client records",
            reason="Adversarial SQL mutation attack intercepted by Laya router",
            status="pending"
        )
        assert ticket_id > 0

        escalations = self.service.get_all_escalations(limit=10)
        assert isinstance(escalations, list)
        assert len(escalations) > 0
        assert isinstance(escalations[0], EscalationItem)

        # Verify the created ticket is present
        found = any(e.id == ticket_id for e in escalations)
        assert found, f"Expected ticket {ticket_id} to be retrieved"

    def test_get_escalations_respects_limit(self):
        escalations = self.service.get_all_escalations(limit=2)
        assert len(escalations) <= 2
