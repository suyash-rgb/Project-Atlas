from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- Request Schemas ---

class ChatRequest(BaseModel):
    client_id: str = Field(..., description="Unique client identifier, e.g., C-01, C-02")
    question: str = Field(..., description="Natural language question or prompt")

    @model_validator(mode="before")
    @classmethod
    def unify_query_and_question(cls, data: Any):
        if isinstance(data, dict):
            if "query" in data and not data.get("question"):
                data["question"] = data["query"]
        return data


class IngestRequest(BaseModel):
    report_id: str = Field(..., description="Report identifier, e.g. R-101")
    title: str = Field(...)
    publisher: str = Field(...)
    published_date: str = Field(...)
    sector: str = Field(...)
    access_tier: str = Field(..., description="'paid' or 'public'")
    content: str = Field(..., description="Full text or markdown content of the report")


# --- Sub-models for Structured Chat Response ---

class ConflictItem(BaseModel):
    metric: str
    reports: List[str]
    description: str
    scope_differences: str


class DerivedValueItem(BaseModel):
    metric: str
    formula: str
    assumptions: List[str]
    estimated_value: str
    confidence_note: Optional[str] = None


# --- Response Schemas ---

class ChatResponse(BaseModel):
    answer: str
    citations: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    derived_values: List[DerivedValueItem] = Field(default_factory=list)
    escalated: bool = False
    escalation_ticket_id: Optional[str] = None


class EscalationItem(BaseModel):
    id: int
    client_id: str
    question: str
    reason: str
    status: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_store: str


class FeedbackRequest(BaseModel):
    client_id: str = Field(..., description="Client ID submitting feedback, e.g. C-01")
    message_id: Optional[str] = Field("msg_live", description="ID of the message being rated")
    rating: str = Field(..., description="'up' or 'down'")
    comment: Optional[str] = Field(None, description="Optional qualitative feedback")


class FeedbackResponse(BaseModel):
    status: str
    message: str
