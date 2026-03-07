"""Tests for Path Execution Coordinator."""

import pytest
import asyncio
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.models.results import RoutePlan
from src.modules.m2d5_path_coordinator import PathExecutionCoordinator, PathExecutionPlan


class TestPathExecutionCoordinator:
    """Test suite for Path Execution Coordinator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.coordinator = PathExecutionCoordinator()
        
        # Create test data
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What is Python and how does it compare to Java?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create WorkUnits
        self.workunit1 = WorkUnit(
            parent_query_id=self.query_id,
            text="What is Python programming language?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=True,
            priority=0
        )
        
        self.workunit2 = WorkUnit(
            parent_query_id=self.query_id,
            text="How does Python compare to Java?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=True,
            priority=1
        )
        
        # Create test state
        self.state = ReactorState(original_query=self.user_query)
        self.state.add_workunit(self.workunit1)
        self.state.add_workunit(self.workunit2)
    
    def test_create_execution_plans(self):
        """Test creation of execution plans from route plans."""
        # Create route plans
        route_plans = [
            RoutePlan(
                workunit_id=self.workunit1.id,
                selected_paths=["P1"],  # Simple retrieval only
                router_decision_id=uuid4(),
                reasoning="Factual query"
            ),
            RoutePlan(
                workunit_id=self.workunit2.id,
                selected_paths=["P1", "P3"],  # Simple + Multi-hop
                router_decision_id=uuid4(),
                reasoning="Comparison query"
            )
        ]
        
        self.state.route_plans = route_plans
        
        # Create execution plans
        execution_plans = self.coordinator._create_execution_plans(self.state)
        
        # Verify execution plans
        assert len(execution_plans) == 2  # P1 and P3
        
        # Find P1 plan
        p1_plan = next((p for p in execution_plans if p.path_id == "P1"), None)
        assert p1_plan is not None
        assert p1_plan.module_name == "M3"
        assert len(p1_plan.assigned_workunits) == 2  # Both WorkUnits go to P1
        assert self.workunit1.id in p1_plan.assigned_workunits
        assert self.workunit2.id in p1_plan.assigned_workunits
        
        # Find P3 plan
        p3_plan = next((p for p in execution_plans if p.path_id == "P3"), None)
        assert p3_plan is not None
        assert p3_plan.module_name == "M6"
        assert len(p3_plan.assigned_workunits) == 1  # Only workunit2 goes to P3
        assert self.workunit2.id in p3_plan.assigned_workunits
    
    def test_create_path_state(self):
        """Test creation of path-specific state."""
        # Create execution plan
        plan = PathExecutionPlan(
            path_id="P1",
            assigned_workunits=[self.workunit1.id],
            module_name="M3"
        )
        
        # Create path state
        path_state = self.coordinator._create_path_state(self.state, plan)
        
        # Verify path state
        assert len(path_state.workunits) == 1
        assert path_state.workunits[0].id == self.workunit1.id
        assert path_state.current_path_id == "P1"
        assert path_state.current_module == "M3"
        
        # Original state should be unchanged
        assert len(self.state.workunits) == 2
    
    def test_get_path_priority(self):
        """Test path priority assignment."""
        assert self.coordinator._get_path_priority("P1") == 1  # Fastest
        assert self.coordinator._get_path_priority("P2") == 2  # Medium
        assert self.coordinator._get_path_priority("P3") == 3  # Slowest
        assert self.coordinator._get_path_priority("P99") == 1  # Default
    
    @pytest.mark.asyncio
    async def test_execute_parallel_paths_no_routes(self):
        """Test parallel execution with no route plans."""
        # No route plans in state
        result_state = await self.coordinator.execute_parallel_paths(self.state)
        
        # Should return original state unchanged
        assert result_state == self.state
        assert len(result_state.evidences) == 0
    
    @pytest.mark.asyncio
    async def test_execute_parallel_paths_with_p1_only(self):
        """Test parallel execution with P1 path only."""
        # Create route plan for P1 only
        route_plans = [
            RoutePlan(
                workunit_id=self.workunit1.id,
                selected_paths=["P1"],
                router_decision_id=uuid4(),
                reasoning="Simple factual query"
            )
        ]
        
        self.state.route_plans = route_plans
        
        # Execute parallel paths
        result_state = await self.coordinator.execute_parallel_paths(self.state)
        
        # Verify results
        assert hasattr(result_state, 'path_execution_results')
        assert len(result_state.path_execution_results) == 1
        
        # Check P1 execution result
        p1_result = result_state.path_execution_results[0]
        assert p1_result.path_id == "P1"
        assert p1_result.success == True
        assert self.workunit1.id in p1_result.workunit_results
        
        # Note: M3 currently uses mock data, so evidence count may be 0
        # This is expected in the current implementation
        
        # Should have path statistics
        assert len(result_state.path_stats) == 1
        assert result_state.path_stats[0].path_id == "P1"
        assert result_state.path_stats[0].success == True
    
    def test_path_modules_mapping(self):
        """Test that path modules are correctly mapped."""
        expected_mapping = {
            "P1": "M3",  # Simple Retrieval
            "P2": "M5",  # Internet Retrieval  
            "P3": "M6",  # Multi-hop Reasoning
        }
        
        assert self.coordinator.path_modules == expected_mapping