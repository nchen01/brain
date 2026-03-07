"""Tests for history update functionality in the workflow."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, HistoryTurn, ClarifiedQuery, Answer
from src.models.types import Role
from src.workflow.graph import QueryReactorGraph


class TestHistoryUpdates:
    """Test suite for workflow history update functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = QueryReactorGraph()
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        
        # Create a sample user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is the capital of France?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create initial state
        self.initial_state = ReactorState(original_query=self.user_query)
    
    def test_add_user_query_to_history(self):
        """Test adding user query to conversation history."""
        # Execute the history initialization
        updated_state = self.graph._add_user_query_to_history(self.initial_state)
        
        # Verify history was updated
        assert len(updated_state.history) == 1
        
        # Verify the history turn details
        history_turn = updated_state.history[0]
        assert history_turn.role == Role.user
        assert history_turn.text == "What is the capital of France?"
        assert history_turn.timestamp == self.user_query.timestamp
        assert history_turn.locale == "en-US"
    
    def test_add_assistant_response_to_history(self):
        """Test adding assistant response to conversation history."""
        # Start with user query in history
        state_with_user = self.graph._add_user_query_to_history(self.initial_state)
        
        # Add assistant response
        response_text = "The capital of France is Paris."
        updated_state = self.graph._add_assistant_response_to_history(
            state_with_user, response_text
        )
        
        # Verify history has both turns
        assert len(updated_state.history) == 2
        
        # Verify assistant turn
        assistant_turn = updated_state.history[1]
        assert assistant_turn.role == Role.assistant
        assert assistant_turn.text == response_text
        assert assistant_turn.locale == "en-US"
        assert assistant_turn.timestamp > 0  # Should have a valid timestamp
    
    def test_add_system_message_to_history(self):
        """Test adding system message to conversation history."""
        # Start with existing history
        state_with_history = self.graph._add_user_query_to_history(self.initial_state)
        
        # Add system message
        system_message = "Processing your request..."
        updated_state = self.graph._add_system_message_to_history(
            state_with_history, system_message
        )
        
        # Verify history has both turns
        assert len(updated_state.history) == 2
        
        # Verify system turn
        system_turn = updated_state.history[1]
        assert system_turn.role == Role.system
        assert system_turn.text == system_message
        assert system_turn.locale == "en-US"
        assert system_turn.timestamp > 0
    
    def test_initialize_history_node(self):
        """Test the initialize_history_node wrapper function."""
        # Execute the node function
        result_state = self.graph._initialize_history_node(self.initial_state)
        
        # Verify it calls the underlying history function
        assert len(result_state.history) == 1
        assert result_state.history[0].role == Role.user
        assert result_state.history[0].text == "What is the capital of France?"
    
    @patch('src.workflow.graph.qa_with_human')
    @pytest.mark.asyncio
    async def test_m0_with_history_clarification(self, mock_qa_with_human):
        """Test M0 wrapper with clarification question history tracking."""
        # Mock M0 returning a clarified query (indicating clarification occurred)
        clarified_query = ClarifiedQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is the capital of France and its main landmarks?",
            locale="en-US",
            timestamp=int(time.time() * 1000),
            original_text=self.user_query.text,
            clarification_turns=1,
            confidence=0.9
        )
        
        mock_result_state = ReactorState(original_query=self.user_query)
        mock_result_state.clarified_query = clarified_query
        mock_qa_with_human.return_value = mock_result_state
        
        # Execute M0 with history tracking
        result_state = await self.graph._m0_with_history(self.initial_state)
        
        # Verify M0 was called
        mock_qa_with_human.assert_called_once_with(self.initial_state)
        
        # Verify clarification was added to history (when clarification_turns > 0)
        if result_state.clarified_query and result_state.clarified_query.clarification_turns > 0:
            assert len(result_state.history) == 1
            assert result_state.history[0].role == Role.assistant
            assert "Clarification needed:" in result_state.history[0].text
    
    @patch('src.workflow.graph.qa_with_human')
    @pytest.mark.asyncio
    async def test_m0_with_history_no_clarification(self, mock_qa_with_human):
        """Test M0 wrapper when no clarification is needed."""
        # Mock M0 returning without clarification (clarification_turns = 0)
        clarified_query = ClarifiedQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text=self.user_query.text,  # Same as original
            locale="en-US",
            timestamp=int(time.time() * 1000),
            original_text=self.user_query.text,
            clarification_turns=0,  # No clarification needed
            confidence=0.9
        )
        
        mock_result_state = ReactorState(original_query=self.user_query)
        mock_result_state.clarified_query = clarified_query
        mock_qa_with_human.return_value = mock_result_state
        
        # Execute M0 with history tracking
        result_state = await self.graph._m0_with_history(self.initial_state)
        
        # Verify M0 was called
        mock_qa_with_human.assert_called_once_with(self.initial_state)
        
        # Verify no history was added (no clarification)
        assert len(result_state.history) == 0
    
    @patch('src.workflow.graph.interaction_answer')
    @pytest.mark.asyncio
    async def test_m12_with_history_final_answer(self, mock_interaction_answer):
        """Test M12 wrapper with final answer history tracking."""
        # Mock M12 returning a final answer
        mock_final_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="The capital of France is Paris, known for its iconic landmarks.",
            confidence=0.95,
            citations=[]
        )
        
        mock_result_state = ReactorState(original_query=self.user_query)
        mock_result_state.final_answer = mock_final_answer
        mock_interaction_answer.return_value = mock_result_state
        
        # Execute M12 with history tracking
        result_state = await self.graph._m12_with_history(self.initial_state)
        
        # Verify M12 was called
        mock_interaction_answer.assert_called_once_with(self.initial_state)
        
        # Verify final answer was added to history
        assert len(result_state.history) == 1
        assert result_state.history[0].role == Role.assistant
        assert result_state.history[0].text == "The capital of France is Paris, known for its iconic landmarks."
    
    def test_empty_response_handling(self):
        """Test that empty responses don't create history entries."""
        # Test empty assistant response
        updated_state = self.graph._add_assistant_response_to_history(
            self.initial_state, ""
        )
        assert len(updated_state.history) == 0
        
        # Test None assistant response
        updated_state = self.graph._add_assistant_response_to_history(
            self.initial_state, None
        )
        assert len(updated_state.history) == 0
        
        # Test empty system message
        updated_state = self.graph._add_system_message_to_history(
            self.initial_state, ""
        )
        assert len(updated_state.history) == 0
    
    def test_history_ordering(self):
        """Test that history maintains correct chronological order."""
        state = self.initial_state
        
        # Add user query
        state = self.graph._add_user_query_to_history(state)
        
        # Add system message
        state = self.graph._add_system_message_to_history(state, "Processing...")
        
        # Add assistant response
        state = self.graph._add_assistant_response_to_history(state, "Here's your answer.")
        
        # Verify order and count
        assert len(state.history) == 3
        assert state.history[0].role == Role.user
        assert state.history[1].role == Role.system
        assert state.history[2].role == Role.assistant
        
        # Verify timestamps are in order (allowing for same millisecond)
        assert state.history[0].timestamp <= state.history[1].timestamp
        assert state.history[1].timestamp <= state.history[2].timestamp
    
    def test_history_with_minimal_query(self):
        """Test history handling with minimal query text."""
        # Create a minimal user query for ReactorState (minimum 1 character)
        minimal_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="?",  # Minimum valid text
            timestamp=int(time.time() * 1000)
        )
        minimal_state = ReactorState(original_query=minimal_query)
        
        # Try to add user query to history
        updated_state = self.graph._add_user_query_to_history(minimal_state)
        
        # Should add the minimal query
        assert len(updated_state.history) == 1
        assert updated_state.history[0].text == "?"
        
        # Assistant response should still work
        updated_state = self.graph._add_assistant_response_to_history(
            updated_state, "Test response"
        )
        assert len(updated_state.history) == 2
        assert updated_state.history[1].text == "Test response"
    
    def test_get_recent_history_integration(self):
        """Test that history updates work with get_recent_history method."""
        state = self.initial_state
        
        # Add multiple history turns
        state = self.graph._add_user_query_to_history(state)
        state = self.graph._add_assistant_response_to_history(state, "Response 1")
        state = self.graph._add_user_query_to_history(state)  # Simulate follow-up
        state = self.graph._add_assistant_response_to_history(state, "Response 2")
        
        # Test get_recent_history
        recent_2 = state.get_recent_history(2)
        assert len(recent_2) == 2
        assert recent_2[0].text == "What is the capital of France?"  # Most recent user query
        assert recent_2[1].text == "Response 2"  # Most recent assistant response
        
        # Test get all history
        all_history = state.get_recent_history(10)
        assert len(all_history) == 4


