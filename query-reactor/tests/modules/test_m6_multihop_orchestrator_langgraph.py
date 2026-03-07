"""Tests for M6 Multi-hop Orchestrator LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m6_multihop_orchestrator_langgraph import (
    multihop_orchestrator_langgraph,
    MultihopOrchestratorLangGraph,
    ComplexityAnalysis,
    HopPlan,
    HopExecution,
    ReasoningSynthesis
)


class TestM6MultihopOrchestratorLangGraph:
    """Test suite for M6 Multi-hop Orchestrator LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        
        # Create complex multi-hop query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            text="How does climate change affect ocean currents, and what impact does this have on global weather patterns and marine ecosystems?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create WorkUnits for multi-hop reasoning
        self.workunit1 = WorkUnit(
            text="How does climate change affect ocean currents?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        self.workunit2 = WorkUnit(
            text="Impact of ocean current changes on weather patterns",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        # Create initial state
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_workunit(self.workunit1)
        self.initial_state.add_workunit(self.workunit2)    
    
@pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M6 execution with multi-hop orchestration."""
        with patch.object(multihop_orchestrator_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Complexity analysis
                '{"query_text": "How does climate change affect ocean currents...", "complexity_score": 0.9, "reasoning_type": "causal_chain", "hop_count_estimate": 3, "key_concepts": ["climate change", "ocean currents", "weather patterns", "marine ecosystems"], "confidence": 0.85}',
                # Hop planning
                '{"hop_sequence": ["climate_ocean_impact", "current_weather_connection", "ecosystem_effects"], "intermediate_queries": ["How does climate change affect ocean temperature and salinity?", "How do ocean current changes influence weather?", "What are the marine ecosystem impacts?"], "dependency_map": {"hop1": [], "hop2": ["hop1"], "hop3": ["hop1", "hop2"]}, "expected_evidence_types": ["climate_data", "oceanographic_data", "weather_data"], "confidence": 0.8}',
                # Hop execution (multiple hops)
                '{"hop_id": "hop1", "query_executed": "climate change ocean temperature salinity", "evidence_found": 3, "reasoning_result": "Climate change increases ocean temperature and alters salinity patterns", "next_hop_needed": true, "confidence": 0.85}',
                '{"hop_id": "hop2", "query_executed": "ocean current changes weather patterns", "evidence_found": 2, "reasoning_result": "Changed ocean currents disrupt atmospheric circulation", "next_hop_needed": true, "confidence": 0.8}',
                '{"hop_id": "hop3", "query_executed": "marine ecosystem impacts ocean changes", "evidence_found": 2, "reasoning_result": "Marine ecosystems face habitat disruption and species migration", "next_hop_needed": false, "confidence": 0.8}',
                # Synthesis
                '{"total_hops": 3, "synthesis_result": "Climate change affects ocean currents through temperature and salinity changes, which disrupts weather patterns and marine ecosystems", "evidence_chain": ["climate_data", "ocean_data", "weather_data", "ecosystem_data"], "reasoning_quality": 0.85, "completeness": 0.9, "confidence": 0.85}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await multihop_orchestrator_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'complexity_analysis')
            assert hasattr(result_state, 'hop_plan')
            assert hasattr(result_state, 'reasoning_synthesis')
            
            # Check multi-hop execution
            assert result_state.complexity_analysis.hop_count_estimate >= 2
            assert len(result_state.hop_plan.hop_sequence) >= 2
    
    @pytest.mark.asyncio
    async def test_analyze_complexity_node(self):
        """Test complexity analysis node with Pydantic validation."""
        with patch.object(multihop_orchestrator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "query_text": "How does climate change affect ocean currents, and what impact does this have on global weather patterns and marine ecosystems?",\n                "complexity_score": 0.95,\n                "reasoning_type": "multi_causal_chain",\n                "hop_count_estimate": 4,\n                "key_concepts": ["climate change", "ocean currents", "global weather", "marine ecosystems", "causal relationships"],\n                "confidence": 0.9\n            }'
            
            result_state = await multihop_orchestrator_langgraph._analyze_complexity_node(self.initial_state)
            
            # Verify complexity analysis results
            assert hasattr(result_state, 'complexity_analysis')
            analysis = result_state.complexity_analysis
            
            assert analysis.complexity_score == 0.95
            assert analysis.reasoning_type == "multi_causal_chain"
            assert analysis.hop_count_estimate == 4
            assert "climate change" in analysis.key_concepts
            assert "ocean currents" in analysis.key_concepts
            assert analysis.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_plan_hops_node(self):
        """Test hop planning node."""
        # Set up state with complexity analysis
        state_with_analysis = ReactorState(original_query=self.user_query)
        state_with_analysis.add_workunit(self.workunit1)
        state_with_analysis.complexity_analysis = ComplexityAnalysis(
            query_text=self.user_query.text,
            complexity_score=0.9,
            reasoning_type="causal_chain",
            hop_count_estimate=3,
            key_concepts=["climate change", "ocean currents", "weather patterns"],
            confidence=0.85
        )
        
        with patch.object(multihop_orchestrator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "hop_sequence": ["climate_impact_analysis", "ocean_current_changes", "weather_pattern_effects", "ecosystem_consequences"],\n                "intermediate_queries": ["How does climate change affect ocean temperature?", "How do temperature changes affect currents?", "How do current changes affect weather?", "What are the ecosystem impacts?"],\n                "dependency_map": {"hop1": [], "hop2": ["hop1"], "hop3": ["hop2"], "hop4": ["hop1", "hop3"]},\n                "expected_evidence_types": ["climate_research", "oceanographic_data", "meteorological_data", "ecological_studies"],\n                "confidence": 0.85\n            }'
            
            result_state = await multihop_orchestrator_langgraph._plan_hops_node(state_with_analysis)
            
            # Verify hop planning results
            assert hasattr(result_state, 'hop_plan')
            plan = result_state.hop_plan
            
            assert len(plan.hop_sequence) == 4
            assert "climate_impact_analysis" in plan.hop_sequence
            assert len(plan.intermediate_queries) == 4
            assert "hop1" in plan.dependency_map
            assert "climate_research" in plan.expected_evidence_types
            assert plan.confidence == 0.85    
   
 @pytest.mark.asyncio
    async def test_execute_hop_node(self):
        """Test hop execution node."""
        # Set up state with hop plan
        state_with_plan = ReactorState(original_query=self.user_query)
        state_with_plan.add_workunit(self.workunit1)
        state_with_plan.hop_plan = HopPlan(
            hop_sequence=["climate_analysis", "current_impact", "weather_effects"],
            intermediate_queries=["climate change ocean effects", "current pattern changes", "weather pattern disruption"],
            dependency_map={"hop1": [], "hop2": ["hop1"], "hop3": ["hop2"]},
            expected_evidence_types=["climate_data", "ocean_data", "weather_data"],
            confidence=0.8
        )
        
        with patch.object(multihop_orchestrator_langgraph, '_call_llm') as mock_llm:
            # Mock multiple hop executions
            mock_responses = [
                '{"hop_id": "hop1", "query_executed": "climate change ocean effects", "evidence_found": 4, "reasoning_result": "Climate change increases ocean temperature by 1-2°C, affecting density and circulation", "next_hop_needed": true, "confidence": 0.9}',
                '{"hop_id": "hop2", "query_executed": "current pattern changes", "evidence_found": 3, "reasoning_result": "Temperature changes slow thermohaline circulation by 15-20%", "next_hop_needed": true, "confidence": 0.85}',
                '{"hop_id": "hop3", "query_executed": "weather pattern disruption", "evidence_found": 2, "reasoning_result": "Slower circulation affects regional climate patterns and precipitation", "next_hop_needed": false, "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            # Mock evidence retrieval for each hop
            with patch.object(multihop_orchestrator_langgraph, '_retrieve_hop_evidence') as mock_retrieve:
                mock_retrieve.return_value = [
                    EvidenceItem(
                        workunit_id=self.workunit1.id,
                        user_id=self.user_id,
                        conversation_id=self.conversation_id,
                        content="Climate change increases ocean temperature affecting circulation patterns.",
                        title="Ocean Temperature Climate Impact",
                        score_raw=0.9,
                        provenance=Provenance(
                            source_type=SourceType.knowledge_base,
                            source_id="climate_research_db",
                            doc_id="ocean_temp_001"
                        )
                    )
                ]
                
                result_state = await multihop_orchestrator_langgraph._execute_hop_node(state_with_plan)
                
                # Verify hop execution results
                assert hasattr(result_state, 'hop_executions')
                assert len(result_state.hop_executions) >= 1
                
                execution = result_state.hop_executions[0]
                assert execution.hop_id == "hop1"
                assert execution.evidence_found > 0
                assert "temperature" in execution.reasoning_result.lower()
                assert execution.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_synthesize_results_node(self):
        """Test results synthesis node."""
        # Set up state with hop executions
        state_with_hops = ReactorState(original_query=self.user_query)
        state_with_hops.hop_executions = [
            HopExecution(
                hop_id="hop1",
                query_executed="climate ocean effects",
                evidence_found=3,
                reasoning_result="Climate change increases ocean temperature",
                next_hop_needed=True,
                confidence=0.9
            ),
            HopExecution(
                hop_id="hop2",
                query_executed="current changes weather",
                evidence_found=2,
                reasoning_result="Changed currents affect weather patterns",
                next_hop_needed=False,
                confidence=0.85
            )
        ]
        
        with patch.object(multihop_orchestrator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "total_hops": 2,\n                "synthesis_result": "Climate change increases ocean temperature, which alters current patterns and subsequently affects global weather systems through disrupted atmospheric circulation",\n                "evidence_chain": ["climate_temperature_data", "ocean_circulation_data", "weather_pattern_data"],\n                "reasoning_quality": 0.88,\n                "completeness": 0.85,\n                "confidence": 0.87\n            }'
            
            result_state = await multihop_orchestrator_langgraph._synthesize_results_node(state_with_hops)
            
            # Verify synthesis results
            assert hasattr(result_state, 'reasoning_synthesis')
            synthesis = result_state.reasoning_synthesis
            
            assert synthesis.total_hops == 2
            assert "climate change" in synthesis.synthesis_result.lower()
            assert "temperature" in synthesis.synthesis_result.lower()
            assert len(synthesis.evidence_chain) > 0
            assert synthesis.reasoning_quality == 0.88
            assert synthesis.completeness == 0.85
            assert synthesis.confidence == 0.87
    
    def test_complexity_analysis_pydantic_model(self):
        """Test ComplexityAnalysis Pydantic model validation."""
        # Valid data
        valid_data = {
            "query_text": "Complex multi-hop query about climate and oceans",
            "complexity_score": 0.9,
            "reasoning_type": "causal_chain",
            "hop_count_estimate": 3,
            "key_concepts": ["climate", "oceans", "weather"],
            "confidence": 0.85
        }
        analysis = ComplexityAnalysis(**valid_data)
        assert analysis.complexity_score == 0.9
        assert analysis.reasoning_type == "causal_chain"
        assert analysis.hop_count_estimate == 3
        assert "climate" in analysis.key_concepts
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            ComplexityAnalysis(
                query_text="test",
                complexity_score=1.5,  # Invalid: > 1.0
                reasoning_type="test",
                hop_count_estimate=1,
                key_concepts=[],
                confidence=0.8
            )