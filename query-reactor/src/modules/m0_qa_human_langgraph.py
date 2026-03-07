"""M0 - QA with Human (LangGraph + Pydantic Implementation)

This module implements the first stage of the question-answering flow using LangGraph
with Pydantic structured output for reliable clarity assessment and routing.
"""

from typing import TypedDict, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .base import LLMModule
from ..models.state import ReactorState
from ..models.core import ClarifiedQuery, HistoryTurn
from ..config.model_manager import model_manager


# 1. Define LangGraph State
class M0State(TypedDict, total=False):
    """State passed through M0 LangGraph nodes."""
    history: str                    # Serialized <history>...</history>
    current_query: str             # Serialized <current_query>...</current_query>
    clarity_score: float           # Filled after assessment
    needs_followup: bool           # Branch flag
    followup_question: Optional[str]  # Filled if needs_followup == True
    original_state: ReactorState   # Original reactor state for context


# 2. Define Pydantic Schema for Clarity Output
class ClarityResult(BaseModel):
    """Pydantic model for structured clarity assessment output."""
    clarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How clear and unambiguous the query is, from 0.0 (unclear) to 1.0 (fully clear)."
    )


# 3. Define Pydantic Schema for Follow-up Question Output
class FollowupResult(BaseModel):
    """Pydantic model for structured follow-up question output."""
    question: str = Field(
        min_length=1,
        description="A targeted clarifying question to resolve ambiguity."
    )


class QAWithHumanLangGraph(LLMModule):
    """M0 module implemented with LangGraph and Pydantic structured output."""
    
    def __init__(self):
        super().__init__("M0", "qa.model")
        self.graph = self._build_graph()
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute the M0 LangGraph workflow."""
        self._update_state_module(state)
        self._log_execution_start(state, "Starting M0 LangGraph workflow")
        
        try:
            # Prepare M0 state
            m0_state = self._prepare_m0_state(state)
            
            # Run the LangGraph
            result = await self.graph.ainvoke(m0_state)
            
            # Convert back to ReactorState
            updated_state = self._convert_to_reactor_state(result, state)
            
            self._log_execution_end(state, f"M0 completed with clarity score: {result.get('clarity_score', 'N/A')}")
            return updated_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M0 Execute - {e}")
            print(f"   → Creating basic clarified query")
            # Fallback: create a basic clarified query
            fallback_query = ClarifiedQuery(
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                id=state.original_query.id,
                text=state.original_query.text,
                locale=state.original_query.locale,
                timestamp=state.original_query.timestamp,
                trace=state.original_query.trace,
                original_text=state.original_query.text,
                clarification_turns=0,
                confidence=0.5  # Default moderate confidence
            )
            state.clarified_query = fallback_query
            return state
    
    def _prepare_m0_state(self, state: ReactorState) -> M0State:
        """Convert ReactorState to M0State for LangGraph."""
        # Format history as XML
        history_xml = self._format_history_for_xml(state.get_recent_history(3))
        
        return M0State(
            history=history_xml,
            current_query=state.original_query.text,
            original_state=state
        )
    
    def _format_history_for_xml(self, history: list) -> str:
        """Format conversation history for XML structure."""
        if not history:
            return "No previous conversation history."
        
        formatted_history = []
        for turn in history[-3:]:  # Only use last 3 turns
            role = "User" if turn.role.value == "user" else "Assistant"
            content = getattr(turn, 'text', getattr(turn, 'content', str(turn)))
            formatted_history.append(f"{role}: {content}")
        
        return "\n".join(formatted_history)
    
    def _convert_to_reactor_state(self, m0_result: M0State, original_state: ReactorState) -> ReactorState:
        """Convert M0State result back to ReactorState."""
        clarity_score = m0_result.get('clarity_score', 0.5)
        followup_question = m0_result.get('followup_question', '')
        
        # Determine final query text
        if followup_question and m0_result.get('needs_followup', False):
            final_text = f"{original_state.original_query.text} [Clarification needed: {followup_question}]"
            clarification_turns = 1
        else:
            final_text = original_state.original_query.text
            clarification_turns = 0
        
        # Create clarified query
        clarified_query = ClarifiedQuery(
            user_id=original_state.original_query.user_id,
            conversation_id=original_state.original_query.conversation_id,
            id=original_state.original_query.id,
            text=final_text,
            locale=original_state.original_query.locale,
            timestamp=original_state.original_query.timestamp,
            trace=original_state.original_query.trace,
            original_text=original_state.original_query.text,
            clarification_turns=clarification_turns,
            confidence=clarity_score
        )
        
        original_state.clarified_query = clarified_query
        return original_state
    
    def _build_graph(self) -> StateGraph:
        """Build the M0 LangGraph with clarity assessment and follow-up nodes."""
        graph = StateGraph(M0State)
        
        # Add nodes
        graph.add_node("m0_clarity_assessment", self._clarity_assessment_node)
        graph.add_node("m0_followup_question", self._followup_question_node)
        
        # Set entry point
        graph.set_entry_point("m0_clarity_assessment")
        
        # Add conditional routing
        graph.add_conditional_edges(
            "m0_clarity_assessment",
            self._route_after_clarity,
            {
                "followup": "m0_followup_question",
                "end": END
            }
        )
        
        # After follow-up, we're done
        graph.add_edge("m0_followup_question", END)
        
        return graph.compile()
    
    async def _clarity_assessment_node(self, state: M0State) -> M0State:
        """LangGraph node for clarity assessment with Pydantic structured output."""
        try:
            # Get model and create structured LLM
            model_name = model_manager.get_model_for_task('clarity_assessment', self.model_config_key)
            api_params = model_manager.optimize_params_for_task(model_name, 'clarity_assessment')
            
            # Create LLM with structured output
            raw_llm = ChatOpenAI(
                model=api_params["model"],
                temperature=api_params.get("temperature", 0.0)
            )
            clarity_llm = raw_llm.with_structured_output(ClarityResult)
            
            # Get prompt from configuration
            clarity_prompt = self._get_prompt("m0_clarity_assessment", 
                "Assess query clarity and return a score between 0.0 and 1.0")
            
            # Format prompt with XML structure
            full_prompt = f"""{clarity_prompt}

