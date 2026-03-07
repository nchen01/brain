"""Tests for ReactorState model based on specification requirements."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.models.state import ReactorState, RouterStats
from src.models.core import UserQuery, WorkUnit, EvidenceItem, Provenance, SourceType, HistoryTurn, Role


class TestReactorState:
    """Test ReactorState model per Requirements 1.1, 1.3, 6.1, 6.3 - state management and loop prevention."""
    
    def test_reactor_state_creation_spec_1_1(self, sample_user_query):
        """Test ReactorState creation with original query per Requirement 1.1."""
        state = ReactorState(original_query=sample_user_query)
        
        assert state.original_query == sample_user_query
        assert state.workunits == []
        assert state.evidences == []
        assert state.history == []
        assert state.loop_counters.smartretrieval_to_qp == 0
        assert state.loop_counters.answercheck_to_ac == 0
        assert state.loop_counters.answercheck_to_qp == 0
    
    def test_reactor_state_add_workunit_spec_2_4(self, sample_user_query, sample_workunit):
        """Test adding WorkUnit to state per Requirement 2.4."""
        state = ReactorState(original_query=sample_user_query)
        
        state.add_workunit(sample_workunit)
        
        assert len(state.workunits) == 1
        assert state.workunits[0] == sample_workunit
    
    def test_reactor_state_add_evidence_spec_3_4(self, sample_user_query, sample_evidence_item):
        """Test adding EvidenceItem to state per Requirement 3.4."""
        state = ReactorState(original_query=sample_user_query)
        
        state.add_evidence(sample_evidence_item)
        
        assert len(state.evidences) == 1
        assert state.evidences[0] == sample_evidence_item
    
    def test_reactor_state_add_history_turn_spec_8_1(self, sample_user_query):
        """Test adding conversation history per Requirement 8.1."""
        state = ReactorState(original_query=sample_user_query)
        
        history_turn = HistoryTurn(
            role=Role.user,
            text="What is Python?",
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        state.add_history_turn(history_turn)
        
        assert len(state.history) == 1
        assert state.history[0] == history_turn
    
    def test_reactor_state_loop_counter_management_spec_6_1(self, sample_user_query):
        """Test loop counter management per Requirement 6.1."""
        state = ReactorState(original_query=sample_user_query)
        
        # Test increment loop counter
        state.increment_loop_counter("smartretrieval_to_qp")
        assert state.loop_counters["smartretrieval_to_qp"] == 1
        
        # Test multiple increments
        state.increment_loop_counter("smartretrieval_to_qp")
        assert state.loop_counters["smartretrieval_to_qp"] == 2
        
        # Test different counter
        state.increment_loop_counter("answercheck_to_ac")
        assert state.loop_counters["answercheck_to_ac"] == 1
        assert state.loop_counters["smartretrieval_to_qp"] == 2
    
    def test_reactor_state_reset_loop_counters_spec_6_3(self, sample_user_query):
        """Test loop counter reset per Requirement 6.3."""
        state = ReactorState(original_query=sample_user_query)
        
        # Set some counters
        state.increment_loop_counter("smartretrieval_to_qp")
        state.increment_loop_counter("answercheck_to_ac")
        assert state.loop_counters["smartretrieval_to_qp"] == 1
        assert state.loop_counters["answercheck_to_ac"] == 1
        
        # Reset counters
        state.reset_loop_counters()
        assert state.loop_counters.smartretrieval_to_qp == 0
        assert state.loop_counters.answercheck_to_ac == 0
        assert state.loop_counters.answercheck_to_qp == 0
    
    def test_reactor_state_get_recent_history_spec_8_1(self, sample_user_query):
        """Test getting recent conversation history per Requirement 8.1."""
        state = ReactorState(original_query=sample_user_query)
        
        # Add multiple history turns
        for i in range(5):
            turn = HistoryTurn(
                role=Role.user if i % 2 == 0 else Role.assistant,
                text=f"Message {i}",
                timestamp=int(datetime.now().timestamp() * 1000) + i
            )
            state.add_history_turn(turn)
        
        # Get recent history (last 3)
        recent = state.get_recent_history(3)
        assert len(recent) == 3
        assert recent[0].text == "Message 2"  # Should be in chronological order
        assert recent[1].text == "Message 3"
        assert recent[2].text == "Message 4"
    
    def test_reactor_state_get_recent_history_empty_spec_8_1(self, sample_user_query):
        """Test getting recent history when empty."""
        state = ReactorState(original_query=sample_user_query)
        
        recent = state.get_recent_history(3)
        assert recent == []
    
    def test_reactor_state_set_current_module_spec_8_2(self, sample_user_query):
        """Test setting current module for logging per Requirement 8.2."""
        state = ReactorState(original_query=sample_user_query)
        
        state.set_current_module("M1")
        assert state.current_module == "M1"
        
        state.set_current_module("M2")
        assert state.current_module == "M2"
    
    def test_reactor_state_thread_safety_spec_1_3(self, sample_user_query):
        """Test that ReactorState maintains isolation per Requirement 1.3."""
        # Create two separate states
        state1 = ReactorState(original_query=sample_user_query)
        
        query2 = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            id=uuid4(),
            text="What is Java?",
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        state2 = ReactorState(original_query=query2)
        
        # Modify state1
        state1.increment_loop_counter("test_counter")
        state1.set_current_module("M1")
        
        # Verify state2 is unaffected
        assert state2.loop_counters.get("test_counter", 0) == 0
        assert state2.current_module is None
        assert state2.original_query.text == "What is Java?"


class TestRouterStats:
    """Test RouterStats model for routing statistics tracking."""
    
    def test_router_stats_creation(self):
        """Test RouterStats creation and initialization."""
        stats = RouterStats()
        
        assert stats.total_workunits == 0
        assert stats.parallel_routes == 0
        assert stats.path_selections == {}
        assert stats.routing_time_ms == 0.0
    
    def test_router_stats_path_tracking(self):
        """Test RouterStats path selection tracking."""
        stats = RouterStats()
        
        # Simulate path selections
        stats.path_selections["P1"] = 3
        stats.path_selections["P2"] = 2
        stats.path_selections["P3"] = 1
        
        assert stats.path_selections["P1"] == 3
        assert stats.path_selections["P2"] == 2
        assert stats.path_selections["P3"] == 1
    
    def test_router_stats_timing_tracking(self):
        """Test RouterStats timing information."""
        stats = RouterStats()
        
        stats.routing_time_ms = 150.5
        stats.total_workunits = 2
        stats.parallel_routes = 1
        
        assert stats.routing_time_ms == 150.5
        assert stats.total_workunits == 2
        assert stats.parallel_routes == 1