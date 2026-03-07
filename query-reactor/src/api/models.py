"""API request and response models for QueryReactor."""

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import time


class QueryRequest(BaseModel):
    """Request model for query processing."""
    
    text: str = Field(..., description="The user's query text")
    user_id: Optional[UUID] = Field(None, description="User identifier (generated if not provided)")
    conversation_id: Optional[UUID] = Field(None, description="Conversation identifier (generated if not provided)")
    locale: Optional[str] = Field(None, description="Language/locale code (e.g., 'en-US')")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")
    
    def __post_init__(self):
        """Generate IDs if not provided."""
        if self.user_id is None:
            self.user_id = uuid4()
        if self.conversation_id is None:
            self.conversation_id = uuid4()


class CitationResponse(BaseModel):
    """Citation information in API response."""
    
    id: int = Field(..., description="Citation number")
    evidence_id: str = Field(..., description="Evidence item identifier")
    title: Optional[str] = Field(None, description="Source title")
    source: str = Field(..., description="Source identifier")
    source_type: str = Field(..., description="Type of source (db, web, api)")
    url: Optional[str] = Field(None, description="Source URL if available")
    retrieval_path: str = Field(..., description="Retrieval path used (P1, P2, P3)")
    content_preview: str = Field(..., description="Preview of source content")
    span: Optional[Dict[str, Any]] = Field(None, description="Text span information if available")


class ProcessingMetadata(BaseModel):
    """Processing metadata in API response."""
    
    workunits_processed: int = Field(..., description="Number of work units processed")
    evidence_items_found: int = Field(..., description="Total evidence items found")
    retrieval_paths_used: List[str] = Field(..., description="Retrieval paths that were used")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time in milliseconds")


class VerificationInfo(BaseModel):
    """Answer verification information."""
    
    is_valid: bool = Field(..., description="Whether answer passed verification")
    confidence: float = Field(..., description="Verification confidence score")
    issues_count: int = Field(..., description="Number of verification issues found")


class QueryResponse(BaseModel):
    """Response model for query processing."""
    
    query_id: str = Field(..., description="Unique identifier for this query")
    answer: str = Field(..., description="The generated answer")
    confidence: float = Field(..., description="Confidence score for the answer")
    citations: List[CitationResponse] = Field(default_factory=list, description="Supporting citations")
    limitations: List[str] = Field(default_factory=list, description="Answer limitations or disclaimers")
    metadata: ProcessingMetadata = Field(..., description="Processing metadata")
    verification: Optional[VerificationInfo] = Field(None, description="Verification information")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    query_id: Optional[str] = Field(None, description="Query ID if available")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Error timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Health check timestamp")
    components: Dict[str, str] = Field(default_factory=dict, description="Component status")


class MetricsResponse(BaseModel):
    """Metrics response model."""
    
    queries_processed: int = Field(..., description="Total queries processed")
    error_rate: float = Field(..., description="Error rate (0.0 to 1.0)")
    average_query_time_ms: float = Field(..., description="Average query processing time")
    average_evidence_retrieved: float = Field(..., description="Average evidence items per query")
    path_usage: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Retrieval path usage statistics")
    loop_frequency: Dict[str, int] = Field(default_factory=dict, description="Loop iteration frequency")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Metrics timestamp")


class FeedbackRequest(BaseModel):
    """Feedback request model."""
    
    query_id: str = Field(..., description="Query identifier")
    feedback_type: str = Field(..., description="Type of feedback (helpful, not_helpful, etc.)")
    rating: Optional[int] = Field(None, description="Rating score (1-5)")
    comments: Optional[str] = Field(None, description="Additional comments")
    user_id: Optional[str] = Field(None, description="User identifier")


class FeedbackResponse(BaseModel):
    """Feedback response model."""

    success: bool = Field(..., description="Whether feedback was recorded successfully")
    message: str = Field(..., description="Response message")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Response timestamp")


class QARequest(BaseModel):
    """Request model for the /api/qa endpoint."""

    question: str = Field(..., description="The user's question")
    user_id: Optional[UUID] = Field(None, description="User identifier (generated if not provided)")
    locale: Optional[str] = Field(None, description="Language/locale code (e.g., 'en-US')")


class QAResponse(QueryResponse):
    """Response model for the /api/qa endpoint — extends QueryResponse with doc_sources."""

    doc_sources: List[str] = Field(
        default_factory=list,
        description="Unique doc_uuid values from all evidence provenance (brain-mvp document IDs)",
    )


class DirectAskRequest(BaseModel):
    """Request model for the /api/ask-direct endpoint."""

    question: str = Field(..., description="The user's question")
    top_k: int = Field(10, description="Number of chunks to retrieve from brain-mvp")
    doc_filter: Optional[str] = Field(None, description="Limit search to a specific doc_uuid")


class DirectChunkSource(BaseModel):
    """A single chunk used as source in the direct RAG response."""

    chunk_id: str
    doc_uuid: str
    score: float
    section_path: Optional[str] = None
    content_preview: str


class DirectAskResponse(BaseModel):
    """Response model for the /api/ask-direct endpoint."""

    query_id: str
    answer: str
    sources: List[DirectChunkSource] = Field(default_factory=list)
    doc_sources: List[str] = Field(default_factory=list, description="Unique doc_uuid values")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))