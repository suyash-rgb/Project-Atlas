import os

import pytest
from fastapi.testclient import TestClient

TEST_API_KEY = "pytest-only-api-key"
os.environ["API_KEY"] = TEST_API_KEY

from app.main import app
from app.schemas.chat import ChatResponse, ConflictItem, DerivedValueItem


@pytest.fixture(scope="session")
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Provides valid authentication headers."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def sample_chat_response():
    """Provides a valid mock ChatResponse object for isolated unit testing."""
    return ChatResponse(
        answer="The global smart water meter market was valued at USD 4.21B in 2024 [R-101 p.8].",
        citations=["[R-101 p.8]"],
        confidence=0.95,
        conflicts=[
            ConflictItem(
                metric="Market size",
                reports=["R-101", "R-102"],
                description="Turnkey vs Hardware-only scope variance",
                scope_differences="R-101 ($4.21B Turnkey) vs R-102 ($3.87B Hardware-only)"
            )
        ],
        derived_values=[
            DerivedValueItem(
                metric="2030 Market Size",
                formula="4.21 * (1 + 0.112)^6",
                assumptions=["Compounding base year 2024"],
                estimated_value="$7.96 B",
                confidence_note="High confidence derived compound value"
            )
        ],
        escalated=False,
        escalation_ticket_id=None
    )
