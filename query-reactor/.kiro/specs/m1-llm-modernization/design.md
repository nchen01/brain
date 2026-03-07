# Design Document

## Overview

The M1 Query Preprocessor modernization will transform the module from using deprecated JSON parsing to the proven structured output pattern successfully implemented in M0. This design addresses the core architectural inconsistencies causing LLM response parsing failures, implements robust state management, and ensures reliable error handling with proper fallback behavior. The modernized M1 will maintain full compatibility with the existing QueryReactor system while providing significantly improved reliability and maintainability.

## Architecture

### Current vs. Target Architecture

**Current M1 Architecture (Problematic):**
```python
# Raw JSON parsing approach
response = await self._call_llm(prompt)  # Returns string
parsed_data = json.loads(response)       # Manual parsing
output = QueryNormalizationOutput(**parsed_data)  # Manual validation
```

**Target M1 Architecture (Like M0):**
```python
# Structured output approach
llm = ChatOpenAI().with_structured_output(QueryNormalizationOutput)
result = await llm.ainvoke(prompt)  # Returns validated Pydantic object directly
```

### Modernization Strategy

The modernization follows a **three-phase approach**:

1. **Phase 1: LLM Integration Modernization** - Replace JSON parsing with structured output
2. **Phase 2: State Management Fixes** - Implement robust ReactorState attribute handling
3. **Phase 3: Error Handling Enhancement** - Add comprehensive fallback mechanisms

### Key Architectural Changes

**LLM Integration Layer:**
- Replace `_call_llm()` + `json.loads()` + `Pydantic(**data)` pattern
- Implement `ChatOpenAI().with_structured_output(Model)` pattern like M0
- Use model_manager for consistent model selection and parameter optimization
- Eliminate manual JSON parsing and validation steps

**State Management Layer:**
- Implement safe attribute initialization for ReactorState
- Add proper attribute existence checking with graceful fallbacks
- Ensure type consistency throughout the processing pipeline
- Fix dynamic attribute access patterns

**Error Handling Layer:**
- Implement structured exception handling for each processing node
- Add comprehensive fallback processing for all LLM operations
- Ensure processing pipeline continuation even with partial failures
- Maintain proper logging and observability throughout

## Components and Interfaces

### Modernized LLM Integration Components

**Structured LLM Factory:**
```python
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
        return raw_llm.with_structured_output(QueryNormalizationOutput)
    
    @staticmethod
    def create_resolution_llm() -> ChatOpenAI:
        """Create LLM for reference resolution with structured output."""
        # Similar pattern for ReferenceResolutionOutput
    
    @staticmethod
    def create_decomposition_llm() -> ChatOpenAI:
        """Create LLM for query decomposition with structured output."""
        # Similar pattern for QueryDecompositionOutput
```

**Updated Pydantic Models (V2 Compatible):**
```python
class QueryNormalizationOutput(BaseModel):
    """Modernized Pydantic model with v2 compatibility."""
    normalized_text: str = Field(description="Normalized query text")
    changes_made: List[str] = Field(default_factory=list, description="List of normalization changes")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in normalization")
    
    # V2 methods (replacing deprecated ones)
    def to_dict(self) -> Dict[str, Any]:
        """Replace deprecated dict() method."""
        return self.model_dump()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QueryNormalizationOutput':
        """Replace deprecated parse_raw() method."""
        return cls.model_validate_json(json_str)
```

### Enhanced State Management Components

**ReactorState Attribute Manager:**
```python
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
```

**State Validation Layer:**
```python
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
```

### Modernized Processing Nodes

