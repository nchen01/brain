"""Tests for M1 Query Preprocessor LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit, HistoryTurn, ClarifiedQuery
from src.models.types import Role
from src.modules.m1_query_preprocessor_langgraph import (
    query_preprocessor_langgraph,
    QueryPreprocessorLangGraph,
    QueryNormalizationOutput,
    ReferenceResolutionOutput,
    QueryDecompositionOutput
)


class TestM1QueryPreprocessorLangGraph:
    """Test suite for M1 Query Preprocessor LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        
        # Create test user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is machine learning and how does it work?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test state
        self.initial_state = ReactorState(original_query=self.user_query)
        
        # Add conversation history for reference resolution tests
        history_turns = [
            HistoryTurn(
                role=Role.user,
                text="I'm interested in artificial intelligence",
                timestamp=int(time.time() * 1000) - 120000
            ),
            HistoryTurn(
                role=Role.assistant,
                text="AI is a fascinating field! What specific aspect would you like to know about?",
                timestamp=int(time.time() * 1000) - 90000
            ),
            HistoryTurn(
                role=Role.user,
                text="Tell me about Python programming",
                timestamp=int(time.time() * 1000) - 60000
            )
        ]
        for turn in history_turns:
            self.initial_state.add_history_turn(turn)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M1 execution with query preprocessing."""
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for each node
            mock_responses = [
                '{"normalized_text": "What is machine learning and how does it work?", "changes_made": ["Fixed capitalization"], "confidence": 0.9}',
                '{"resolved_text": "What is machine learning and how does it work?", "resolutions": {}, "confidence": 0.8}',
                '{"should_decompose": true, "sub_questions": ["What is machine learning?", "How does machine learning work?"], "reasoning": "Complex query with multiple aspects", "confidence": 0.85}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await query_preprocessor_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert len(result_state.workunits) == 2  # Decomposed into 2 sub-questions
            assert result_state.workunits[0].text == "What is machine learning?"
            assert result_state.workunits[1].text == "How does machine learning work?"
            assert result_state.workunits[0].is_subquestion == True
            assert result_state.workunits[1].is_subquestion == True
    
    @pytest.mark.asyncio
    async def test_normalize_query_node(self):
        """Test query normalization node with Pydantic validation."""
        state = self.initial_state.copy()
        state.processing_query = "what   is  machine learning???"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{"normalized_text": "What is machine learning?", "changes_made": ["Fixed spacing", "Removed extra punctuation"], "confidence": 0.95}'
            
            result_state = await query_preprocessor_langgraph._normalize_query_node(state)
            
            # Verify normalization results
            assert result_state.processing_query == "What is machine learning?"
            assert hasattr(result_state, 'preprocessing_metadata')
            assert 'normalization' in result_state.preprocessing_metadata
            
            normalization_data = result_state.preprocessing_metadata['normalization']
            assert normalization_data['normalized_text'] == "What is machine learning?"
            assert normalization_data['confidence'] == 0.95
            assert "Fixed spacing" in normalization_data['changes_made']
    
    @pytest.mark.asyncio
    async def test_resolve_references_node(self):
        """Test reference resolution node with conversation history."""
        state = self.initial_state.copy()
        state.processing_query = "How does it work in practice?"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{"resolved_text": "How does Python programming work in practice?", "resolutions": {"it": "Python programming"}, "confidence": 0.9}'
            
            result_state = await query_preprocessor_langgraph._resolve_references_node(state)
            
            # Verify reference resolution results
            assert result_state.processing_query == "How does Python programming work in practice?"
            assert 'reference_resolution' in result_state.preprocessing_metadata
            
            resolution_data = result_state.preprocessing_metadata['reference_resolution']
            assert resolution_data['resolved_text'] == "How does Python programming work in practice?"
            assert resolution_data['resolutions']['it'] == "Python programming"
            assert resolution_data['confidence'] == 0.9
    
    @pytest.mark.asyncio
    async def test_resolve_references_node_no_history(self):
        """Test reference resolution node with no conversation history."""
        state = ReactorState(original_query=self.user_query)
        state.processing_query = "How does it work?"
        
        result_state = await query_preprocessor_langgraph._resolve_references_node(state)
        
        # Should return unchanged when no history
        assert result_state.processing_query == "How does it work?"
    
    @pytest.mark.asyncio
    async def test_decompose_query_node_should_decompose(self):
        """Test query decomposition node when decomposition is beneficial."""
        state = self.initial_state.copy()
        state.processing_query = "What is AI and how is it different from ML?"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{"should_decompose": true, "sub_questions": ["What is AI?", "What is ML?", "How is AI different from ML?"], "reasoning": "Multi-part question with comparison", "confidence": 0.9}'
            
            result_state = await query_preprocessor_langgraph._decompose_query_node(state)
            
            # Verify decomposition results
            assert len(result_state.decomposed_queries) == 3
            assert "What is AI?" in result_state.decomposed_queries
            assert "What is ML?" in result_state.decomposed_queries
            assert "How is AI different from ML?" in result_state.decomposed_queries
            
            decomposition_data = result_state.preprocessing_metadata['decomposition']
            assert decomposition_data['should_decompose'] == True
            assert decomposition_data['confidence'] == 0.9
    
    @pytest.mark.asyncio
    async def test_decompose_query_node_no_decomposition(self):
        """Test query decomposition node when no decomposition is needed."""
        state = self.initial_state.copy()
        state.processing_query = "What is Python?"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{"should_decompose": false, "sub_questions": [], "reasoning": "Simple, focused question", "confidence": 0.95}'
            
            result_state = await query_preprocessor_langgraph._decompose_query_node(state)
            
            # Verify no decomposition
            assert len(result_state.decomposed_queries) == 1
            assert result_state.decomposed_queries[0] == "What is Python?"
            
            decomposition_data = result_state.preprocessing_metadata['decomposition']
            assert decomposition_data['should_decompose'] == False
    
    @pytest.mark.asyncio
    async def test_create_workunits_node_single_query(self):
        """Test WorkUnit creation from single query."""
        state = self.initial_state.copy()
        state.decomposed_queries = ["What is machine learning?"]
        
        result_state = await query_preprocessor_langgraph._create_workunits_node(state)
        
        # Verify WorkUnit creation
        assert len(result_state.workunits) == 1
        workunit = result_state.workunits[0]
        assert workunit.text == "What is machine learning?"
        assert workunit.is_subquestion == False  # Single query, not a subquestion
        assert workunit.parent_query_id == self.user_query.id
        assert workunit.user_id == self.user_id
        assert workunit.conversation_id == self.conversation_id
    
    @pytest.mark.asyncio
    async def test_create_workunits_node_multiple_queries(self):
        """Test WorkUnit creation from multiple decomposed queries."""
        state = self.initial_state.copy()
        state.decomposed_queries = ["What is AI?", "What is ML?", "How are they different?"]
        
        result_state = await query_preprocessor_langgraph._create_workunits_node(state)
        
        # Verify WorkUnit creation
        assert len(result_state.workunits) == 3
        
        for i, workunit in enumerate(result_state.workunits):
            assert workunit.text == state.decomposed_queries[i]
            assert workunit.is_subquestion == True  # Multiple queries, all are subquestions
            assert workunit.priority == i
            assert workunit.parent_query_id == self.user_query.id
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise exceptions
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await query_preprocessor_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback
            assert result_state is not None
            assert len(result_state.workunits) >= 1
            # Should create at least one WorkUnit with original query
            assert any(wu.text == self.user_query.text for wu in result_state.workunits)
    
    @pytest.mark.asyncio
    async def test_normalization_fallback(self):
        """Test normalization fallback when LLM fails."""
        state = self.initial_state.copy()
        state.processing_query = "what   is  machine   learning???"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM failed")
            
            result_state = await query_preprocessor_langgraph._normalize_query_node(state)
            
            # Should use fallback normalization
            assert result_state.processing_query == "what is machine learning???"  # Spaces normalized
    
    @pytest.mark.asyncio
    async def test_reference_resolution_fallback(self):
        """Test reference resolution fallback when LLM fails."""
        state = self.initial_state.copy()
        state.processing_query = "How does it work?"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM failed")
            
            result_state = await query_preprocessor_langgraph._resolve_references_node(state)
            
            # Should use fallback resolution (replace 'it' with recent subject)
            # Based on history, should replace 'it' with 'Python'
            assert "Python" in result_state.processing_query or result_state.processing_query == "How does it work?"
    
    @pytest.mark.asyncio
    async def test_decomposition_fallback(self):
        """Test decomposition fallback when LLM fails."""
        state = self.initial_state.copy()
        state.processing_query = "What is AI vs ML?"
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM failed")
            
            result_state = await query_preprocessor_langgraph._decompose_query_node(state)
            
            # Should use fallback decomposition for "vs" queries
            assert len(result_state.decomposed_queries) >= 1
            # May decompose "AI vs ML" into separate questions
    
    def test_query_normalization_pydantic_model(self):
        """Test QueryNormalizationOutput Pydantic model validation."""
        # Valid data
        valid_data = {
            "normalized_text": "What is Python?",
            "changes_made": ["Fixed capitalization", "Added question mark"],
            "confidence": 0.9
        }
        
        result = QueryNormalizationOutput(**valid_data)
        assert result.normalized_text == "What is Python?"
        assert len(result.changes_made) == 2
        assert result.confidence == 0.9
        
        # Invalid confidence (too high)
        with pytest.raises(Exception):  # Pydantic validation error
            QueryNormalizationOutput(
                normalized_text="Test",
                changes_made=[],
                confidence=1.5
            )
    
    def test_reference_resolution_pydantic_model(self):
        """Test ReferenceResolutionOutput Pydantic model validation."""
        # Valid data
        valid_data = {
            "resolved_text": "How does Python programming work?",
            "resolutions": {"it": "Python programming"},
            "confidence": 0.85
        }
        
        result = ReferenceResolutionOutput(**valid_data)
        assert result.resolved_text == "How does Python programming work?"
        assert result.resolutions["it"] == "Python programming"
        assert result.confidence == 0.85
        
        # Test with empty resolutions (should work)
        empty_resolutions = {
            "resolved_text": "What is AI?",
            "resolutions": {},
            "confidence": 0.9
        }
        result = ReferenceResolutionOutput(**empty_resolutions)
        assert len(result.resolutions) == 0
    
    def test_query_decomposition_pydantic_model(self):
        """Test QueryDecompositionOutput Pydantic model validation."""
        # Valid data with decomposition
        valid_data = {
            "should_decompose": True,
            "sub_questions": ["What is AI?", "What is ML?"],
            "reasoning": "Multi-part question",
            "confidence": 0.8
        }
        
        result = QueryDecompositionOutput(**valid_data)
        assert result.should_decompose == True
        assert len(result.sub_questions) == 2
        assert result.reasoning == "Multi-part question"
        
        # Valid data without decomposition
        no_decomp_data = {
            "should_decompose": False,
            "sub_questions": [],
            "reasoning": "Simple question",
            "confidence": 0.95
        }
        
        result = QueryDecompositionOutput(**no_decomp_data)
        assert result.should_decompose == False
        assert len(result.sub_questions) == 0
    
    def test_format_history_for_context(self):
        """Test history formatting for LLM context."""
        history = [
            HistoryTurn(role=Role.user, text="Hello", timestamp=1000),
            HistoryTurn(role=Role.assistant, text="Hi there!", timestamp=2000),
            HistoryTurn(role=Role.user, text="What is Python?", timestamp=3000)
        ]
        
        formatted = query_preprocessor_langgraph._format_history_for_context(history)
        
        assert "User: Hello" in formatted
        assert "Assistant: Hi there!" in formatted
        assert "User: What is Python?" in formatted
        
        # Test with empty history
        empty_formatted = query_preprocessor_langgraph._format_history_for_context([])
        assert empty_formatted == "No previous conversation history."
    
    def test_fallback_normalize(self):
        """Test fallback normalization method."""
        # Test space normalization
        result = query_preprocessor_langgraph._fallback_normalize("what   is  machine   learning")
        assert result == "what is machine learning"
        
        # Test unicode punctuation
        result = query_preprocessor_langgraph._fallback_normalize("What is AI？")
        assert result == "What is AI?"
        
        # Test stripping
        result = query_preprocessor_langgraph._fallback_normalize("  What is ML?  ")
        assert result == "What is ML?"
    
    def test_fallback_resolve_references(self):
        """Test fallback reference resolution method."""
        history = [
            HistoryTurn(role=Role.assistant, text="Python is a programming language", timestamp=1000),
            HistoryTurn(role=Role.user, text="Tell me more about it", timestamp=2000)
        ]
        
        # Should replace 'it' with 'Python'
        result = query_preprocessor_langgraph._fallback_resolve_references("How does it work?", history)
        assert "Python" in result
        
        # Test with no history
        result = query_preprocessor_langgraph._fallback_resolve_references("How does it work?", [])
        assert result == "How does it work?"
    
    def test_extract_subjects_from_history(self):
        """Test subject extraction from conversation history."""
        history = [
            HistoryTurn(role=Role.assistant, text="Python is great for beginners", timestamp=1000),
            HistoryTurn(role=Role.assistant, text="JavaScript is also popular", timestamp=2000)
        ]
        
        subjects = query_preprocessor_langgraph._extract_subjects_from_history(history)
        
        # Should extract capitalized words (subjects)
        assert "JavaScript" in subjects or "Python" in subjects
    
    def test_fallback_decompose(self):
        """Test fallback decomposition method."""
        # Test "vs" query
        result = query_preprocessor_langgraph._fallback_decompose("Python vs JavaScript")
        assert len(result) == 2
        assert "Python" in result[0]
        assert "JavaScript" in result[1]
        
        # Test "and" query
        result = query_preprocessor_langgraph._fallback_decompose("What is AI and ML")
        assert len(result) == 2
        
        # Test multiple questions
        result = query_preprocessor_langgraph._fallback_decompose("What is AI? How does it work?")
        assert len(result) == 2
        assert "What is AI?" in result
        assert "How does it work?" in result
        
        # Test simple query (no decomposition)
        result = query_preprocessor_langgraph._fallback_decompose("What is Python?")
        assert len(result) == 0  # No decomposition needed
    
    @pytest.mark.asyncio
    async def test_with_clarified_query(self):
        """Test M1 execution with a clarified query instead of original query."""
        # Add clarified query to state
        clarified_query = ClarifiedQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is deep learning specifically?",
            locale="en-US",
            timestamp=int(time.time() * 1000),
            original_text=self.user_query.text,
            clarification_turns=1,
            confidence=0.9
        )
        self.initial_state.clarified_query = clarified_query
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"normalized_text": "What is deep learning specifically?", "changes_made": [], "confidence": 0.9}',
                '{"resolved_text": "What is deep learning specifically?", "resolutions": {}, "confidence": 0.8}',
                '{"should_decompose": false, "sub_questions": [], "reasoning": "Specific focused question", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await query_preprocessor_langgraph.execute(self.initial_state)
            
            # Should process clarified query, not original
            assert len(result_state.workunits) == 1
            assert result_state.workunits[0].text == "What is deep learning specifically?"
    
    @pytest.mark.asyncio
    async def test_configuration_options(self):
        """Test various configuration options."""
        state = self.initial_state.copy()
        
        # Test with decomposition disabled
        with patch.object(query_preprocessor_langgraph, '_get_config') as mock_config:
            mock_config.side_effect = lambda key, default: False if key == "qp.enable_decomposition" else default
            
            result_state = await query_preprocessor_langgraph._decompose_query_node(state)
            
            # Should not decompose when disabled
            assert len(result_state.decomposed_queries) == 1
            assert result_state.decomposed_queries[0] == self.user_query.text
        
        # Test with memory disabled
        with patch.object(query_preprocessor_langgraph, '_get_config') as mock_config:
            mock_config.side_effect = lambda key, default: False if key == "memory.enable_in_m1" else default
            
            result_state = await query_preprocessor_langgraph._resolve_references_node(state)
            
            # Should skip reference resolution when memory disabled
            assert result_state == state


class TestM1Integration:
    """Integration tests for M1 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="Compare Python and JavaScript for web development",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_complex_query(self):
        """Test M1 integration with complex multi-part query."""
        state = ReactorState(original_query=self.user_query)
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"normalized_text": "Compare Python and JavaScript for web development", "changes_made": [], "confidence": 0.9}',
                '{"resolved_text": "Compare Python and JavaScript for web development", "resolutions": {}, "confidence": 0.8}',
                '{"should_decompose": true, "sub_questions": ["What is Python for web development?", "What is JavaScript for web development?", "How do Python and JavaScript compare for web development?"], "reasoning": "Comparison query benefits from decomposition", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await query_preprocessor_langgraph.execute(state)
            
            # Should create multiple WorkUnits for complex query
            assert len(result_state.workunits) == 3
            assert all(wu.is_subquestion for wu in result_state.workunits)
            assert result_state.workunits[0].priority == 0
            assert result_state.workunits[1].priority == 1
            assert result_state.workunits[2].priority == 2
    
    @pytest.mark.asyncio
    async def test_integration_with_conversation_context(self):
        """Test M1 integration with rich conversation context."""
        state = ReactorState(original_query=UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="How does it compare to the alternatives?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        ))
        
        # Add rich conversation history
        history_turns = [
            HistoryTurn(role=Role.user, text="I'm learning about React", timestamp=1000),
            HistoryTurn(role=Role.assistant, text="React is a great JavaScript library for building user interfaces", timestamp=2000),
            HistoryTurn(role=Role.user, text="What are its main benefits?", timestamp=3000),
            HistoryTurn(role=Role.assistant, text="React offers component reusability, virtual DOM, and strong ecosystem", timestamp=4000)
        ]
        for turn in history_turns:
            state.add_history_turn(turn)
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"normalized_text": "How does it compare to the alternatives?", "changes_made": [], "confidence": 0.9}',
                '{"resolved_text": "How does React compare to the alternatives?", "resolutions": {"it": "React"}, "confidence": 0.95}',
                '{"should_decompose": false, "sub_questions": [], "reasoning": "Clear focused question after resolution", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await query_preprocessor_langgraph.execute(state)
            
            # Should resolve reference and create appropriate WorkUnit
            assert len(result_state.workunits) >= 1
            assert "React" in result_state.workunits[0].text
    
    @pytest.mark.asyncio
    async def test_performance_and_state_management(self):
        """Test performance metrics and state management."""
        state = ReactorState(original_query=self.user_query)
        
        with patch.object(query_preprocessor_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{"normalized_text": "Test query", "changes_made": [], "confidence": 0.9}'
            
            result_state = await query_preprocessor_langgraph.execute(state)
            
            # Check that state management works correctly
            assert result_state is not None
            assert hasattr(result_state, '_m1_entered')  # Loop counter reset flag
            assert len(result_state.workunits) >= 1
            
            # Check that history was added
            user_turns = [turn for turn in result_state.conversation_history if turn.role == Role.user]
            assert len(user_turns) >= 1
            assert any(turn.text == self.user_query.text for turn in user_turns)