"""LangGraph workflow orchestration for QueryReactor system."""

from typing import Dict, Any, List, Callable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import time
import functools

from ..models import ReactorState
from ..models.core import HistoryTurn
from ..models.types import Role


def _coerce_state(state) -> ReactorState:
    """Convert a dict (LangGraph 1.x internal representation) back to ReactorState."""
    if isinstance(state, ReactorState):
        return state
    if isinstance(state, dict):
        try:
            return ReactorState.model_validate(state)
        except Exception:
            pass
    return state


def _node(fn: Callable) -> Callable:
    """Wrap a node function so dict state is coerced to ReactorState before the call."""
    if not callable(fn):
        return fn

    @functools.wraps(fn)
    async def _async_wrapper(state):
        return await fn(_coerce_state(state))

    @functools.wraps(fn)
    def _sync_wrapper(state):
        return fn(_coerce_state(state))

    import asyncio
    if asyncio.iscoroutinefunction(fn):
        return _async_wrapper
    return _sync_wrapper
from ..modules import (
    qa_with_human, query_preprocessor, query_router,
    simple_retrieval, internet_retrieval, multihop_orchestrator,
    retrieval_quality_check, evidence_aggregator, reranker,
    smart_retrieval_controller, answer_creator, answer_check,
    interaction_answer
)