**Normalization Node (Structured Output):**
```python
async def _normalize_query_node(self, state: ReactorState) -> ReactorState:
    """Modernized normalization node with structured output."""
    # Validate and prepare state
    StateValidator.validate_state_type(state)
    StateAttributeManager.ensure_preprocessing_metadata(state)
    
    # Get current query text (prioritizing clarified_query from M0)
    query_text = StateAttributeManager.get_current_query_text(state)
    
    try:
        # Create structured LLM (like M0)
        normalization_llm = StructuredLLMFactory.create_normalization_llm()
        
        # Get prompt from configuration
        prompt = self._get_prompt("m1_normalization", 
            "Normalize the query text by fixing formatting, encoding, and standardizing punctuation.")
        
        full_prompt = f"""{prompt}

<query>
{query_text}
</query>

Return a JSON object with normalized_text, changes_made, and confidence fields."""
        
        # Call structured LLM - returns validated Pydantic object directly
        result: QueryNormalizationOutput = await normalization_llm.ainvoke(full_prompt)
        
        # Update state safely
        StateAttributeManager.safe_set_attribute(state, 'processing_query', result.normalized_text)
        state.preprocessing_metadata['normalization'] = result.to_dict()
        
        return state
        
    except Exception as e:
        self.logger.warning(f"[{self.module_code}] Normalization failed, using fallback: {e}")
        # Robust fallback processing
        normalized = self._fallback_normalize(query_text)
        StateAttributeManager.safe_set_attribute(state, 'processing_query', normalized)
        state.preprocessing_metadata['normalization'] = {
            'normalized_text': normalized,
            'changes_made': ['fallback_normalization'],
            'confidence': 0.5
        }
        return state
```

**Reference Resolution Node (Enhanced with History Context):**
```python
async def _resolve_references_node(self, state: ReactorState) -> ReactorState:
    """Modernized reference resolution node with proper conversation context."""
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
    
    if not conversation_context:
        # No history available, skip reference resolution
        return state
    
    try:
        # Create structured LLM (like M0)
        resolution_llm = StructuredLLMFactory.create_resolution_llm()
        
        # Get prompt from configuration
        prompt = self._get_prompt("m1_reference_resolution",
            "Resolve pronouns and references in the query using conversation history.")
        
        # Format conversation context for LLM
        history_context = self._format_conversation_context(conversation_context)
        
        full_prompt = f"""{prompt}

<conversation_history>
{history_context}
</conversation_history>

<current_query>
{query_text}
</current_query>

Analyze the current query and resolve any pronouns or references using the conversation history.
Return a JSON object with resolved_text, resolutions map, and confidence."""
        
        # Call structured LLM - returns validated Pydantic object directly
        result: ReferenceResolutionOutput = await resolution_llm.ainvoke(full_prompt)
        
        # Update state safely
        StateAttributeManager.safe_set_attribute(state, 'processing_query', result.resolved_text)
        state.preprocessing_metadata['reference_resolution'] = result.to_dict()
        
        return state
        
    except Exception as e:
        self.logger.warning(f"[{self.module_code}] Reference resolution failed, using fallback: {e}")
        # Robust fallback processing
        resolved = self._fallback_resolve_references(query_text, conversation_context)
        StateAttributeManager.safe_set_attribute(state, 'processing_query', resolved)
        state.preprocessing_metadata['reference_resolution'] = {
            'resolved_text': resolved,
            'resolutions': {},
            'confidence': 0.5
        }
        return state

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
```

**Decomposition Node (Enhanced with Context Awareness):**
```python
async def _decompose_query_node(self, state: ReactorState) -> ReactorState:
    """Modernized decomposition node with conversation context awareness."""
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
        
        # Get prompt from configuration
        prompt = self._get_prompt("m1_decomposition",
            "Analyze if this query should be broken down into simpler sub-questions.")
        
        # Include conversation context if available
        context_section = ""
        if conversation_context:
            history_context = self._format_conversation_context(conversation_context)
            context_section = f"""
<conversation_context>
{history_context}
</conversation_context>
"""
        
        full_prompt = f"""{prompt}

{context_section}
<current_query>
{query_text}
</current_query>

Consider the query complexity and conversation context. Determine if decomposition would improve answer quality.
Return a JSON object with should_decompose, sub_questions list, reasoning, and confidence."""
        
        # Call structured LLM - returns validated Pydantic object directly
        result: QueryDecompositionOutput = await decomposition_llm.ainvoke(full_prompt)
        
        # Store decomposition results
        if result.should_decompose and result.sub_questions:
            decomposed_queries = result.sub_questions
        else:
            decomposed_queries = [query_text]
        
        StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', decomposed_queries)
        state.preprocessing_metadata['decomposition'] = result.to_dict()
        
        return state
        
    except Exception as e:
        self.logger.warning(f"[{self.module_code}] Decomposition failed, using fallback: {e}")
        # Robust fallback processing
        sub_queries = self._fallback_decompose(query_text)
        decomposed_queries = sub_queries if sub_queries else [query_text]
        StateAttributeManager.safe_set_attribute(state, 'decomposed_queries', decomposed_queries)
        state.preprocessing_metadata['decomposition'] = {
            'should_decompose': len(sub_queries) > 1,
            'sub_questions': sub_queries,
            'reasoning': 'Fallback decomposition using pattern matching',
            'confidence': 0.5
        }
        return state
```

