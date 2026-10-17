from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- Request Schemas ---

class ChatRequest(BaseModel):
    client_id: str = Field(..., description="Unique client identifier, e.g., C-01, C-02")
    question: str = Field(..., min_length=2, description="Natural language question or prompt")


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
