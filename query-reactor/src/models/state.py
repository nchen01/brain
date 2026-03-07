"""State management models for QueryReactor system."""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from .core import UserQuery, WorkUnit, EvidenceItem, RankedEvidence, Answer, HistoryTurn, ClarifiedQuery


class LoopCounters(BaseModel):
    """Loop counters for preventing infinite cycles."""
    model_config = ConfigDict(extra="allow")  # Allow arbitrary counter names
    
    smartretrieval_to_qp: int = 0
    answercheck_to_ac: int = 0
    answercheck_to_qp: int = 0
    
    def __getitem__(self, key: str) -> int:
        """Support dict-like access for reading counters."""
        return getattr(self, key, 0)
    
    def __setitem__(self, key: str, value: int) -> None:
        """Support dict-like access for setting counters."""
        setattr(self, key, value)
    
    def get(self, key: str, default: int = 0) -> int:
        """Get counter value with default."""
        return getattr(self, key, default)
    
    def reset(self) -> None:
        """Reset all counters to 0."""
        # Reset known counters
        self.smartretrieval_to_qp = 0
        self.answercheck_to_ac = 0
        self.answercheck_to_qp = 0
        
        # Reset any additional counters to 0 (don't delete them)
        if hasattr(self, '__pydantic_extra__') and self.__pydantic_extra__:
            for field_name in list(self.__pydantic_extra__.keys()):
                self.__pydantic_extra__[field_name] = 0
    
    def increment_smr_to_qp(self) -> int:
        """Increment smartretrieval_to_qp counter and return new value."""
        self.smartretrieval_to_qp += 1
        return self.smartretrieval_to_qp
    
    def increment_ack_to_ac(self) -> int:
        """Increment answercheck_to_ac counter and return new value."""
        self.answercheck_to_ac += 1
        return self.answercheck_to_ac
    
    def increment_ack_to_qp(self) -> int:
        """Increment answercheck_to_qp counter and return new value."""
        self.answercheck_to_qp += 1
        return self.answercheck_to_qp


class RouterStats(BaseModel):
    """Statistics for routing decisions."""
    model_config = ConfigDict(extra="forbid")
    
    total_workunits: int = 0
    path_selections: Dict[str, int] = Field(default_factory=dict)
    parallel_routes: int = 0
    routing_time_ms: float = 0.0


class PathStats(BaseModel):
    """Statistics for retrieval paths."""
    model_config = ConfigDict(extra="forbid")
    
    path_id: str
    execution_time_ms: float = 0.0
    evidence_count: int = 0
    success: bool = True
    error_message: Optional[str] = None