## Data Models

### Updated Pydantic Models (V2 Compatible)

**Base Model with Modern Methods:**
```python
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
```

**Updated Output Models:**
```python
class QueryNormalizationOutput(ModernBaseModel):
    """Updated normalization output with modern Pydantic patterns."""
    normalized_text: str = Field(description="Normalized query text")
    changes_made: List[str] = Field(default_factory=list, description="List of normalization changes")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in normalization")

class ReferenceResolutionOutput(ModernBaseModel):
    """Updated reference resolution output with modern Pydantic patterns."""
    resolved_text: str = Field(description="Text with resolved references")
    resolutions: Dict[str, str] = Field(default_factory=dict, description="Map of resolved references")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in resolution")

class QueryDecompositionOutput(ModernBaseModel):
    """Updated decomposition output with modern Pydantic patterns."""
    should_decompose: bool = Field(description="Whether query should be decomposed")
    sub_questions: List[str] = Field(default_factory=list, description="Generated sub-questions")
    reasoning: str = Field(description="Reasoning for decomposition decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in decomposition")
```

### Enhanced State Management Models

**ReactorState Extensions:**
```python
# Extensions to ReactorState for better M1 integration
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
```

**Processing Context Model:**
```python
class M1ProcessingContext(BaseModel):
    """Context model for M1 processing state."""
    current_node: str = Field(description="Current processing node")
    processing_query: str = Field(description="Query text being processed")
    fallback_used: bool = Field(default=False, description="Whether fallback processing was used")
    error_count: int = Field(default=0, description="Number of errors encountered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
```

## Error Handling

### Comprehensive Error Handling Strategy

**Three-Tier Error Handling:**

1. **Tier 1: LLM Call Level** - Handle individual LLM failures
2. **Tier 2: Node Level** - Handle processing node failures  
3. **Tier 3: Module Level** - Handle complete module failures

**Tier 1: LLM Call Error Handling:**
```python
async def _safe_llm_call(self, llm: ChatOpenAI, prompt: str, fallback_func: callable) -> Any:
    """Safe LLM call with automatic fallback."""
    try:
        result = await llm.ainvoke(prompt)
        return result
    except ValidationError as e:
        self.logger.warning(f"[{self.module_code}] Pydantic validation failed: {e}")
        return fallback_func()
    except Exception as e:
        self.logger.error(f"[{self.module_code}] LLM call failed: {e}")
        return fallback_func()
```

**Tier 2: Node Level Error Handling:**
```python
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
        # Return original state with error metadata
        StateAttributeManager.ensure_preprocessing_metadata(state)
        state.preprocessing_metadata[f'{node_name}_error'] = str(e)
        return state
```

**Tier 3: Module Level Error Handling:**
```python
async def execute(self, state: ReactorState) -> ReactorState:
    """Execute with comprehensive error handling and proper history management."""
    try:
        # Initialize state safely
        ReactorStateExtensions.initialize_m1_attributes(state)
        ReactorStateExtensions.ensure_history_management(state)
        
        # Reset loop counters on first entry to M1
        if not getattr(state, '_m1_entered', False):
            state.reset_loop_counters()
            state._m1_entered = True
        
        # Execute LangGraph workflow
        result_state = await self.graph.ainvoke(state, config=thread_config)
        
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
        
        return result_state
        
    except Exception as e:
        self.logger.error(f"[{self.module_code}] Complete module failure: {e}")
        return self._create_fallback_workunit(state)
```

### Fallback Processing Mechanisms

**Normalization Fallback:**
```python
def _fallback_normalize(self, query_text: str) -> str:
    """Enhanced fallback normalization with better text processing."""
    import re
    
    # Basic text cleaning
    normalized = query_text.strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
    normalized = normalized.replace('？', '?').replace('！', '!')  # Unicode punctuation
    
    # Fix common encoding issues
    normalized = normalized.replace('"', '"').replace('"', '"')  # Smart quotes
    normalized = normalized.replace(''', "'").replace(''', "'")  # Smart apostrophes
    
    return normalized
```

**Reference Resolution Fallback:**
```python
def _fallback_resolve_references(self, query_text: str, history: List[HistoryTurn]) -> str:
    """Enhanced fallback reference resolution with context analysis."""
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
```

