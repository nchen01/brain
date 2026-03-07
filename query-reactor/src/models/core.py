"""Core data models for QueryReactor system."""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict, field_validator
import time

from .types import EpochMs, Score, Confidence, Role, SourceType


class TraceInfo(BaseModel):
    """Trace identifiers for observability (OpenTelemetry-compatible)."""
    model_config = ConfigDict(extra="forbid")
    
    trace_id: str
    span_id: Optional[str] = None


class HistoryTurn(BaseModel):
    """A single conversational turn used as context."""
    model_config = ConfigDict(extra="forbid")
    
    role: Role
    text: str
    timestamp: EpochMs
    locale: Optional[str] = None


class ContextBundle(BaseModel):
    """Optional user and conversation context."""
    model_config = ConfigDict(extra="forbid")
    
    history: Optional[List[HistoryTurn]] = None
    user_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="User profile, preferences, or metadata"
    )


class UserQuery(BaseModel):
    """Top-level user request."""
    model_config = ConfigDict(extra="forbid")
    
    # Identity and tenancy
    user_id: UUID
    conversation_id: UUID
    id: UUID = Field(default_factory=uuid4, description="Unique query ID")
    request_id: Optional[str] = Field(
        default=None, description="Idempotency key (defaults to query ID if omitted)"
    )
    
    # Content
    text: str = Field(..., min_length=1, description="Query text cannot be empty")
    locale: Optional[str] = Field(None, description="e.g., 'en-US', 'zh-TW'")
    
    # Timing and tracing
    timestamp: EpochMs = Field(default_factory=lambda: int(time.time() * 1000))
    trace: Optional[TraceInfo] = None
    
    # Optional embedded context
    context: Optional[ContextBundle] = None
    
    def __post_init__(self):
        """Set request_id to query ID if not provided."""
        if self.request_id is None:
            self.request_id = str(self.id)


class ClarifiedQuery(BaseModel):
    """Query after clarification process."""
    model_config = ConfigDict(extra="forbid")
    
    # Inherit from UserQuery structure
    user_id: UUID
    conversation_id: UUID
    id: UUID
    text: str
    locale: Optional[str] = None
    timestamp: EpochMs
    trace: Optional[TraceInfo] = None
    
    # Clarification metadata
    original_text: str
    clarification_turns: int = 0
    confidence: Confidence


class WorkUnit(BaseModel):
    """A unit of work — the original query or a sub-question."""
    model_config = ConfigDict(extra="forbid")
    
    id: UUID = Field(default_factory=uuid4)
    parent_query_id: UUID
    parent_workunit_id: Optional[UUID] = Field(None, description="Hierarchical linkage")
    text: str
    is_subquestion: bool
    locale: Optional[str] = None
    timestamp: EpochMs = Field(default_factory=lambda: int(time.time() * 1000))
    priority: Optional[int] = Field(
        None, description="Scheduler hint (lower = higher priority)"
    )
    features: Optional[Dict[str, Any]] = None
    trace: Optional[TraceInfo] = None
    
    # Tenancy
    user_id: UUID
    conversation_id: UUID


class Provenance(BaseModel):
    """Metadata describing where an evidence item originated."""
    model_config = ConfigDict(extra="forbid")
    
    source_type: SourceType
    source_id: str
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    retrieved_at: EpochMs = Field(default_factory=lambda: int(time.time() * 1000))
    retrieval_path: str = Field(..., description="Retrieval route identifier (e.g. 'P1')")
    router_decision_id: UUID
    
    # Ranking-related metadata
    authority_score: Optional[Confidence] = None
    published_at: Optional[EpochMs] = None
    language: Optional[str] = None


class EvidenceItem(BaseModel):
    """An evidence item (text snippet, record, or structured data)."""
    model_config = ConfigDict(extra="forbid")
    
    id: UUID = Field(default_factory=uuid4)
    workunit_id: UUID
    user_id: UUID
    conversation_id: UUID
    content: str = Field(..., min_length=1, description="Evidence content cannot be empty")
    title: Optional[str] = None
    section_title: Optional[str] = None
    language: Optional[str] = None
    char_len: Optional[int] = Field(None, ge=0)
    tokens: Optional[int] = Field(None, ge=0)
    score_raw: Optional[Score] = Field(None, description="Retriever score before reranking")
    embeddings: Optional[List[float]] = Field(None, description="Optional embedding vector")
    provenance: Provenance
    
    @field_validator("char_len", mode="before")
    @classmethod
    def derive_length(cls, v, info):
        """Auto-derive character length from content if missing."""
        if v is None and (content := info.data.get("content")):
            return len(content)
        return v


class RankedEvidence(EvidenceItem):
    """Evidence after M8 ReRanker processing."""
    rr_score: Score = Field(..., description="ReRanker model score")
    rank: int = Field(..., ge=1, description="1-based rank within the WorkUnit")
    is_primary: bool = Field(..., description="True if within top-K for this WorkUnit")
    rationale: Optional[str] = Field(None, description="Explanation or justification text")


class Citation(BaseModel):
    """A link from an answer segment to a supporting evidence item."""
    model_config = ConfigDict(extra="forbid")
    
    evidence_id: UUID
    span_start: Optional[int] = Field(None, description="Character start offset in answer text")
    span_end: Optional[int] = Field(None, description="Character end offset in answer text")
    
    @field_validator("span_start", "span_end")
    @classmethod
    def validate_span_values(cls, v):
        if v is not None and v < 0:
            raise ValueError("Citation span values must be >= 0")
        return v
    
    def model_post_init(self, __context):
        """Validate span consistency after model creation."""
        if self.span_start is not None and self.span_end is not None:
            if self.span_end < self.span_start:
                raise ValueError("Citation span_end must be >= span_start")


class Answer(BaseModel):
    """Final or partial answer returned to the user."""
    model_config = ConfigDict(extra="forbid")
    
    user_id: UUID
    conversation_id: UUID
    query_id: UUID
    workunit_id: Optional[UUID] = None
    text: str
    citations: List[Citation]
    limitations: Optional[List[str]] = None
    confidence: Optional[Confidence] = None
    locale: Optional[str] = None
    timestamp: EpochMs = Field(default_factory=lambda: int(time.time() * 1000))
    trace: Optional[TraceInfo] = None