"""Result models for QueryReactor operations."""

from __future__ import annotations
from typing import List, Optional, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from .core import EvidenceItem, WorkUnit
from .types import RQCStatus, RQCReason, SMRDecision


class RQCResult(BaseModel):
    """Result from Retrieval Quality Check module."""
    model_config = ConfigDict(extra="forbid")
    
    status: RQCStatus
    items: Optional[List[EvidenceItem]] = None
    reason: Optional[RQCReason] = None
    diagnostics: Optional[Any] = None
    
    @classmethod
    def ok(cls, items: List[EvidenceItem]) -> "RQCResult":
        """Create successful RQC result."""
        return cls(status=RQCStatus.ok, items=items)
    
    @classmethod
    def no_fit(cls, reason: RQCReason, diagnostics: Optional[Any] = None) -> "RQCResult":
        """Create failed RQC result."""
        return cls(status=RQCStatus.no_fit, reason=reason, diagnostics=diagnostics)


class RoutePlan(BaseModel):
    """Query routing plan from M2."""
    model_config = ConfigDict(extra="forbid")
    
    workunit_id: UUID
    selected_paths: List[str] = Field(description="List of path identifiers (P1, P2, P3)")
    router_decision_id: UUID
    reasoning: Optional[str] = None


class EvidenceSet(BaseModel):
    """Unified evidence set for a WorkUnit."""
    model_config = ConfigDict(extra="forbid")
    
    workunit_id: UUID
    items: List[EvidenceItem]
    source_paths: List[str] = Field(description="Paths that contributed evidence")
    total_items: int = Field(description="Total items before any filtering")
    
    def __post_init__(self):
        """Set total_items if not provided."""
        if not hasattr(self, 'total_items'):
            self.total_items = len(self.items)


class SMRDecisionResult(BaseModel):
    """Result from SmartRetrieval Controller."""
    model_config = ConfigDict(extra="forbid")
    
    decision: SMRDecision
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    feedback: Optional[str] = Field(None, description="Feedback for query refinement")
    
    @classmethod
    def answer_ready(cls, confidence: float, reasoning: Optional[str] = None) -> "SMRDecisionResult":
        """Create answer ready decision."""
        return cls(decision=SMRDecision.answer_ready, confidence=confidence, reasoning=reasoning)
    
    @classmethod
    def needs_refinement(cls, feedback: str, reasoning: Optional[str] = None) -> "SMRDecisionResult":
        """Create needs refinement decision."""
        return cls(
            decision=SMRDecision.needs_better_decomposition,
            confidence=0.0,
            feedback=feedback,
            reasoning=reasoning
        )
    
    @classmethod
    def insufficient_evidence(cls, reasoning: Optional[str] = None) -> "SMRDecisionResult":
        """Create insufficient evidence decision."""
        return cls(
            decision=SMRDecision.insufficient_evidence,
            confidence=0.0,
            reasoning=reasoning
        )


class VerificationResult(BaseModel):
    """Result from answer verification."""
    model_config = ConfigDict(extra="forbid")
    
    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    
    @classmethod
    def valid(cls, confidence: float = 1.0) -> "VerificationResult":
        """Create valid verification result."""
        return cls(is_valid=True, confidence=confidence)
    
    @classmethod
    def invalid(cls, issues: List[str], suggestions: Optional[List[str]] = None) -> "VerificationResult":
        """Create invalid verification result."""
        return cls(
            is_valid=False,
            issues=issues,
            suggestions=suggestions or [],
            confidence=0.0
        )