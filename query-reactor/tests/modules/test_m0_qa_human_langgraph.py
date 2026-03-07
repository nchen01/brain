"""Tests for M0 QA Human LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, ClarifiedQuery, HistoryTurn
from src.models.types import Role
from src.modules.m0_qa_human_langgraph import (
    qa_with_human_langgraph,
    QAWithHumanLangGraph,
    ClarityResult,
    FollowupResult,
    M0State
)


class TestM0QAHumanLangGraph:
    """Test suite for M0 QA Human LangGraph implementation."""
    
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
            text="What is machine learning?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test state
        self.initial_state = ReactorState(original_query=self.user_query)
        
        # Add some conversation history
        history_turns = [
            HistoryTurn(
                role=Role.user,
                text="Hello, I have a question about AI",
                timestamp=int(time.time() * 1000) - 60000
            ),
            HistoryTurn(
                role=Role.assistant,
                text="I'd be happy to help with your AI question!",
                timestamp=int(time.time() * 1000) - 30000
            )
        ]
        for turn in history_turns:
            self.initial_state.add_history_turn(turn)
    
    @pytest.mark.asyncio
    async def test_basic_execution_clear_query(self):
        """Test basic M0 execution with a clear query."""
        with patch.object(qa_with_human_langgraph, '_call_llm') as mock_llm:
            # Mock high clarity score (no follow-up needed)
            mock_llm.return_value = '{"clarity_score": 0.9}'
            
            # Mock the structured LLM calls
            with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
                mock_clarity_result = ClarityResult(clarity_score=0.9)
                mock_llm_instance = MagicMock()
                mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_clarity_result)
                mock_openai.return_value = mock_llm_instance
                
                result_state = await qa_with_human_langgraph.execute(self.initial_state)
                
                # Verify basic execution
                assert result_state is not None
                assert result_state.clarified_query is not None
                assert result_state.clarified_query.text == self.user_query.text
                assert result_state.clarified_query.clarification_turns == 0
                assert result_state.clarified_query.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_basic_execution_unclear_query(self):
        """Test basic M0 execution with an unclear query requiring follow-up."""
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            # Mock clarity assessment (low score)
            mock_clarity_result = ClarityResult(clarity_score=0.4)
            mock_followup_result = FollowupResult(question="What specific aspect of machine learning interests you?")
            
            mock_llm_instance = MagicMock()
            mock_structured_llm = MagicMock()
            
            # Set up the structured LLM to return different results for different calls
            call_count = 0
            async def mock_ainvoke(prompt):
                nonlocal call_count
                call_count += 1
                if call_count == 1:  # First call is clarity assessment
                    return mock_clarity_result
                else:  # Second call is follow-up question
                    return mock_followup_result
            
            mock_structured_llm.ainvoke = mock_ainvoke
            mock_llm_instance.with_structured_output.return_value = mock_structured_llm
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph.execute(self.initial_state)
            
            # Verify follow-up was generated
            assert result_state is not None
            assert result_state.clarified_query is not None
            assert result_state.clarified_query.clarification_turns == 1
            assert result_state.clarified_query.confidence == 0.4
            assert "Clarification needed:" in result_state.clarified_query.text
    
    @pytest.mark.asyncio
    async def test_clarity_assessment_node(self):
        """Test clarity assessment node with Pydantic validation."""
        # Create M0 state
        m0_state = M0State(
            history="User: Hello\nAssistant: Hi there!",
            current_query="What is machine learning?",
            original_state=self.initial_state
        )
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            mock_clarity_result = ClarityResult(clarity_score=0.8)
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_clarity_result)
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph._clarity_assessment_node(m0_state)
            
            # Verify clarity assessment results
            assert result_state["clarity_score"] == 0.8
            assert result_state["needs_followup"] == False  # Above threshold (0.7)
            assert result_state["history"] == m0_state["history"]
            assert result_state["current_query"] == m0_state["current_query"]
    
    @pytest.mark.asyncio
    async def test_followup_question_node(self):
        """Test follow-up question generation node."""
        # Create M0 state that needs follow-up
        m0_state = M0State(
            history="User: Hello\nAssistant: Hi there!",
            current_query="Tell me about it",
            needs_followup=True,
            clarity_score=0.3,
            original_state=self.initial_state
        )
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            mock_followup_result = FollowupResult(question="What specific topic would you like to know about?")
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_followup_result)
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph._followup_question_node(m0_state)
            
            # Verify follow-up question was generated
            assert result_state["followup_question"] == "What specific topic would you like to know about?"
            assert result_state["needs_followup"] == True
            assert result_state["clarity_score"] == 0.3
    
    @pytest.mark.asyncio
    async def test_followup_question_node_no_followup_needed(self):
        """Test follow-up question node when no follow-up is needed."""
        # Create M0 state that doesn't need follow-up
        m0_state = M0State(
            history="User: Hello\nAssistant: Hi there!",
            current_query="What is machine learning?",
            needs_followup=False,
            clarity_score=0.9,
            original_state=self.initial_state
        )
        
        result_state = await qa_with_human_langgraph._followup_question_node(m0_state)
        
        # Should return unchanged state
        assert result_state == m0_state
        assert "followup_question" not in result_state
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            # Mock LLM to raise an exception
            mock_openai.side_effect = Exception("LLM call failed")
            
            result_state = await qa_with_human_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback
            assert result_state is not None
            assert result_state.clarified_query is not None
            assert result_state.clarified_query.confidence == 0.5  # Default fallback confidence
            assert result_state.clarified_query.clarification_turns == 1  # Fallback triggers followup
    
    @pytest.mark.asyncio
    async def test_clarity_assessment_fallback(self):
        """Test clarity assessment fallback when structured LLM fails."""
        m0_state = M0State(
            history="User: Hello",
            current_query="What is AI?",
            original_state=self.initial_state
        )
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            # Mock LLM to raise an exception
            mock_openai.side_effect = Exception("Structured LLM failed")
            
            result_state = await qa_with_human_langgraph._clarity_assessment_node(m0_state)
            
            # Should use fallback values
            assert result_state["clarity_score"] == 0.5
            assert result_state["needs_followup"] == True
    
    @pytest.mark.asyncio
    async def test_followup_question_fallback(self):
        """Test follow-up question fallback when structured LLM fails."""
        m0_state = M0State(
            history="User: Hello",
            current_query="Tell me about it",
            needs_followup=True,
            original_state=self.initial_state
        )
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            # Mock LLM to raise an exception
            mock_openai.side_effect = Exception("Structured LLM failed")
            
            result_state = await qa_with_human_langgraph._followup_question_node(m0_state)
            
            # Should use fallback question
            assert result_state["followup_question"] == "Could you provide more details about what you're looking for?"
    
    def test_clarity_result_pydantic_model(self):
        """Test ClarityResult Pydantic model validation."""
        # Valid data
        valid_data = {"clarity_score": 0.8}
        result = ClarityResult(**valid_data)
        assert result.clarity_score == 0.8
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            ClarityResult(clarity_score=1.5)
        
        # Invalid data (score too low)
        with pytest.raises(Exception):  # Pydantic validation error
            ClarityResult(clarity_score=-0.1)
    
    def test_followup_result_pydantic_model(self):
        """Test FollowupResult Pydantic model validation."""
        # Valid data
        valid_data = {"question": "What specific aspect interests you?"}
        result = FollowupResult(**valid_data)
        assert result.question == "What specific aspect interests you?"
        
        # Invalid data (empty question)
        with pytest.raises(Exception):  # Pydantic validation error
            FollowupResult(question="")
    
    def test_prepare_m0_state(self):
        """Test conversion from ReactorState to M0State."""
        m0_state = qa_with_human_langgraph._prepare_m0_state(self.initial_state)
        
        assert isinstance(m0_state, dict)
        assert "history" in m0_state
        assert "current_query" in m0_state
        assert "original_state" in m0_state
        assert m0_state["current_query"] == self.user_query.text
        assert m0_state["original_state"] == self.initial_state
    
    def test_format_history_for_xml(self):
        """Test history formatting for XML structure."""
        # Test with history
        history_xml = qa_with_human_langgraph._format_history_for_xml(self.initial_state.get_recent_history(3))
        assert "User:" in history_xml
        assert "Assistant:" in history_xml
        
        # Test with empty history
        empty_history_xml = qa_with_human_langgraph._format_history_for_xml([])
        assert empty_history_xml == "No previous conversation history."
    
    def test_convert_to_reactor_state_clear_query(self):
        """Test conversion from M0State back to ReactorState for clear query."""
        m0_result = M0State(
            history="User: Hello",
            current_query="What is AI?",
            clarity_score=0.9,
            needs_followup=False,
            original_state=self.initial_state
        )
        
        result_state = qa_with_human_langgraph._convert_to_reactor_state(m0_result, self.initial_state)
        
        assert result_state.clarified_query is not None
        assert result_state.clarified_query.text == self.user_query.text
        assert result_state.clarified_query.clarification_turns == 0
        assert result_state.clarified_query.confidence == 0.9
    
    def test_convert_to_reactor_state_unclear_query(self):
        """Test conversion from M0State back to ReactorState for unclear query."""
        m0_result = M0State(
            history="User: Hello",
            current_query="Tell me about it",
            clarity_score=0.3,
            needs_followup=True,
            followup_question="What specific topic interests you?",
            original_state=self.initial_state
        )
        
        result_state = qa_with_human_langgraph._convert_to_reactor_state(m0_result, self.initial_state)
        
        assert result_state.clarified_query is not None
        assert "Clarification needed:" in result_state.clarified_query.text
        assert result_state.clarified_query.clarification_turns == 1
        assert result_state.clarified_query.confidence == 0.3
    
    def test_route_after_clarity(self):
        """Test routing logic after clarity assessment."""
        # Test route to follow-up
        state_needs_followup = M0State(needs_followup=True)
        route = qa_with_human_langgraph._route_after_clarity(state_needs_followup)
        assert route == "followup"
        
        # Test route to end
        state_no_followup = M0State(needs_followup=False)
        route = qa_with_human_langgraph._route_after_clarity(state_no_followup)
        assert route == "end"
    
    @pytest.mark.asyncio
    async def test_different_clarity_thresholds(self):
        """Test behavior with different clarity thresholds."""
        m0_state = M0State(
            history="User: Hello",
            current_query="What is AI?",
            original_state=self.initial_state
        )
        
        # Test with different clarity scores around threshold
        test_cases = [
            (0.6, True),   # Below default threshold (0.7) - needs followup
            (0.7, True),   # At threshold (0.7 <= 0.7 = True) - needs followup
            (0.8, False),  # Above threshold (0.8 <= 0.7 = False) - no followup needed
        ]
        
        for clarity_score, should_need_followup in test_cases:
            with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
                mock_clarity_result = ClarityResult(clarity_score=clarity_score)
                mock_llm_instance = MagicMock()
                mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_clarity_result)
                mock_openai.return_value = mock_llm_instance
                
                result_state = await qa_with_human_langgraph._clarity_assessment_node(m0_state)
                
                assert result_state["clarity_score"] == clarity_score
                assert result_state["needs_followup"] == should_need_followup


class TestM0Integration:
    """Integration tests for M0 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="I need help with something",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_conversation_history(self):
        """Test M0 integration with conversation history."""
        state = ReactorState(original_query=self.user_query)
        
        # Add extensive conversation history
        for i in range(5):
            user_turn = HistoryTurn(
                role=Role.user,
                text=f"User message {i+1}",
                timestamp=int(time.time() * 1000) - (5-i) * 30000
            )
            assistant_turn = HistoryTurn(
                role=Role.assistant,
                text=f"Assistant response {i+1}",
                timestamp=int(time.time() * 1000) - (5-i) * 30000 + 15000
            )
            state.add_history_turn(user_turn)
            state.add_history_turn(assistant_turn)
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            mock_clarity_result = ClarityResult(clarity_score=0.8)
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_clarity_result)
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph.execute(state)
            
            # Should process successfully with history context
            assert result_state is not None
            assert result_state.clarified_query is not None
    
    @pytest.mark.asyncio
    async def test_integration_with_empty_state(self):
        """Test M0 behavior with minimal state."""
        minimal_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="Help",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        state = ReactorState(original_query=minimal_query)
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            mock_clarity_result = ClarityResult(clarity_score=0.2)  # Very unclear
            mock_followup_result = FollowupResult(question="What do you need help with?")
            
            mock_llm_instance = MagicMock()
            mock_structured_llm = MagicMock()
            
            call_count = 0
            async def mock_ainvoke(prompt):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_clarity_result
                else:
                    return mock_followup_result
            
            mock_structured_llm.ainvoke = mock_ainvoke
            mock_llm_instance.with_structured_output.return_value = mock_structured_llm
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph.execute(state)
            
            # Should handle minimal query and generate appropriate follow-up
            assert result_state is not None
            assert result_state.clarified_query is not None
            assert result_state.clarified_query.clarification_turns == 1
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded."""
        state = ReactorState(original_query=self.user_query)
        
        with patch('src.modules.m0_qa_human_langgraph.ChatOpenAI') as mock_openai:
            mock_clarity_result = ClarityResult(clarity_score=0.8)
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_clarity_result)
            mock_openai.return_value = mock_llm_instance
            
            result_state = await qa_with_human_langgraph.execute(state)
            
            # Check that module execution was tracked
            assert result_state is not None
            # Module should have updated the state with its execution
            # (Specific metrics depend on base module implementation)