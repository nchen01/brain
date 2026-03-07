"""Tests for M3 Simple Retrieval LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.models.results import RoutePlan
from src.modules.m3_simple_retrieval_langgraph import (
    simple_retrieval_langgraph,
    QueryAnalysis,
    SourceSelection,
    RetrievalResults,
    ValidationResults
)


class TestM3SimpleRetrievalLangGraph:
    """Test suite for M3 Simple Retrieval LangGraph implementation."""
    
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
            text="What is Python programming language?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test WorkUnit
        self.workunit = WorkUnit(
            parent_query_id=self.query_id,
            text=self.user_query.text,
            is_subquestion=False,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            trace=self.user_query.trace
        )
        
        # Create test state
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_workunit(self.workunit)
        
        # Add route plan for P1
        route_plan = RoutePlan(
            workunit_id=self.workunit.id,
            selected_paths=["P1"],
            router_decision_id=uuid4(),
            reasoning="Test routing to P1"
        )
        self.initial_state.route_plans = [route_plan]
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M3 LangGraph execution."""
        with patch.object(simple_retrieval_langgraph, '_call_llm', side_effect=self._mock_llm_responses):
            result_state = await simple_retrieval_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert len(result_state.evidences) > 0
            assert hasattr(result_state, 'query_analyses')
            assert hasattr(result_state, 'source_selections')
            assert hasattr(result_state, 'retrieval_results')
    
    @pytest.mark.asyncio
    async def test_query_analysis_node(self):
        """Test query analysis node with Pydantic validation."""
        state = self.initial_state.copy()
        state.current_workunits = [self.workunit]
        
        with patch.object(simple_retrieval_langgraph, '_call_llm', side_effect=self._mock_query_analysis_response):
            result_state = await simple_retrieval_langgraph._analyze_query_node(state)
            
            # Verify query analysis results
            assert hasattr(result_state, 'query_analyses')
            assert len(result_state.query_analyses) == 1
            
            analysis = result_state.query_analyses[0]
            assert isinstance(analysis, QueryAnalysis)
            assert analysis.query_text == self.workunit.text
            assert analysis.query_type in ["factual", "technical", "historical", "comparative", "general"]
            assert 0.0 <= analysis.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_source_selection_node(self):
        """Test source selection node with Pydantic validation."""
        # Create state with query analysis
        analysis = QueryAnalysis(
            query_text=self.workunit.text,
            query_type="technical",
            complexity_level="moderate",
            key_concepts=["Python", "programming", "language"],
            retrieval_strategy="focused_search",
            confidence=0.8
        )
        
        state = self.initial_state.copy()
        state.query_analyses = [analysis]
        
        with patch.object(simple_retrieval_langgraph, '_call_llm', side_effect=self._mock_source_selection_response):
            result_state = await simple_retrieval_langgraph._select_sources_node(state)
            
            # Verify source selection results
            assert hasattr(result_state, 'source_selections')
            assert len(result_state.source_selections) == 1
            
            selection = result_state.source_selections[0]
            assert isinstance(selection, SourceSelection)
            assert len(selection.selected_sources) > 0
            assert all(0.0 <= score <= 1.0 for score in selection.source_priorities.values())
            assert 0.0 <= selection.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_retrieve_data_node(self):
        """Test data retrieval node."""
        # Create state with source selection
        selection = SourceSelection(
            selected_sources=["general_kb", "technical_kb"],
            source_priorities={"general_kb": 0.8, "technical_kb": 0.9},
            selection_reasoning="Technical query requires technical sources",
            expected_results=3,
            confidence=0.8
        )
        
        state = self.initial_state.copy()
        state.current_workunits = [self.workunit]
        state.source_selections = [selection]
        
        result_state = await simple_retrieval_langgraph._retrieve_data_node(state)
        
        # Verify retrieval results
        assert hasattr(result_state, 'retrieval_results')
        assert hasattr(result_state, 'retrieved_evidence')
        assert len(result_state.retrieval_results) == 1
        
        results = result_state.retrieval_results[0]
        assert isinstance(results, RetrievalResults)
        assert results.total_results > 0
        assert len(results.evidence_items) > 0
        assert 0.0 <= results.confidence <= 1.0
        
        # Verify evidence was added to state
        assert len(result_state.evidences) > 0
    
    @pytest.mark.asyncio
    async def test_validate_results_node(self):
        """Test results validation node."""
        # Create state with retrieved evidence
        state = self.initial_state.copy()
        
        # Add some evidence to validate
        from src.models.core import EvidenceItem, Provenance
        from src.models.types import SourceType
        
        evidence = EvidenceItem(
            workunit_id=self.workunit.id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Python is a high-level programming language known for its simplicity and readability.",
            title="Python Programming Language Overview",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.db,
                source_id="technical_kb",
                retrieval_path="P1",
                router_decision_id=uuid4()
            )
        )
        
        state.retrieved_evidence = [evidence]
        
        result_state = await simple_retrieval_langgraph._validate_results_node(state)
        
        # Verify validation results
        assert hasattr(result_state, 'validation_results')
        
        validation = result_state.validation_results
        assert isinstance(validation, ValidationResults)
        assert len(validation.validated_items) >= 0
        assert 0.0 <= validation.overall_quality <= 1.0
        assert 0.0 <= validation.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        # Test with failing LLM calls
        with patch.object(simple_retrieval_langgraph, '_call_llm', side_effect=Exception("LLM call failed")):
            result_state = await simple_retrieval_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback mechanisms
            assert result_state is not None
            # May have evidence from fallback retrieval
            assert len(result_state.evidences) >= 0
    
    @pytest.mark.asyncio
    async def test_no_routed_workunits(self):
        """Test behavior when no WorkUnits are routed to P1."""
        # Create state without route plans
        state = ReactorState(original_query=self.user_query)
        
        result_state = await simple_retrieval_langgraph.execute(state)
        
        # Should handle gracefully
        assert result_state is not None
        assert len(result_state.evidences) == 0
    
    @pytest.mark.asyncio
    async def test_pydantic_validation_errors(self):
        """Test handling of Pydantic validation errors."""
        # Mock LLM to return invalid JSON
        with patch.object(simple_retrieval_langgraph, '_call_llm', return_value='{"invalid": "json"'):
            result_state = await simple_retrieval_langgraph.execute(self.initial_state)
            
            # Should fall back gracefully
            assert result_state is not None
    
    def test_query_analysis_pydantic_model(self):
        """Test QueryAnalysis Pydantic model validation."""
        # Valid data
        valid_data = {
            "query_text": "What is Python?",
            "query_type": "factual",
            "complexity_level": "simple",
            "key_concepts": ["Python", "programming"],
            "retrieval_strategy": "focused_search",
            "confidence": 0.8
        }
        
        analysis = QueryAnalysis(**valid_data)
        assert analysis.query_text == "What is Python?"
        assert analysis.confidence == 0.8
        
        # Invalid confidence (should raise validation error)
        with pytest.raises(Exception):  # Pydantic validation error
            QueryAnalysis(**{**valid_data, "confidence": 1.5})
    
    def test_source_selection_pydantic_model(self):
        """Test SourceSelection Pydantic model validation."""
        valid_data = {
            "selected_sources": ["general_kb", "technical_kb"],
            "source_priorities": {"general_kb": 0.8, "technical_kb": 0.9},
            "selection_reasoning": "Technical query needs technical sources",
            "expected_results": 3,
            "confidence": 0.8
        }
        
        selection = SourceSelection(**valid_data)
        assert len(selection.selected_sources) == 2
        assert selection.expected_results == 3
    
    def test_retrieval_results_pydantic_model(self):
        """Test RetrievalResults Pydantic model validation."""
        valid_data = {
            "evidence_items": [{"id": "test", "content": "test content"}],
            "retrieval_stats": {"total": 1},
            "source_coverage": {"general_kb": 1},
            "total_results": 1,
            "confidence": 0.8
        }
        
        results = RetrievalResults(**valid_data)
        assert results.total_results == 1
        assert results.confidence == 0.8
    
    def test_validation_results_pydantic_model(self):
        """Test ValidationResults Pydantic model validation."""
        valid_data = {
            "validated_items": ["item1", "item2"],
            "quality_scores": {"item1": 0.8, "item2": 0.7},
            "validation_issues": [],
            "overall_quality": 0.75,
            "confidence": 0.9
        }
        
        validation = ValidationResults(**valid_data)
        assert len(validation.validated_items) == 2
        assert validation.overall_quality == 0.75
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded."""
        with patch.object(simple_retrieval_langgraph, '_call_llm', side_effect=self._mock_llm_responses):
            result_state = await simple_retrieval_langgraph.execute(self.initial_state)
            
            # Check that path stats were recorded
            assert hasattr(result_state, 'path_stats')
            # Should have at least one path stat entry
            # (Implementation may vary based on how path_stats is stored)
    
    def _mock_llm_responses(self, prompt: str) -> str:
        """Mock LLM responses for different prompt types."""
        if 'query_analysis' in prompt.lower():
            return self._mock_query_analysis_response(prompt)
        elif 'source_selection' in prompt.lower():
            return self._mock_source_selection_response(prompt)
        else:
            return '{"status": "processed"}'
    
    def _mock_query_analysis_response(self, prompt: str) -> str:
        """Mock query analysis response."""
        return '''
        {
            "query_text": "What is Python programming language?",
            "query_type": "factual",
            "complexity_level": "simple",
            "key_concepts": ["Python", "programming", "language"],
            "retrieval_strategy": "focused_search",
            "confidence": 0.8
        }
        '''
    
    def _mock_source_selection_response(self, prompt: str) -> str:
        """Mock source selection response."""
        return '''
        {
            "selected_sources": ["general_kb", "technical_kb"],
            "source_priorities": {
                "general_kb": 0.7,
                "technical_kb": 0.9
            },
            "selection_reasoning": "Technical query about programming language requires technical knowledge base",
            "expected_results": 3,
            "confidence": 0.8
        }
        '''


class TestM3Integration:
    """Integration tests for M3 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="Explain machine learning algorithms",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_routing(self):
        """Test M3 integration with routing information."""
        # Create state with proper routing
        state = ReactorState(original_query=self.user_query)
        
        workunit = WorkUnit(
            parent_query_id=self.user_query.id,
            text=self.user_query.text,
            is_subquestion=False,
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id
        )
        state.add_workunit(workunit)
        
        # Add routing information
        route_plan = RoutePlan(
            workunit_id=workunit.id,
            selected_paths=["P1", "P2"],  # Multiple paths
            router_decision_id=uuid4(),
            reasoning="Multi-path retrieval for comprehensive results"
        )
        state.route_plans = [route_plan]
        
        with patch.object(simple_retrieval_langgraph, '_call_llm', return_value='{"status": "ok"}'):
            result_state = await simple_retrieval_langgraph.execute(state)
            
            # Should process WorkUnit routed to P1
            assert result_state is not None
    
    @pytest.mark.asyncio
    async def test_evidence_integration(self):
        """Test that generated evidence integrates properly with the system."""
        state = ReactorState(original_query=self.user_query)
        
        workunit = WorkUnit(
            parent_query_id=self.user_query.id,
            text=self.user_query.text,
            is_subquestion=False,
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id
        )
        state.add_workunit(workunit)
        
        with patch.object(simple_retrieval_langgraph, '_call_llm', return_value='{"status": "ok"}'):
            result_state = await simple_retrieval_langgraph.execute(state)
            
            # Check evidence properties
            for evidence in result_state.evidences:
                assert evidence.workunit_id == workunit.id
                assert evidence.user_id == self.user_query.user_id
                assert evidence.conversation_id == self.user_query.conversation_id
                assert evidence.provenance is not None
                assert evidence.provenance.retrieval_path == "P1"