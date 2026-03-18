"""M1 - Query Preprocessor (LangGraph + Pydantic Implementation)."""

from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from ..models import ReactorState, WorkUnit, HistoryTurn, Role
from .base import LLMModule
from ..config.model_manager import model_manager


class ModernBaseModel(BaseModel):
    """Base model with Pydantic v2 compatibility methods."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Modern replacement for deprecated dict() method."""
        return self.model_dump()
    
    @classmethod
    def from_json(cls, json_str: str):
        """Modern replacement for deprecated parse_raw() method."""
        return cls.model_validate_json(json_str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Modern replacement for deprecated parse_obj() method."""
        return cls.model_validate(data)


class QueryNormalizationOutput(ModernBaseModel):
    """Pydantic model for query normalization output."""
    normalized_text: str = Field(description="Normalized query text")
    changes_made: Optional[List[str]] = Field(default=None, description="List of normalization changes")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in normalization")


class ReferenceResolutionOutput(ModernBaseModel):
    """Pydantic model for reference resolution output."""
    resolved_text: str = Field(description="Text with resolved references")
    resolutions: Optional[Dict[str, str]] = Field(default=None, description="Map of resolved references")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in resolution")


class QueryDecompositionOutput(ModernBaseModel):
    """Pydantic model for query decomposition output."""
    should_decompose: bool = Field(description="Whether query should be decomposed")
    sub_questions: Optional[List[str]] = Field(default=None, description="Generated sub-questions")
    is_multihop: bool = Field(default=False, description="Whether this requires multi-hop reasoning")
    reasoning: str = Field(description="Reasoning for decomposition decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in decomposition")


class StructuredLLMFactory:
    """Factory for creating structured output LLMs like M0."""
    
    @staticmethod
    def create_normalization_llm() -> ChatOpenAI:
        """Create LLM for query normalization with structured output."""
        model_name = model_manager.get_model_for_task('normalization', 'qp.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'normalization')
        
        raw_llm = ChatOpenAI(
            model=api_params["model"],
            temperature=api_params.get("temperature", 0.0)
        )
        return raw_llm.with_structured_output(QueryNormalizationOutput, method="function_calling")
    
    @staticmethod
    def create_resolution_llm() -> ChatOpenAI:
        """Create LLM for reference resolution with structured output."""
        model_name = model_manager.get_model_for_task('reference_resolution', 'qp.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'reference_resolution')
        
        raw_llm = ChatOpenAI(
            model=api_params["model"],
            temperature=api_params.get("temperature", 0.1)
        )
        return raw_llm.with_structured_output(ReferenceResolutionOutput, method="function_calling")
    
    @staticmethod
    def create_decomposition_llm() -> ChatOpenAI:
        """Create LLM for query decomposition with structured output."""
        model_name = model_manager.get_model_for_task('decomposition', 'qp.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'decomposition')
        
        raw_llm = ChatOpenAI(
            model=api_params["model"],
            temperature=api_params.get("temperature", 0.2)
        )
        return raw_llm.with_structured_output(QueryDecompositionOutput, method="function_calling")


class StateAttributeManager:
    """Manages safe attribute access and initialization for ReactorState."""
    
    @staticmethod
    def ensure_preprocessing_metadata(state: ReactorState) -> None:
        """Ensure preprocessing_metadata attribute exists and is initialized."""
        if not hasattr(state, 'preprocessing_metadata'):
            state.preprocessing_metadata = {}
    
    @staticmethod
    def safe_get_attribute(state: ReactorState, attr_name: str, default: Any = None) -> Any:
        """Safely get attribute with fallback to default value."""
        return getattr(state, attr_name, default)
    
    @staticmethod
    def safe_set_attribute(state: ReactorState, attr_name: str, value: Any) -> None:
        """Safely set attribute with proper type checking."""
        if not isinstance(state, ReactorState):
            raise TypeError(f"Expected ReactorState, got {type(state)}")
        setattr(state, attr_name, value)
    
    @staticmethod
    def get_current_query_text(state: ReactorState) -> str:
        """Get the current query text, prioritizing clarified_query from M0."""
        # First check if M0 has provided a clarified query
        clarified_query = getattr(state, 'clarified_query', None)
        if clarified_query is not None:
            return clarified_query.text
        
        # Fallback to original query
        return state.original_query.text
    
    @staticmethod
    def get_conversation_context(state: ReactorState, max_turns: int = 3) -> List[HistoryTurn]:
        """Get relevant conversation history for the current query session."""
        # Get recent history, excluding the current query if it's already in history
        recent_history = state.get_recent_history(max_turns + 1)  # Get extra in case current query is included
        
        current_query_text = StateAttributeManager.get_current_query_text(state)
        
        # Filter out the current query from history to avoid duplication
        filtered_history = []
        for turn in recent_history:
            if turn.text != current_query_text and turn.text != state.original_query.text:
                filtered_history.append(turn)
        
        # Return only the requested number of turns
        return filtered_history[-max_turns:] if len(filtered_history) > max_turns else filtered_history


class StateValidator:
    """Validates ReactorState consistency throughout processing."""
    
    @staticmethod
    def validate_state_type(state: Any) -> ReactorState:
        """Ensure state is ReactorState, not dict or other type."""
        if isinstance(state, dict):
            raise TypeError("Received dict instead of ReactorState - check node return types")
        if not isinstance(state, ReactorState):
            raise TypeError(f"Expected ReactorState, got {type(state)}")
        return state
    
    @staticmethod
    def validate_required_attributes(state: ReactorState) -> None:
        """Validate that required attributes exist before processing."""
        required_attrs = ['original_query', 'workunits']
        for attr in required_attrs:
            if not hasattr(state, attr):
                raise AttributeError(f"ReactorState missing required attribute: {attr}")


class ReactorStateExtensions:
    """Extensions for ReactorState to support M1 modernization."""
    
    @staticmethod
    def initialize_m1_attributes(state: ReactorState) -> None:
        """Initialize all M1-specific attributes safely."""
        if not hasattr(state, 'preprocessing_metadata'):
            state.preprocessing_metadata = {}
        if not hasattr(state, 'processing_query'):
            # Use clarified query from M0 if available, otherwise original query
            state.processing_query = StateAttributeManager.get_current_query_text(state)
        if not hasattr(state, 'decomposed_queries'):
            state.decomposed_queries = []
        if not hasattr(state, '_m1_entered'):
            state._m1_entered = False
    
    @staticmethod
    def ensure_history_management(state: ReactorState) -> None:
        """Ensure proper history management for M1 processing."""
        # Check if current query is already in history (added by M0 or previous processing)
        current_query_text = StateAttributeManager.get_current_query_text(state)
        original_query_text = state.original_query.text
        
        # Check if either the original or clarified query is already in history
        query_in_history = any(
            turn.text in [current_query_text, original_query_text] 
            for turn in state.history
        )
        
        # If not in history, we'll add it after M1 processing completes
        # This prevents duplication while ensuring the query is captured
        if not query_in_history:
            state._needs_history_update = True
        else:
            state._needs_history_update = False


class QueryPreprocessorLangGraph(LLMModule):
    """M1 - Query preprocessing with LangGraph orchestration and Pydantic validation."""
    
    def __init__(self):
        super().__init__("M1_LG", "qp.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    async def test_structured_llm_factory(self) -> Dict[str, str]:
        """Test method to verify StructuredLLMFactory works correctly."""
        try:
            # Test normalization LLM creation
            norm_llm = StructuredLLMFactory.create_normalization_llm()
            
            # Test resolution LLM creation
            res_llm = StructuredLLMFactory.create_resolution_llm()
            
            # Test decomposition LLM creation
            decomp_llm = StructuredLLMFactory.create_decomposition_llm()
            
            return {
                "normalization_llm": f"Created successfully: {type(norm_llm).__name__}",
                "resolution_llm": f"Created successfully: {type(res_llm).__name__}",
                "decomposition_llm": f"Created successfully: {type(decomp_llm).__name__}",
                "status": "All LLM factories working correctly"
            }
        except Exception as e:
            return {
                "error": f"LLM factory test failed: {str(e)}",
                "status": "Failed"
            }
    
    def test_pydantic_models(self) -> Dict[str, str]:
        """Test method to verify Pydantic models work correctly with v2 methods."""
        try:
            # Test QueryNormalizationOutput
            norm_data = {
                "normalized_text": "What is Python programming?",
                "changes_made": ["Fixed capitalization"],
                "confidence": 0.9
            }
            norm_output = QueryNormalizationOutput.from_dict(norm_data)
            norm_dict = norm_output.to_dict()
            
            # Test ReferenceResolutionOutput
            res_data = {
                "resolved_text": "What is Python programming?",
                "resolutions": {"it": "Python"},
                "confidence": 0.8
            }
            res_output = ReferenceResolutionOutput.from_dict(res_data)
            res_dict = res_output.to_dict()
            
            # Test QueryDecompositionOutput
            decomp_data = {
                "should_decompose": False,
                "sub_questions": [],
                "reasoning": "Single focused question",
                "confidence": 0.85
            }
            decomp_output = QueryDecompositionOutput.from_dict(decomp_data)
            decomp_dict = decomp_output.to_dict()
            
            return {
                "normalization_model": f"✓ Created and converted: {len(norm_dict)} fields",
                "resolution_model": f"✓ Created and converted: {len(res_dict)} fields",
                "decomposition_model": f"✓ Created and converted: {len(decomp_dict)} fields",
                "status": "All Pydantic models working correctly with v2 methods"
            }
        except Exception as e:
            return {
                "error": f"Pydantic model test failed: {str(e)}",
                "status": "Failed"
            }
    
    def test_state_management(self, test_state: ReactorState) -> Dict[str, str]:
        """Test method to verify state management components work correctly."""
        try:
            # Test StateValidator
            StateValidator.validate_state_type(test_state)
            StateValidator.validate_required_attributes(test_state)
            
            # Test ReactorStateExtensions
            ReactorStateExtensions.initialize_m1_attributes(test_state)
            ReactorStateExtensions.ensure_history_management(test_state)
            
            # Test StateAttributeManager
            StateAttributeManager.ensure_preprocessing_metadata(test_state)
            current_query = StateAttributeManager.get_current_query_text(test_state)
            context = StateAttributeManager.get_conversation_context(test_state)
            
            # Test safe attribute operations
            StateAttributeManager.safe_set_attribute(test_state, 'test_attr', 'test_value')
            test_value = StateAttributeManager.safe_get_attribute(test_state, 'test_attr', 'default')
            
            return {
                "state_validator": "✓ Validation passed",
                "state_extensions": "✓ Initialization completed",
                "attribute_manager": f"✓ Query: {current_query[:30]}..., Context: {len(context)} turns",
                "safe_operations": f"✓ Set/Get test: {test_value}",
                "status": "All state management components working correctly"
            }
        except Exception as e:
            return {
                "error": f"State management test failed: {str(e)}",
                "status": "Failed"
            }
    
    async def _safe_llm_call(self, llm: ChatOpenAI, prompt: str, fallback_func: callable) -> Any:
        """Safe LLM call with automatic fallback."""
        try:
            result = await llm.ainvoke(prompt)
            return result
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] LLM call failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M1 LLM Call - {e}")
            print(f"   → Using fallback function")
            return fallback_func()
    
    async def _safe_node_execution(self, node_func: callable, state: ReactorState, node_name: str) -> ReactorState:
        """Safe node execution with state preservation."""
        try:
            # Validate state before processing
            StateValidator.validate_state_type(state)
            StateValidator.validate_required_attributes(state)
            
            # Execute node
            result_state = await node_func(state)
            
            # Validate result
            StateValidator.validate_state_type(result_state)
            return result_state
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Node {node_name} failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M1 Node {node_name} - {e}")
            print(f"   → Returning original state with error metadata")
            # Return original state with error metadata
            StateAttributeManager.ensure_preprocessing_metadata(state)
            state.preprocessing_metadata[f'{node_name}_error'] = str(e)
            return state
    
    def _create_fallback_workunit(self, state: ReactorState) -> ReactorState:
        """Create fallback WorkUnit for complete failure scenarios."""
        print(f"🔄 EXECUTING FALLBACK: M1 WorkUnit Creation - Creating fallback WorkUnit")
        try:
            # Get the best available query text
            query_text = StateAttributeManager.get_current_query_text(state)
            
            # Create fallback WorkUnit
            fallback_workunit = WorkUnit(
                parent_query_id=state.original_query.id,
                text=query_text,
                is_subquestion=False,
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                trace=state.original_query.trace
            )
            
            # Clear any existing workunits and add fallback
            state.workunits = []
            state.add_workunit(fallback_workunit)
            
            # Add fallback metadata
            StateAttributeManager.ensure_preprocessing_metadata(state)
            state.preprocessing_metadata['fallback_used'] = True
            state.preprocessing_metadata['fallback_reason'] = 'Complete module failure'
            
            return state
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Even fallback WorkUnit creation failed: {e}")
            # Last resort - return state as-is
            return state
    
    def _log_llm_call(self, operation: str, prompt_length: int, success: bool, timing_ms: float = None) -> None:
        """Log LLM call details with timing information."""
        status = "SUCCESS" if success else "FAILED"
        timing_info = f" ({timing_ms:.2f}ms)" if timing_ms else ""
        self.logger.info(f"[{self.module_code}] LLM {operation}: {status}, prompt: {prompt_length} chars{timing_info}")
    
    def _log_state_transition(self, from_node: str, to_node: str, state_changes: Dict[str, Any]) -> None:
        """Log state transitions and attribute changes."""
        changes_summary = ", ".join([f"{k}={v}" for k, v in state_changes.items()])
        self.logger.debug(f"[{self.module_code}] {from_node} -> {to_node}: {changes_summary}")
    
    def _log_fallback_activation(self, operation: str, reason: str, fallback_action: str) -> None:
        """Log fallback behavior activation."""
        self.logger.warning(f"[{self.module_code}] FALLBACK {operation}: {reason} -> {fallback_action}")
        print(f"🔄 FALLBACK TRIGGERED: M1 {operation} - {reason}")
        print(f"   → {fallback_action}")
    
    def _log_processing_summary(self, state: ReactorState) -> None:
        """Log summary statistics for completed processing."""
        try:
            query_text = StateAttributeManager.get_current_query_text(state)
            workunit_count = len(state.workunits)
            
            # Check for preprocessing metadata
            metadata = getattr(state, 'preprocessing_metadata', {})
            operations = list(metadata.keys())
            
            # Check for fallback usage
            fallback_used = metadata.get('fallback_used', False)
            fallback_info = " (FALLBACK)" if fallback_used else ""
            
            self.logger.info(f"[{self.module_code}] SUMMARY: '{query_text[:30]}...' -> {workunit_count} WorkUnits, "
                           f"operations: {operations}{fallback_info}")
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Failed to log processing summary: {e}")
    
    def test_helper_methods(self, test_history: List[HistoryTurn]) -> Dict[str, str]:
        """Test method to verify helper methods work correctly."""
        try:
            # Test conversation context formatting
            context_formatted = self._format_conversation_context(test_history)
            
            # Test entity extraction
            entities = self._extract_entities_from_history(test_history)
            
            # Test fallback methods
            test_query = "What is it and how does this work?"
            normalized = self._fallback_normalize(test_query)
            resolved = self._fallback_resolve_references(test_query, test_history)
            decomposed = self._fallback_decompose("What is Python vs JavaScript?")
            
            return {
                "context_formatting": f"✓ Formatted {len(test_history)} turns",
                "entity_extraction": f"✓ Found {len(entities)} entities: {entities[:3]}",
                "fallback_normalize": f"✓ '{test_query}' -> '{normalized}'",
                "fallback_resolve": f"✓ Resolved: '{resolved[:50]}...'",
                "fallback_decompose": f"✓ Decomposed into {len(decomposed)} parts",
                "status": "All helper methods working correctly"
            }
        except Exception as e:
            return {
                "error": f"Helper methods test failed: {str(e)}",
                "status": "Failed"
            }
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests of all modernized components."""
        test_results = {}
        
        try:
            # Test 1: LLM Factory
            test_results["llm_factory"] = await self.test_structured_llm_factory()
            
            # Test 2: Pydantic Models
            test_results["pydantic_models"] = self.test_pydantic_models()
            
            # Test 3: Create a mock ReactorState for testing
            from ..models.core import UserQuery
            from uuid import uuid4
            
            mock_query = UserQuery(
                user_id=uuid4(),
                conversation_id=uuid4(),
                id=uuid4(),
                text="What is Python programming?",
                timestamp=1234567890
            )
            
            mock_state = ReactorState(original_query=mock_query)
            
            # Test 4: State Management
            test_results["state_management"] = self.test_state_management(mock_state)
            
            # Test 5: Helper Methods (create mock history)
            mock_history = [
                HistoryTurn(role=Role.user, text="Tell me about programming", timestamp=1234567880),
                HistoryTurn(role=Role.assistant, text="Programming is the process of creating software", timestamp=1234567885)
            ]
            test_results["helper_methods"] = self.test_helper_methods(mock_history)
            
            # Overall status
            all_passed = all(result.get("status", "").endswith("correctly") for result in test_results.values())
            test_results["overall_status"] = "ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"
            
            return test_results
            
        except Exception as e:
            return {
                "error": f"Comprehensive test failed: {str(e)}",
                "overall_status": "CRITICAL FAILURE"
            }
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for query preprocessing with error handling."""
        try:
            workflow = StateGraph(ReactorState)
            
            # Add processing nodes (all use modernized implementations)
            workflow.add_node("normalize_query", self._normalize_query_node)
            workflow.add_node("resolve_references", self._resolve_references_node)
            workflow.add_node("decompose_query", self._decompose_query_node)
            workflow.add_node("create_workunits", self._create_workunits_node)
            
            # Define workflow edges with proper error propagation
            workflow.add_edge("normalize_query", "resolve_references")
            workflow.add_edge("resolve_references", "decompose_query")
            workflow.add_edge("decompose_query", "create_workunits")
            workflow.add_edge("create_workunits", END)
            
            # Set entry point
            workflow.set_entry_point("normalize_query")
            
            # Compile the graph without checkpointer to avoid serialization issues
            self.graph = workflow.compile()
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Failed to build LangGraph workflow: {e}")
            raise
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute with comprehensive error handling and proper history management."""
        self._update_state_module(state)
        
        try:
            # Debug: Check initial state type
            self.logger.debug(f"[{self.module_code}] Initial state type: {type(state)}")
            
            # Initialize state safely
            ReactorStateExtensions.initialize_m1_attributes(state)
            ReactorStateExtensions.ensure_history_management(state)
            
            # Reset loop counters on first entry to M1
            if not getattr(state, '_m1_entered', False):
                state.reset_loop_counters()
                state._m1_entered = True
            
            # Get current query text (prioritizing clarified_query from M0)
            query_text = StateAttributeManager.get_current_query_text(state)
            
            self._log_execution_start(state, f"Processing query: {query_text[:50]}...")
            
            # Execute the LangGraph workflow
            thread_config = {
                "configurable": {
                    "thread_id": str(uuid4())
                }
            }
            
            self.logger.debug(f"[{self.module_code}] About to invoke LangGraph with state type: {type(state)}")
            result_state = await self.graph.ainvoke(state, config=thread_config)
            self.logger.debug(f"[{self.module_code}] LangGraph returned state type: {type(result_state)}")
            
            # Add current query to history if needed (avoiding duplication)
            if getattr(result_state, '_needs_history_update', False):
                current_query_text = StateAttributeManager.get_current_query_text(result_state)
                history_turn = HistoryTurn(
                    role=Role.user,
                    text=current_query_text,
                    timestamp=result_state.original_query.timestamp,
                    locale=result_state.original_query.locale
                )
                result_state.add_history_turn(history_turn)
                delattr(result_state, '_needs_history_update')  # Clean up temporary flag
            
            # Validate final result
            if not result_state.workunits:
                self.logger.warning(f"[{self.module_code}] No WorkUnits created, using fallback")
                return self._create_fallback_workunit(state)
            
            # Log processing summary
            self._log_processing_summary(result_state)
            self._log_execution_end(result_state, f"Created {len(result_state.workunits)} work units")
            return result_state
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Complete module failure: {e}")
            
            # Try to run decomposition directly before falling back completely
            try:
                self.logger.info(f"[{self.module_code}] Attempting direct decomposition as recovery...")
                
                # Initialize state properly
                ReactorStateExtensions.initialize_m1_attributes(state)
                state.processing_query = StateAttributeManager.get_current_query_text(state)
                
                # Try decomposition directly
                decomp_result = await self._decompose_query_node(state)
                
                # Create WorkUnits from decomposition
                final_result = await self._create_workunits_node(decomp_result)
                
                self.logger.info(f"[{self.module_code}] Direct decomposition recovery successful!")
                return final_result
                
            except Exception as recovery_e:
                self.logger.error(f"[{self.module_code}] Recovery attempt failed: {recovery_e}")
                
                # Ensure we have a proper ReactorState object
                if not isinstance(state, ReactorState):
                    self.logger.error(f"[{self.module_code}] State is not ReactorState: {type(state)}")
                    # Try to recover by creating a new state
                    try:
                        if isinstance(state, dict) and 'original_query' in state:
                            state = ReactorState(original_query=state['original_query'])
                        else:
                            # Last resort - return original state
                            return state
                    except:
                        return state
                
                return self._create_fallback_workunit(state)
    
    async def _normalize_query_node(self, state: ReactorState) -> ReactorState:
        """Modernized normalization node with structured output."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in normalization node")
            # This shouldn't happen, but let's handle it gracefully
            return state
        
        # Validate and prepare state
        StateValidator.validate_state_type(state)
        StateAttributeManager.ensure_preprocessing_metadata(state)
        
        # Get the query text to normalize (use processing_query if set, otherwise get current query)
        query_text = StateAttributeManager.safe_get_attribute(state, 'processing_query', 
                                                             StateAttributeManager.get_current_query_text(state))
        
        try:
            # Create structured LLM (like M0)
            normalization_llm = StructuredLLMFactory.create_normalization_llm()
            
            # Get prompt from configuration
            prompt = self._get_prompt("m1_normalization", 
                "Normalize the query text by fixing formatting, encoding, and standardizing punctuation.")
            
            full_prompt = f"""{prompt}

<query>
{query_text}
</query>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            import time
            start_time = time.time()
            
            # Log the input prompt for review
            self.logger.info(f"[{self.module_code}] NORMALIZATION INPUT:\n{full_prompt}")
            
            result: QueryNormalizationOutput = await normalization_llm.ainvoke(full_prompt)
            timing_ms = (time.time() - start_time) * 1000
            
            # Log the output for review
            self.logger.info(f"[{self.module_code}] NORMALIZATION OUTPUT: {result.to_dict()}")
            
            # Log successful LLM call
            self._log_llm_call("normalization", len(full_prompt), True, timing_ms)
            
            # Update state safely
            StateAttributeManager.safe_set_attribute(state, 'processing_query', result.normalized_text)
            norm_dict = result.to_dict()
            # Handle None values
            if norm_dict.get('changes_made') is None:
                norm_dict['changes_made'] = []
            state.preprocessing_metadata['normalization'] = norm_dict
            
            # Log state transition
            self._log_state_transition("normalization", "reference_resolution", 
                                     {"processing_query": result.normalized_text[:30] + "..."})
            
            return state
            
        except Exception as e:
            # Log fallback activation
            self._log_fallback_activation("normalization", str(e), "simple text processing")
            
            # Robust fallback processing
            normalized = self._fallback_normalize(query_text)
            StateAttributeManager.safe_set_attribute(state, 'processing_query', normalized)
            state.preprocessing_metadata['normalization'] = {
                'normalized_text': normalized,
                'changes_made': ['fallback_normalization'],
                'confidence': 0.5
            }
            return state
    
    async def _resolve_references_node(self, state: ReactorState) -> ReactorState:
        """Modernized reference resolution node with proper conversation context."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in reference resolution node")
            return state
        
        # Validate and prepare state
        StateValidator.validate_state_type(state)
        StateAttributeManager.ensure_preprocessing_metadata(state)
        
        # Get current processing query
        query_text = StateAttributeManager.safe_get_attribute(state, 'processing_query', 
                                                             StateAttributeManager.get_current_query_text(state))
        
        # Check if reference resolution is enabled
        if not self._get_config("memory.enable_in_m1", True):
            return state
        
        # Get relevant conversation context (excluding current query)
        conversation_context = StateAttributeManager.get_conversation_context(state, max_turns=3)
        
        try:
            # Create structured LLM (like M0)
            resolution_llm = StructuredLLMFactory.create_resolution_llm()
            
            # Get prompt from configuration
            prompt = self._get_prompt("m1_reference_resolution",
                "Resolve pronouns and references in the query using conversation history.")
            
            # Format conversation context for LLM (always include history section)
            if conversation_context:
                history_context = self._format_conversation_context(conversation_context)
            else:
                history_context = "No previous conversation history."
            
            full_prompt = f"""{prompt}

<history>
{history_context}
</history>

<current_query>
{query_text}
</current_query>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            # Log the input prompt for review
            self.logger.info(f"[{self.module_code}] REFERENCE_RESOLUTION INPUT:\n{full_prompt}")
            
            result: ReferenceResolutionOutput = await resolution_llm.ainvoke(full_prompt)
            
            # Log the output for review
            self.logger.info(f"[{self.module_code}] REFERENCE_RESOLUTION OUTPUT: {result.to_dict()}")
            
            # Update state safely
            StateAttributeManager.safe_set_attribute(state, 'processing_query', result.resolved_text)
            res_dict = result.to_dict()
            # Handle None values
            if res_dict.get('resolutions') is None:
                res_dict['resolutions'] = {}
            state.preprocessing_metadata['reference_resolution'] = res_dict
            
            return state
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Reference resolution failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M1 Reference Resolution - {e}")
            print(f"   → Using enhanced fallback reference resolution")
            # Robust fallback processing
            resolved = self._fallback_resolve_references(query_text, conversation_context)
            StateAttributeManager.safe_set_attribute(state, 'processing_query', resolved)
            state.preprocessing_metadata['reference_resolution'] = {
                'resolved_text': resolved,
                'resolutions': {},
                'confidence': 0.5
            }
            return state
    
    async def _decompose_query_node(self, state: ReactorState) -> ReactorState:
        """Modernized decomposition node with conversation context awareness."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in decomposition node")
            return state
        
        # Validate and prepare state
        StateValidator.validate_state_type(state)
        StateAttributeManager.ensure_preprocessing_metadata(state)
        
        # Get current processing query
        query_text = StateAttributeManager.safe_get_attribute(state, 'processing_query', 
                                                             StateAttributeManager.get_current_query_text(state))
        
        # Check if decomposition is enabled
        if not self._get_config("qp.enable_decomposition", True):
            # Store single query for workunit creation
            StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', [query_text])
            return state
        
        try:
            # Create structured LLM (like M0)
            decomposition_llm = StructuredLLMFactory.create_decomposition_llm()
            
            # Get conversation context for better decomposition decisions
            conversation_context = StateAttributeManager.get_conversation_context(state, max_turns=2)
            self.logger.info(f"[{self.module_code}] CONVERSATION CONTEXT: Found {len(conversation_context)} turns")
            
            # Get prompt from configuration
            prompt = self._get_prompt("m1_decomposition",
                "Analyze if this query should be broken down into simpler sub-questions.")
            
            # Include conversation context if available
            context_section = ""
            if conversation_context:
                history_context = self._format_conversation_context(conversation_context)
                context_section = f"""
<history>
{history_context}
</history>
"""
                self.logger.info(f"[{self.module_code}] ADDED HISTORY SECTION with {len(conversation_context)} turns")
            else:
                self.logger.info(f"[{self.module_code}] NO CONVERSATION CONTEXT - history section will be empty")
            
            full_prompt = f"""{prompt}

{context_section}
<current_query>
{query_text}
</current_query>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            # Log the input prompt for review
            self.logger.info(f"[{self.module_code}] DECOMPOSITION INPUT:\n{full_prompt}")
            
            result: QueryDecompositionOutput = await decomposition_llm.ainvoke(full_prompt)
            
            # Log the output for review
            self.logger.info(f"[{self.module_code}] DECOMPOSITION OUTPUT: {result.to_dict()}")
            
            # Store decomposition results
            sub_questions = result.sub_questions or []
            if result.should_decompose and sub_questions:
                decomposed_queries = sub_questions
            else:
                # Always ensure we have at least one query (the original)
                decomposed_queries = [query_text]
            
            StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', decomposed_queries)
            
            # Store decomposition metadata including multi-hop flag
            decomp_dict = result.to_dict()
            # Handle None values
            if decomp_dict.get('sub_questions') is None:
                decomp_dict['sub_questions'] = decomposed_queries
            
            # Add multi-hop flag to state for downstream processing
            StateAttributeManager.safe_set_attribute(state, 'is_multihop_query', result.is_multihop)
            
            state.preprocessing_metadata['decomposition'] = decomp_dict
            
            return state
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Decomposition failed, using fallback: {e}")
            # Robust fallback processing - still try to use LLM for better results
            self.logger.warning(f"[{self.module_code}] Decomposition LLM failed, trying simple LLM call: {e}")
            
            try:
                # Try a simpler LLM call without structured output
                simple_prompt = f"""Analyze this query for decomposition and multi-hop reasoning:

Query: {query_text}

Is this a multi-hop question that requires sequential reasoning steps? 
Should it be decomposed into sub-questions?

Respond with JSON: {{"should_decompose": true/false, "sub_questions": ["q1", "q2"], "is_multihop": true/false, "reasoning": "explanation"}}"""
                
                response = await self._call_llm(simple_prompt)
                import json
                response_data = json.loads(response)
                
                sub_questions = response_data.get('sub_questions', [])
                decomposed_queries = sub_questions if sub_questions else [query_text]
                StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', decomposed_queries)
                StateAttributeManager.safe_set_attribute(state, 'is_multihop_query', response_data.get('is_multihop', False))
                
                state.preprocessing_metadata['decomposition'] = {
                    'should_decompose': response_data.get('should_decompose', False),
                    'sub_questions': decomposed_queries,
                    'is_multihop': response_data.get('is_multihop', False),
                    'reasoning': response_data.get('reasoning', 'Fallback LLM decomposition'),
                    'confidence': 0.7
                }
                
            except Exception as fallback_e:
                self.logger.warning(f"[{self.module_code}] Even fallback LLM failed, using pattern matching: {fallback_e}")
                print(f"🔄 FALLBACK TRIGGERED: M1 Query Decomposition (Last Resort) - {fallback_e}")
                print(f"   → Using pattern matching decomposition")
                # Last resort: pattern matching
                sub_queries = self._fallback_decompose(query_text)
                decomposed_queries = sub_queries if sub_queries else [query_text]
                StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', decomposed_queries)
                
                # Use pattern-based multi-hop detection as last resort
                is_multihop = self._detect_multihop_fallback(query_text)
                StateAttributeManager.safe_set_attribute(state, 'is_multihop_query', is_multihop)
                
                state.preprocessing_metadata['decomposition'] = {
                    'should_decompose': len(sub_queries) > 1,
                    'sub_questions': decomposed_queries,
                    'is_multihop': is_multihop,
                    'reasoning': 'Pattern-based fallback decomposition',
                    'confidence': 0.3
                }
            return state
    
    async def _create_workunits_node(self, state: ReactorState) -> ReactorState:
        """Updated WorkUnit creation node with modernized compatibility."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in create workunits node")
            return state
        
        # Validate state
        StateValidator.validate_state_type(state)
        
        # Get decomposed queries safely
        decomposed_queries = StateAttributeManager.safe_get_attribute(
            state, 'decomposed_queries', [StateAttributeManager.get_current_query_text(state)]
        )
        
        workunits = []
        for i, query_text in enumerate(decomposed_queries):
            workunit = WorkUnit(
                parent_query_id=state.original_query.id,
                text=query_text,
                is_subquestion=len(decomposed_queries) > 1,
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                trace=state.original_query.trace,
                priority=i
            )
            workunits.append(workunit)
        
        # Add WorkUnits to state
        for workunit in workunits:
            state.add_workunit(workunit)
        
        return state
    
    def _format_history_for_context(self, history: List[HistoryTurn]) -> str:
        """Format conversation history for LLM context."""
        if not history:
            return "No previous conversation history."
        
        formatted_history = []
        for turn in history[-3:]:  # Only use last 3 turns
            role = "User" if turn.role.value == "user" else "Assistant"
            formatted_history.append(f"{role}: {turn.text}")
        
        return "\n".join(formatted_history)
    
    def _format_conversation_context(self, history: List[HistoryTurn]) -> str:
        """Format conversation history for LLM context, focusing on recent relevant turns."""
        if not history:
            return "No previous conversation history available."
        
        formatted_turns = []
        for turn in history:
            role = "User" if turn.role.value == "user" else "Assistant"
            # Include timestamp for context if available
            timestamp_info = f" ({turn.timestamp})" if hasattr(turn, 'timestamp') and turn.timestamp else ""
            formatted_turns.append(f"{role}{timestamp_info}: {turn.text}")
        
        return "\n".join(formatted_turns)
    
    def _fallback_normalize(self, query_text: str) -> str:
        """Enhanced fallback normalization with better text processing."""
        print(f"🔄 EXECUTING FALLBACK: M1 Query Normalization - Using text processing fallback")
        import re
        
        # Basic text cleaning
        normalized = query_text.strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        normalized = normalized.replace('？', '?').replace('！', '!')  # Unicode punctuation
        
        # Fix common encoding issues
        normalized = normalized.replace('"', '"').replace('"', '"')  # Smart quotes
        normalized = normalized.replace(''', "'").replace(''', "'")  # Smart apostrophes
        
        return normalized
    
    def _fallback_resolve_references(self, query_text: str, history: List[HistoryTurn]) -> str:
        """Enhanced fallback reference resolution with context analysis."""
        print(f"🔄 EXECUTING FALLBACK: M1 Reference Resolution - Using context analysis fallback")
        import re
        
        if not history:
            return query_text
        
        resolved = query_text
        
        # Extract entities from recent history
        entities = self._extract_entities_from_history(history)
        
        if entities:
            # Replace common pronouns with most recent relevant entity
            for pronoun in ['it', 'this', 'that', 'they', 'them']:
                pattern = rf'\b{pronoun}\b'
                if re.search(pattern, resolved, re.IGNORECASE) and entities:
                    resolved = re.sub(pattern, entities[0], resolved, flags=re.IGNORECASE)
                    break
        
        return resolved
    
    def _extract_subjects_from_history(self, history: List[HistoryTurn]) -> List[str]:
        """Extract potential subjects from conversation history."""
        subjects = []
        
        for turn in reversed(history):
            if turn.role == Role.assistant:
                words = turn.text.split()
                for word in words:
                    if (word[0].isupper() and len(word) > 1 and 
                        word.lower() not in ['this', 'that', 'the', 'a', 'an']):
                        subjects.append(word)
                        break
        
        return subjects
    
    def _extract_entities_from_history(self, history: List[HistoryTurn]) -> List[str]:
        """Enhanced entity extraction for better reference resolution."""
        entities = []
        
        for turn in reversed(history):
            words = turn.text.split()
            for word in words:
                # Look for capitalized words that might be entities
                if (word[0].isupper() and len(word) > 2 and 
                    word.lower() not in ['this', 'that', 'the', 'a', 'an', 'and', 'or', 'but']):
                    entities.append(word)
                    if len(entities) >= 3:  # Limit to top 3 entities
                        break
            if entities:
                break
        
        return entities
    
    def _fallback_decompose(self, query_text: str) -> List[str]:
        """Enhanced fallback decomposition with improved pattern recognition."""
        print(f"🔄 EXECUTING FALLBACK: M1 Query Decomposition - Using pattern recognition fallback")
        import re
        
        # Pattern 1: Comparison queries
        comparison_patterns = [
            r'\b(?:vs|versus|compared to|difference between)\b',
            r'\b(?:better|worse|faster|slower)\s+than\b'
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, query_text, re.IGNORECASE):
                parts = re.split(pattern, query_text, flags=re.IGNORECASE)
                if len(parts) >= 2:
                    return [f"What is {parts[0].strip()}?", f"What is {parts[1].strip()}?"]
        
        # Pattern 2: Multiple questions
        if query_text.count('?') > 1:
            questions = [q.strip() + '?' for q in query_text.split('?') if q.strip()]
            return questions if len(questions) > 1 else []
        
        # Pattern 3: Conjunction queries
        conjunction_patterns = [r'\band\b', r'\bor\b', r'\bplus\b']
        for pattern in conjunction_patterns:
            if re.search(pattern, query_text, re.IGNORECASE):
                parts = re.split(pattern, query_text, flags=re.IGNORECASE)
                if len(parts) == 2:
                    return [parts[0].strip() + "?", parts[1].strip() + "?"]
        
        return []  # No decomposition needed
    
    def _detect_multihop_fallback(self, query_text: str) -> bool:
        """Detect if a query requires multi-hop reasoning using pattern matching."""
        import re
        
        # Patterns that often indicate multi-hop questions
        multihop_patterns = [
            r'\bmost\s+\w+(?:\s+\w+)*\s+of\s+all\s+time\b',  # "most decorated [word(s)] of all time"
            r'\bfirst\s+\w+\s+to\b',  # "first person to"
            r'\blargest\s+\w+\s+in\b',  # "largest company in"
            r'\bbest\s+\w+\s+for\b',  # "best language for"
            r'\bwho\s+\w+\s+the\s+\w+\s+that\b',  # "who created the language that"
            r'\bwhere\s+did\s+the\s+\w+\s+\w+\b',  # "where did the most famous"
            r'\bwhat\s+\w+\s+the\s+\w+\s+that\b',  # "what language the framework that"
            r'\bwhere\s+did\s+the\s+most\b',  # "where did the most"
            r'\bwho\s+is\s+the\s+most\b',  # "who is the most"
            r'\bwhat\s+did\s+the\s+\w+est\b',  # "what did the biggest"
        ]
        
        for pattern in multihop_patterns:
            if re.search(pattern, query_text, re.IGNORECASE):
                return True
        
        # Check for superlative + possessive constructions
        if re.search(r'\b(most|largest|biggest|smallest|first|last)\s+\w+.*\b(their|its|his|her)\b', 
                     query_text, re.IGNORECASE):
            return True
        
        # Check for "the most/best/largest + adjective + noun + question about them"
        if re.search(r'\bthe\s+(most|best|largest|biggest|smallest|first|last)\s+\w+.*\b(get|go|study|work|live)\b', 
                     query_text, re.IGNORECASE):
            return True
        
        # Specific pattern for "Where did the [superlative] [noun] [verb]"
        if re.search(r'\bwhere\s+did\s+the\s+(most|best|largest|biggest|smallest|first|last)\s+\w+', 
                     query_text, re.IGNORECASE):
            return True
        
        return False


# Module instance
query_preprocessor_langgraph = QueryPreprocessorLangGraph()


# LangGraph node function for integration
async def query_preprocessor_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M1 - Query Preprocessor (LangGraph implementation)."""
    return await query_preprocessor_langgraph.execute(state)