**Decomposition Fallback:**
```python
def _fallback_decompose(self, query_text: str) -> List[str]:
    """Enhanced fallback decomposition with pattern recognition."""
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
```

## Testing Strategy

### Modernized Test Architecture

**Test Structure Alignment:**
```python
class TestM1Modernized:
    """Test suite for modernized M1 with structured output."""
    
    @pytest.fixture
    def mock_structured_llm(self):
        """Mock structured LLM that returns Pydantic objects directly."""
        mock_llm = AsyncMock()
        
        # Mock normalization response
        mock_llm.ainvoke.side_effect = [
            QueryNormalizationOutput(
                normalized_text="What is Python programming?",
                changes_made=["Fixed capitalization"],
                confidence=0.9
            ),
            ReferenceResolutionOutput(
                resolved_text="What is Python programming?",
                resolutions={},
                confidence=0.8
            ),
            QueryDecompositionOutput(
                should_decompose=False,
                sub_questions=[],
                reasoning="Single focused question",
                confidence=0.85
            )
        ]
        
        return mock_llm
```

**Integration Test Strategy:**
```python
async def test_m1_with_structured_output(mock_structured_llm):
    """Test M1 with structured output pattern like M0."""
    # Setup
    state = create_test_reactor_state()
    
    # Mock the structured LLM factory
    with patch('src.modules.m1_query_preprocessor_langgraph.StructuredLLMFactory') as mock_factory:
        mock_factory.create_normalization_llm.return_value = mock_structured_llm
        mock_factory.create_resolution_llm.return_value = mock_structured_llm
        mock_factory.create_decomposition_llm.return_value = mock_structured_llm
        
        # Execute
        result_state = await query_preprocessor_langgraph.execute(state)
        
        # Verify
        assert len(result_state.workunits) == 1
        assert result_state.workunits[0].text == "What is Python programming?"
        assert hasattr(result_state, 'preprocessing_metadata')
        assert 'normalization' in result_state.preprocessing_metadata
```

**Fallback Behavior Testing:**
```python
async def test_m1_fallback_behavior():
    """Test that M1 handles failures gracefully with fallback processing."""
    state = create_test_reactor_state()
    
    # Mock LLM to raise exceptions
    with patch('src.modules.m1_query_preprocessor_langgraph.StructuredLLMFactory') as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = ValidationError("Mock validation error", model=QueryNormalizationOutput)
        mock_factory.create_normalization_llm.return_value = mock_llm
        
        # Execute - should not crash
        result_state = await query_preprocessor_langgraph.execute(state)
        
        # Verify fallback behavior
        assert len(result_state.workunits) == 1  # Fallback creates WorkUnit
        assert result_state.preprocessing_metadata['normalization']['changes_made'] == ['fallback_normalization']
```

### Performance and Reliability Testing

**Concurrent Processing Tests:**
```python
async def test_m1_concurrent_processing():
    """Test M1 handles concurrent requests without state interference."""
    states = [create_test_reactor_state() for _ in range(10)]
    
    # Execute concurrently
    tasks = [query_preprocessor_langgraph.execute(state) for state in states]
    results = await asyncio.gather(*tasks)
    
    # Verify isolation
    for i, result in enumerate(results):
        assert result.original_query.id == states[i].original_query.id
        assert len(result.workunits) >= 1
```

**Error Recovery Tests:**
```python
async def test_m1_error_recovery():
    """Test M1 recovers from various error conditions."""
    test_cases = [
        ("invalid_json", "Mock JSON parsing error"),
        ("validation_error", "Mock Pydantic validation error"),
        ("network_error", "Mock network timeout"),
        ("state_error", "Mock state attribute error")
    ]
    
    for error_type, error_message in test_cases:
        state = create_test_reactor_state()
        
        # Mock specific error condition
        with patch_error_condition(error_type, error_message):
            result_state = await query_preprocessor_langgraph.execute(state)
            
            # Verify graceful handling
            assert len(result_state.workunits) >= 1  # Always produces output
            assert hasattr(result_state, 'preprocessing_metadata')  # Metadata preserved
```

This design provides a comprehensive modernization strategy that addresses all the identified issues while maintaining compatibility with the existing QueryReactor system. The structured output pattern from M0 eliminates JSON parsing failures, the enhanced state management prevents attribute errors, and the robust error handling ensures reliable operation even under failure conditions.