class QueryReactorGraph:
    """LangGraph orchestration for QueryReactor workflow."""
    
    def __init__(self):
        """Initialize the QueryReactor graph."""
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _add_user_query_to_history(self, state: ReactorState) -> ReactorState:
        """Add the initial user query to conversation history."""
        if state.original_query:
            user_turn = HistoryTurn(
                role=Role.user,
                text=state.original_query.text,
                timestamp=state.original_query.timestamp,
                locale=state.original_query.locale
            )
            state.add_history_turn(user_turn)
        return state
    
    def _add_assistant_response_to_history(self, state: ReactorState, response_text: str) -> ReactorState:
        """Add assistant response to conversation history."""
        if response_text:
            assistant_turn = HistoryTurn(
                role=Role.assistant,
                text=response_text,
                timestamp=int(time.time() * 1000),  # Current timestamp in ms
                locale=state.original_query.locale if state.original_query else None
            )
            state.add_history_turn(assistant_turn)
        return state
    
    def _add_system_message_to_history(self, state: ReactorState, message: str) -> ReactorState:
        """Add system message to conversation history."""
        if message:
            system_turn = HistoryTurn(
                role=Role.system,
                text=message,
                timestamp=int(time.time() * 1000),
                locale=state.original_query.locale if state.original_query else None
            )
            state.add_history_turn(system_turn)
        return state
    
    def _initialize_history_node(self, state: ReactorState) -> ReactorState:
        """Initialize conversation history with the user query."""
        return self._add_user_query_to_history(state)
    
    async def _m0_with_history(self, state: ReactorState) -> ReactorState:
        """M0 module with history tracking for clarification questions."""
        result_state = await qa_with_human(state)
        
        # If M0 performed clarification (clarification_turns > 0), add it to history
        if (result_state.clarified_query and 
            result_state.clarified_query.clarification_turns > 0):
            clarification_message = f"Clarification needed: {result_state.clarified_query.text}"
            self._add_assistant_response_to_history(
                result_state, 
                clarification_message
            )
        
        return result_state
    
    async def _m12_with_history(self, state: ReactorState) -> ReactorState:
        """M12 module with history tracking for final answers."""
        result_state = await interaction_answer(state)
        
        # Add the final answer to history
        if result_state.final_answer:
            self._add_assistant_response_to_history(
                result_state,
                result_state.final_answer.text
            )
        
        return result_state
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        # Create the state graph
        workflow = StateGraph(ReactorState)
        
        # Add nodes for each module with history tracking
        # All wrapped with _node() to coerce dict→ReactorState (LangGraph 1.x compat)
        workflow.add_node("initialize_history", _node(self._initialize_history_node))
        workflow.add_node("m0_qa_human", _node(self._m0_with_history))
        workflow.add_node("m1_query_preprocessor", _node(query_preprocessor))
        workflow.add_node("m2_query_router", _node(query_router))

        # Retrieval path nodes
        workflow.add_node("m3_simple_retrieval", _node(simple_retrieval))
        workflow.add_node("m5_internet_retrieval", _node(internet_retrieval))
        workflow.add_node("m6_multihop_orchestrator", _node(multihop_orchestrator))
        workflow.add_node("m4_quality_check", _node(retrieval_quality_check))

        # Evidence processing nodes
        workflow.add_node("m7_evidence_aggregator", _node(evidence_aggregator))
        workflow.add_node("m8_reranker", _node(reranker))
        workflow.add_node("m9_smart_controller", _node(smart_retrieval_controller))

        # Answer generation nodes
        workflow.add_node("m10_answer_creator", _node(answer_creator))
        workflow.add_node("m11_answer_check", _node(answer_check))
        workflow.add_node("m12_interaction_answer", _node(self._m12_with_history))
        
        # Define the workflow edges
        self._add_edges(workflow)
        
        # Set entry point to initialize history first
        workflow.set_entry_point("initialize_history")
        
        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    def _add_edges(self, workflow: StateGraph) -> None:
        """Add edges to define the workflow control flow."""
        
        # Initialize history then start with M0
        workflow.add_edge("initialize_history", "m0_qa_human")
        
        # Linear flow from M0 to M2
        workflow.add_edge("m0_qa_human", "m1_query_preprocessor")
        workflow.add_edge("m1_query_preprocessor", "m2_query_router")
        
        # Router to parallel retrieval execution
        workflow.add_node("parallel_retrieval", _node(self._parallel_retrieval_node))
        workflow.add_edge("m2_query_router", "parallel_retrieval")
        
        # Parallel retrieval directly to aggregator (quality check integrated)
        workflow.add_edge("parallel_retrieval", "m7_evidence_aggregator")
        
        # Evidence processing flow
        workflow.add_edge("m7_evidence_aggregator", "m8_reranker")
        workflow.add_edge("m8_reranker", "m9_smart_controller")
        
        # Smart controller conditional routing
        workflow.add_conditional_edges(
            "m9_smart_controller",
            self._smart_controller_routing,
            {
                "answer": "m10_answer_creator",
                "refine": "m1_query_preprocessor",
                "terminate": "m12_interaction_answer"
            }
        )
        
        # Answer generation flow
        workflow.add_edge("m10_answer_creator", "m11_answer_check")
        
        # Answer check conditional routing
        workflow.add_conditional_edges(
            "m11_answer_check",
            self._answer_check_routing,
            {
                "deliver": "m12_interaction_answer",
                "regenerate": "m10_answer_creator",
                "refine_query": "m1_query_preprocessor"
            }
        )
        
        # Final delivery
        workflow.add_edge("m12_interaction_answer", END)
    
    async def _parallel_retrieval_node(self, state: ReactorState) -> ReactorState:
        """並行檢索節點 - 協調 M3, M5, M6 的並行執行"""
        from ..modules.m2d5_path_coordinator import path_coordinator
        return await path_coordinator.execute_parallel_paths(state)
    
    def _smart_controller_routing(self, state) -> str:
        """Route based on SmartRetrieval Controller decision."""
        state = _coerce_state(state)
        decision = getattr(state, 'smr_decision', None)
        if decision == "answer_ready":
            return "answer"
        elif decision == "needs_better_decomposition":
            return "refine"
        elif decision == "insufficient_evidence":
            return "terminate"
        # Default to answer creation if no explicit decision
        return "answer"
    
    def _answer_check_routing(self, state) -> str:
        """Route based on answer verification result."""
        state = _coerce_state(state)
        # Check verification result in state
        result = getattr(state, 'verification_result', None)
        if result is not None:
            if getattr(result, 'is_valid', True):
                return "deliver"
            elif "regenerate" in getattr(result, 'suggestions', []):
                return "regenerate"
            else:
                return "refine_query"
        
        # Default to delivery
        return "deliver"
    
    async def process_query(self, query_data: Dict[str, Any], config: Dict[str, Any]) -> ReactorState:
        """Process a user query through the workflow.
        
        Args:
            query_data: User query data
            config: Configuration dictionary
            
        Returns:
            Final ReactorState with results
        """
        # Create initial state
        from ..models import UserQuery
        from uuid import uuid4
        
        user_query = UserQuery(**query_data)
        initial_state = ReactorState(original_query=user_query)
        
        # Initialize state with configuration
        from ..models.state import StateManager
        state_manager = StateManager(initial_state)
        state_manager.initialize_from_config(config)
        
        # Execute the workflow with LangSmith tracing
        thread_config = {
            "configurable": {
                "thread_id": str(uuid4())
            },
            # LangSmith metadata for better tracing
            "metadata": {
                "query_id": str(user_query.id),
                "user_id": str(user_query.user_id),
                "conversation_id": str(user_query.conversation_id),
                "query_text": user_query.text[:100],  # First 100 chars for privacy
                "locale": user_query.locale
            },
            "tags": ["queryreactor", "production"]
        }
        
        result = await self.graph.ainvoke(
            initial_state,
            config=thread_config
        )

        # LangGraph 1.x may return a dict; coerce back to ReactorState
        return _coerce_state(result)
    
    def get_graph_visualization(self) -> str:
        """Get a text representation of the graph structure."""
        if not self.graph:
            return "Graph not initialized"
        
        # This would return a visualization of the graph structure
        # For now, return a simple description
        return """
QueryReactor Workflow Graph:

M0 (QA Human) → M1 (Query Preprocessor) → M2 (Query Router)
                                              ↓
                    ┌─────────────────────────┼─────────────────────────┐
                    ↓                         ↓                         ↓
            M3 (Simple Retrieval)    M5 (Internet Retrieval)   M6 (MultiHop)
                    ↓                         ↓                         ↓
                    └─────────────────────────┼─────────────────────────┘
                                              ↓
                                    M4 (Quality Check)
                                              ↓
                                    M7 (Evidence Aggregator)
                                              ↓
                                    M8 (ReRanker)
                                              ↓
                                    M9 (Smart Controller)
                                              ↓
                    ┌─────────────────────────┼─────────────────────────┐
                    ↓                         ↓                         ↓
            M10 (Answer Creator)         Refine Query              Terminate
                    ↓                         ↑                         ↓
            M11 (Answer Check)               │                   M12 (Delivery)
                    ↓                         │                         ↑
            M12 (Delivery) ←─────────────────┘                         │
                    ↓                                                   │
                   END ←───────────────────────────────────────────────┘
        """


# Global graph instance
query_reactor_graph = QueryReactorGraph()