<history>
{state["history"]}
</history>

<current_query>
{state["current_query"]}
</current_query>

Return ONLY a JSON object with a single field: {{"clarity_score": number}}"""
            
            # Call structured LLM - result is automatically validated
            result: ClarityResult = await clarity_llm.ainvoke(full_prompt)
            clarity_score = result.clarity_score
            
            # Determine if follow-up is needed (threshold: 0.7)
            clarity_threshold = self._get_config("qa.clarity_threshold", 0.7)
            needs_followup = clarity_score <= clarity_threshold
            
            # Update state
            return {
                **state,
                "clarity_score": clarity_score,
                "needs_followup": needs_followup
            }
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Error in clarity assessment: {str(e)}")
            print(f"🔄 FALLBACK TRIGGERED: M0 Clarity Assessment - {e}")
            print(f"   → Using moderate confidence fallback")
            # Fallback with moderate confidence
            return {
                **state,
                "clarity_score": 0.5,
                "needs_followup": True
            }
    
    async def _followup_question_node(self, state: M0State) -> M0State:
        """LangGraph node for follow-up question generation with Pydantic structured output."""
        # Only run if we actually need clarification
        if not state.get("needs_followup", False):
            return state
        
        try:
            # Get model and create structured LLM
            model_name = model_manager.get_model_for_task('clarity_assessment', self.model_config_key)
            api_params = model_manager.optimize_params_for_task(model_name, 'clarity_assessment')
            
            # Create LLM with structured output
            raw_llm = ChatOpenAI(
                model=api_params["model"],
                temperature=api_params.get("temperature", 0.3)
            )
            followup_llm = raw_llm.with_structured_output(FollowupResult)
            
            # Get prompt from configuration
            followup_prompt = self._get_prompt("m0_followup_question",
                "Generate targeted follow-up questions to clarify the user's intent.")
            
            # Format prompt with XML structure
            full_prompt = f"""{followup_prompt}

<history>
{state["history"]}
</history>

<current_query>
{state["current_query"]}
</current_query>

Return ONLY a JSON object with a single field: {{"question": "your clarifying question here"}}"""
            
            # Call structured LLM - result is automatically validated
            result: FollowupResult = await followup_llm.ainvoke(full_prompt)
            
            return {
                **state,
                "followup_question": result.question
            }
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Error in follow-up generation: {str(e)}")
            print(f"🔄 FALLBACK TRIGGERED: M0 Follow-up Generation - {e}")
            print(f"   → Using generic follow-up question")
            # Fallback question
            return {
                **state,
                "followup_question": "Could you provide more details about what you're looking for?"
            }
    
    def _route_after_clarity(self, state: M0State) -> str:
        """Routing function to decide next node after clarity assessment."""
        if state.get("needs_followup", False):
            return "followup"
        else:
            return "end"


# Module instance
qa_with_human_langgraph = QAWithHumanLangGraph()


# LangGraph node function for integration
async def qa_with_human_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M0 - QA with Human (LangGraph implementation)."""
    return await qa_with_human_langgraph.execute(state)