class TestWorkflowIntegration:
    """Integration tests for history updates in the full workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = QueryReactorGraph()
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        
        # Create a sample user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is machine learning?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    def test_graph_has_history_components(self):
        """Test that the graph has all history-related components."""
        # Verify the graph has the history methods
        assert hasattr(self.graph, '_initialize_history_node')
        assert hasattr(self.graph, '_m0_with_history')
        assert hasattr(self.graph, '_m12_with_history')
        assert hasattr(self.graph, '_add_user_query_to_history')
        assert hasattr(self.graph, '_add_assistant_response_to_history')
        assert hasattr(self.graph, '_add_system_message_to_history')
        
        # Verify the graph is compiled (basic smoke test)
        assert self.graph.graph is not None
    
    def test_graph_visualization_includes_history(self):
        """Test that graph visualization reflects history initialization."""
        visualization = self.graph.get_graph_visualization()
        
        # Should be a string representation
        assert isinstance(visualization, str)
        assert len(visualization) > 0
        
        # Should contain workflow information
        assert "QueryReactor Workflow Graph" in visualization
    
    @pytest.mark.asyncio
    async def test_initialize_history_node_integration(self):
        """Test the initialize_history_node in isolation."""
        initial_state = ReactorState(original_query=self.user_query)
        
        # Execute the initialize history node
        result_state = self.graph._initialize_history_node(initial_state)
        
        # Verify history was initialized with user query
        assert len(result_state.history) == 1
        assert result_state.history[0].role == Role.user
        assert result_state.history[0].text == "What is machine learning?"
        assert result_state.history[0].timestamp == self.user_query.timestamp
        assert result_state.history[0].locale == "en-US"
    
    @patch('src.workflow.graph.qa_with_human')
    @patch('src.workflow.graph.interaction_answer')
    @pytest.mark.asyncio
    async def test_end_to_end_history_flow(self, mock_interaction_answer, mock_qa_with_human):
        """Test history tracking through a simulated end-to-end flow."""
        # Create initial state
        initial_state = ReactorState(original_query=self.user_query)
        
        # Step 1: Initialize history
        state_after_init = self.graph._initialize_history_node(initial_state)
        assert len(state_after_init.history) == 1
        assert state_after_init.history[0].role == Role.user
        
        # Step 2: Mock M0 with clarification
        clarified_query = ClarifiedQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is machine learning and how does it work?",
            locale="en-US",
            timestamp=int(time.time() * 1000),
            original_text=self.user_query.text,
            clarification_turns=1,
            confidence=0.9
        )
        
        mock_state_after_m0 = ReactorState(original_query=self.user_query)
        mock_state_after_m0.history = state_after_init.history.copy()
        mock_state_after_m0.clarified_query = clarified_query
        mock_qa_with_human.return_value = mock_state_after_m0
        
        state_after_m0 = await self.graph._m0_with_history(state_after_init)
        
        # Should have user query + clarification
        assert len(state_after_m0.history) == 2
        assert state_after_m0.history[0].role == Role.user
        assert state_after_m0.history[1].role == Role.assistant
        assert "Clarification needed:" in state_after_m0.history[1].text
        
        # Step 3: Mock M12 with final answer
        final_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="Machine learning is a subset of AI that enables computers to learn from data.",
            confidence=0.95,
            citations=[]
        )
        
        mock_state_after_m12 = ReactorState(original_query=self.user_query)
        mock_state_after_m12.history = state_after_m0.history.copy()
        mock_state_after_m12.final_answer = final_answer
        mock_interaction_answer.return_value = mock_state_after_m12
        
        final_state = await self.graph._m12_with_history(state_after_m0)
        
        # Should have user query + clarification + final answer
        assert len(final_state.history) == 3
        assert final_state.history[0].role == Role.user
        assert final_state.history[1].role == Role.assistant  # Clarification
        assert final_state.history[2].role == Role.assistant  # Final answer
        assert "Machine learning is a subset of AI" in final_state.history[2].text
        
        # Verify chronological order
        assert final_state.history[0].timestamp <= final_state.history[1].timestamp
        assert final_state.history[1].timestamp <= final_state.history[2].timestamp
    
    def test_history_persistence_across_state_updates(self):
        """Test that history persists correctly as state is updated."""
        state = ReactorState(original_query=self.user_query)
        
        # Add multiple history entries
        state = self.graph._add_user_query_to_history(state)
        state = self.graph._add_system_message_to_history(state, "Processing your request...")
        state = self.graph._add_assistant_response_to_history(state, "I need more information.")
        state = self.graph._add_assistant_response_to_history(state, "Here's your answer.")
        
        # Verify all entries are preserved
        assert len(state.history) == 4
        
        # Verify order and content
        assert state.history[0].role == Role.user
        assert state.history[0].text == "What is machine learning?"
        
        assert state.history[1].role == Role.system
        assert state.history[1].text == "Processing your request..."
        
        assert state.history[2].role == Role.assistant
        assert state.history[2].text == "I need more information."
        
        assert state.history[3].role == Role.assistant
        assert state.history[3].text == "Here's your answer."
        
        # Test get_recent_history functionality
        recent_2 = state.get_recent_history(2)
        assert len(recent_2) == 2
        assert recent_2[0].text == "I need more information."
        assert recent_2[1].text == "Here's your answer."