class ReactorState(BaseModel):
    """Shared LangGraph state (append-only and deterministic)."""
    model_config = ConfigDict(extra="allow")  # Allow additional fields for enhanced modules
    
    # Core query and processing data
    original_query: UserQuery
    clarified_query: Optional[ClarifiedQuery] = None
    workunits: List[WorkUnit] = Field(default_factory=list)
    evidences: List[EvidenceItem] = Field(default_factory=list)
    ranked_evidence: Dict[UUID, List[RankedEvidence]] = Field(default_factory=dict)
    partial_answers: Optional[List[Answer]] = None
    final_answer: Optional[Answer] = None
    
    # Configuration snapshot
    cfg: Optional[Dict[str, Any]] = Field(None, description="Runtime configuration snapshot")
    
    # State management components from [S0]
    history: List[HistoryTurn] = Field(default_factory=list)
    loop_counters: LoopCounters = Field(default_factory=LoopCounters)
    loop_limits: Dict[str, int] = Field(default_factory=dict)
    
    # Statistics and tracing
    router_stats: Optional[RouterStats] = None
    path_stats: List[PathStats] = Field(default_factory=list)
    request_index: Optional[str] = None
    
    # Processing metadata
    current_module: Optional[str] = None
    processing_start_time: Optional[int] = None
    total_processing_time_ms: Optional[int] = None
    loop_feedback: Optional[str] = None
    
    # Module-specific results
    route_plans: Optional[List[Any]] = None  # From M2 - Query Router
    rqc_results: Optional[Dict[str, Any]] = None  # From M4 - Quality Check
    evidence_sets: Optional[List[Any]] = None  # From M7 - Evidence Aggregator
    smr_decision: Optional[str] = None  # From M9 - Smart Controller
    smr_confidence: Optional[float] = None  # From M9 - Smart Controller
    smr_reasoning: Optional[str] = None  # From M9 - Smart Controller
    verification_result: Optional[Any] = None  # From M11 - Answer Check
    formatted_answer: Optional[Dict[str, Any]] = None  # From M12 - Interaction Answer
    feedback_mechanism: Optional[str] = None  # From M12 - Interaction Answer
    
    def add_workunit(self, workunit: WorkUnit) -> None:
        """Add a WorkUnit to tracking."""
        self.workunits.append(workunit)
    
    def get_workunit(self, workunit_id: UUID) -> Optional[WorkUnit]:
        """Get WorkUnit by ID."""
        for wu in self.workunits:
            if wu.id == workunit_id:
                return wu
        return None
    
    def add_evidence(self, evidence: EvidenceItem) -> None:
        """Add evidence item."""
        self.evidences.append(evidence)
    
    def get_evidence_for_workunit(self, workunit_id: UUID) -> List[EvidenceItem]:
        """Get all evidence for a specific WorkUnit."""
        return [e for e in self.evidences if e.workunit_id == workunit_id]
    
    def set_ranked_evidence(self, workunit_id: UUID, ranked: List[RankedEvidence]) -> None:
        """Set ranked evidence for a WorkUnit."""
        self.ranked_evidence[workunit_id] = ranked
    
    def get_ranked_evidence(self, workunit_id: UUID) -> List[RankedEvidence]:
        """Get ranked evidence for a WorkUnit."""
        return self.ranked_evidence.get(workunit_id, [])
    
    def add_history_turn(self, turn: HistoryTurn) -> None:
        """Add a conversation turn to history."""
        self.history.append(turn)
    
    def get_recent_history(self, n: int = 5) -> List[HistoryTurn]:
        """Get the last N history turns."""
        return self.history[-n:] if len(self.history) > n else self.history
    
    def check_loop_limit(self, loop_type: str) -> bool:
        """Check if loop limit has been exceeded."""
        current_count = getattr(self.loop_counters, loop_type, 0)
        limit = self.loop_limits.get(f"loop.max.{loop_type}", float('inf'))
        return current_count >= limit
    
    def increment_loop_counter(self, loop_type: str) -> int:
        """Increment loop counter and return new value."""
        # Use specific methods for known counter types
        if loop_type == "smartretrieval_to_qp":
            return self.loop_counters.increment_smr_to_qp()
        elif loop_type == "answercheck_to_ac":
            return self.loop_counters.increment_ack_to_ac()
        elif loop_type == "answercheck_to_qp":
            return self.loop_counters.increment_ack_to_qp()
        else:
            # Support arbitrary counter names for testing and future use
            current_value = self.loop_counters.get(loop_type, 0)
            new_value = current_value + 1
            self.loop_counters[loop_type] = new_value
            return new_value
    
    def reset_loop_counters(self) -> None:
        """Reset all loop counters (called when entering M1 for first time)."""
        self.loop_counters.reset()
    
    def add_path_stats(self, stats: PathStats) -> None:
        """Add path execution statistics."""
        self.path_stats.append(stats)
    
    def set_current_module(self, module_code: str) -> None:
        """Set the currently executing module."""
        self.current_module = module_code
    
    def set_loop_feedback(self, feedback: str) -> None:
        """Set feedback for loop refinement."""
        self.loop_feedback = feedback
    
    def clear_loop_feedback(self) -> None:
        """Clear loop feedback."""
        self.loop_feedback = None


class StateManager:
    """Manager for ReactorState operations."""
    
    def __init__(self, state: ReactorState):
        self.state = state
    
    def initialize_from_config(self, config: Dict[str, Any]) -> None:
        """Initialize state with configuration values."""
        self.state.cfg = config.copy()
        
        # Set loop limits from config
        self.state.loop_limits = {
            "loop.max.smartretrieval_to_qp": config.get("loop", {}).get("max", {}).get("smartretrieval_to_qp", 2),
            "loop.max.answercheck_to_ac": config.get("loop", {}).get("max", {}).get("answercheck_to_ac", 3),
            "loop.max.answercheck_to_qp": config.get("loop", {}).get("max", {}).get("answercheck_to_qp", 1),
        }
    
    def can_loop(self, loop_type: str) -> bool:
        """Check if another loop iteration is allowed."""
        return not self.state.check_loop_limit(loop_type)
    
    def should_terminate_loop(self, loop_type: str) -> bool:
        """Check if loop should be terminated due to limits."""
        return self.state.check_loop_limit(loop_type)
    
    def get_evidence_summary(self) -> Dict[str, Any]:
        """Get summary of evidence collection."""
        total_evidence = len(self.state.evidences)
        evidence_by_workunit = {}
        
        for wu in self.state.workunits:
            evidence_count = len(self.state.get_evidence_for_workunit(wu.id))
            ranked_count = len(self.state.get_ranked_evidence(wu.id))
            evidence_by_workunit[str(wu.id)] = {
                "raw_evidence": evidence_count,
                "ranked_evidence": ranked_count,
                "workunit_text": wu.text
            }
        
        return {
            "total_evidence": total_evidence,
            "total_workunits": len(self.state.workunits),
            "evidence_by_workunit": evidence_by_workunit,
            "has_final_answer": self.state.final_answer is not None
        }