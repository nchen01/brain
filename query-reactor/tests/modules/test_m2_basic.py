"""Basic functionality test for M2 Query Router."""

import pytest
import asyncio
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.modules.m2_query_router_langgraph import QueryRouterLangGraph


class TestM2BasicFunctionality:
    """Test M2 basic routing functionality."""
    
    @pytest.mark.asyncio
    async def test_m2_fallback_routing_works(self):
        """Test that M2 fallback routing mechanism works correctly."""
        
        # Create test state
        state = ReactorState(original_query=UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="What is Python and how does it compare to Java?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        ))
        
        # Add test WorkUnits
        workunits = [
            WorkUnit(
                parent_query_id=state.original_query.id,
                text="What is Python programming language?",  # Should route to P1 (factual)
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                timestamp=int(time.time() * 1000),
                is_subquestion=True,
                priority=0
            ),
            WorkUnit(
                parent_query_id=state.original_query.id,
                text="What are the latest Python updates in 2024?",  # Should route to P2 (current)
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                timestamp=int(time.time() * 1000),
                is_subquestion=True,
                priority=1
            )
        ]
        
        for wu in workunits:
            state.add_workunit(wu)
        
        # Test fallback routing directly
        m2 = QueryRouterLangGraph()
        
        # Test individual fallback decisions
        decision1 = await m2._fallback_routing_decision(workunits[0], 3)
        decision2 = await m2._fallback_routing_decision(workunits[1], 3)
        
        # Basic assertions for fallback
        assert len(decision1.selected_paths) > 0, "Fallback should select at least one path"
        assert len(decision2.selected_paths) > 0, "Fallback should select at least one path"
        assert all(path in ['P1', 'P2', 'P3'] for path in decision1.selected_paths), "Should only use valid paths"
        assert all(path in ['P1', 'P2', 'P3'] for path in decision2.selected_paths), "Should only use valid paths"
        
        # Check that different query types get different routing
        # Factual query should prefer P1
        assert 'P1' in decision1.selected_paths, "Factual query should include P1"
        
        # Current info query should prefer P2
        assert 'P2' in decision2.selected_paths, "Current info query should include P2"
        
        print(f"✅ Fallback routing works correctly")
        print(f"   Factual query → {decision1.selected_paths}")
        print(f"   Current query → {decision2.selected_paths}")
    
    @pytest.mark.asyncio
    async def test_m2_basic_routing_logic(self):
        """Test M2 basic routing logic and path selection."""
        
        m2 = QueryRouterLangGraph()
        
        # Test query complexity assessment
        assert m2._assess_query_complexity("What is AI?") == "low"
        assert m2._assess_query_complexity("What is artificial intelligence and how does it work?") == "medium"
        # This query has 15 words, so it should be "high" (>15 words)
        long_query = "What is artificial intelligence and how does it work in modern machine learning systems and applications today?"
        assert m2._assess_query_complexity(long_query) == "high"
        
        # Test temporal sensitivity
        assert m2._assess_temporal_sensitivity("What is Python?") == "low"
        assert m2._assess_temporal_sensitivity("What are the latest Python features?") == "high"
        assert m2._assess_temporal_sensitivity("What happened this year?") == "medium"
        
        # Test reasoning requirements (note: method converts to lowercase)
        assert m2._assess_reasoning_requirements("What is Python?") == "basic"
        assert m2._assess_reasoning_requirements("Please explain Python syntax") == "moderate"  # Contains "explain"
        assert m2._assess_reasoning_requirements("Why is Python better than Java?") == "complex"  # Contains "why"
        
        # Test information freshness
        assert m2._assess_information_freshness("What is programming?") == "not_critical"
        assert m2._assess_information_freshness("What are the latest news?") == "critical"
        assert m2._assess_information_freshness("What happened in 2024?") == "important"
        
        print("✅ All routing logic assessments work correctly")
    
    @pytest.mark.asyncio
    async def test_m2_fallback_mechanism(self):
        """Test that M2 fallback mechanism works when LLM fails."""
        
        state = ReactorState(original_query=UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="Test fallback",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        ))
        
        # Add a simple WorkUnit
        workunit = WorkUnit(
            parent_query_id=state.original_query.id,
            text="What is artificial intelligence?",
            user_id=state.original_query.user_id,
            conversation_id=state.original_query.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=False
        )
        state.add_workunit(workunit)
        
        m2 = QueryRouterLangGraph()
        
        # Even if LLM fails, fallback should work
        result_state = await m2.execute(state)
        
        assert len(result_state.route_plans) == 1, "Should create route plan even with fallback"
        assert len(result_state.route_plans[0].selected_paths) > 0, "Fallback should select at least one path"
        assert all(path in ['P1', 'P2', 'P3'] for path in result_state.route_plans[0].selected_paths), "Fallback should only use valid paths"