from datetime import date, datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# --- Request Schemas ---

class ChatRequest(BaseModel):
    client_id: str = Field(
        ...,
        max_length=64,
        description="Unique client identifier, e.g., C-01, C-02",
    )
    question: str = Field(
        ...,
        max_length=4000,
        description="Natural language question or prompt",
    )

    @model_validator(mode="before")
    @classmethod
    def unify_query_and_question(cls, data: Any):
        if isinstance(data, dict):
            if "query" in data and not data.get("question"):
                data["question"] = data["query"]
        return data


class IngestPage(BaseModel):
    page_number: int = Field(..., ge=1, description="One-based source PDF page number")
    content: str = Field(..., min_length=1, max_length=2_000_000)


class IngestRequest(BaseModel):
    report_id: str = Field(..., min_length=1, max_length=32, description="Report identifier, e.g. R-101")
    title: str = Field(..., min_length=1, max_length=255)
    publisher: str = Field(..., min_length=1, max_length=255)
    published_date: date
    sector: str = Field(..., min_length=1, max_length=128)
    access_tier: Literal["paid", "public", "public excerpt"] = Field(
        ..., description="'paid' or 'public'"
    )
    content: Optional[str] = Field(
        None,
        max_length=2_000_000,
        description="Unpaginated text or markdown content (treated as one source page)",
    )
    pages: Optional[List[IngestPage]] = Field(
        None,
        max_length=2000,
        description="Page-aware content for citations to the original report",
    )

    @model_validator(mode="after")
    def validate_content_source(self):
        if self.content is not None and self.pages is not None:
            raise ValueError("Provide either content or pages, not both.")
        if self.content is None and self.pages is None:
            raise ValueError("Provide content or page-aware content.")
        if self.pages is not None:
            total_length = sum(len(page.content) for page in self.pages)
            if total_length > 2_000_000:
                raise ValueError("Combined page content cannot exceed 2,000,000 characters.")
        return self


class IngestResponse(BaseModel):
    status: str = Field("success", description="Status of ingestion")
    report_id: str = Field(..., description="Report identifier")
    chunks_ingested: int = Field(..., description="Count of chunks created and indexed")
    message: str = Field(..., description="Status summary message")


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


class ErrorResponse(BaseModel):
    error: str = Field(..., description="High-level error classification")
    detail: str = Field(..., description="Descriptive error detail")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
