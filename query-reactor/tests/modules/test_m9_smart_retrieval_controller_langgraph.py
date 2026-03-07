"""Tests for M9 Smart Retrieval Controller LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m9_smart_retrieval_controller_langgraph import (
    smart_retrieval_controller_langgraph,
    SmartRetrievalControllerLangGraph,
    EvidenceAssessment,
    ControlDecision,
    ActionPlan,
    ControlExecution
)


class TestM9SmartRetrievalControllerLangGraph:
    """Test suite for M9 Smart Retrieval Controller LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        
        # Create test user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            text="What are the long-term economic impacts of artificial intelligence on employment and job markets?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test WorkUnits
        self.workunit1 = WorkUnit(
            text="Economic impacts of AI on employment",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        self.workunit2 = WorkUnit(
            text="AI effects on job market dynamics",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        # Create test evidence with varying quality
        self.high_quality_evidence = EvidenceItem(
            workunit_id=self.workunit1.id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Comprehensive economic analysis shows AI will displace 25% of current jobs while creating 15% new positions by 2030, with net employment impact varying by sector and skill level.",
            title="AI Employment Impact Analysis 2024",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="economic_research_db",
                doc_id="ai_employment_2024"
            )
        )
        
        self.medium_quality_evidence = EvidenceItem(
            workunit_id=self.workunit2.id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="AI automation affects job markets through productivity gains and skill requirements changes.",
            title="AI Job Market Effects",
            score_raw=0.7,
            provenance=Provenance(
                source_type=SourceType.web_search,
                source_id="business_news",
                doc_id="ai_jobs_001"
            )
        )
        
        # Create initial state with some evidence
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_workunit(self.workunit1)
        self.initial_state.add_workunit(self.workunit2)
        self.initial_state.add_evidence(self.high_quality_evidence)
        self.initial_state.add_evidence(self.medium_quality_evidence)   
 
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M9 execution with smart retrieval control."""
        with patch.object(smart_retrieval_controller_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Evidence assessment
                '{"total_evidence": 2, "quality_distribution": {"high": 1, "medium": 1, "low": 0}, "coverage_score": 0.7, "confidence_score": 0.8, "gaps_identified": ["sector-specific analysis", "timeline projections"], "assessment_confidence": 0.85}',
                # Control decision
                '{"decision": "expand", "decision_rationale": "Current evidence provides good foundation but lacks sector-specific details and timeline analysis", "priority_level": "medium", "expected_improvement": 0.3, "resource_cost": "medium", "confidence": 0.8}',
                # Action plan
                '{"action_type": "targeted_retrieval", "target_modules": ["M3", "M5"], "parameters": {"focus_areas": ["sector_analysis", "timeline_data"], "quality_threshold": 0.8}, "success_criteria": ["sector coverage > 80%", "timeline data available"], "fallback_plan": "proceed_with_current_evidence", "estimated_duration": "moderate", "confidence": 0.8}',
                # Control execution
                '{"action_executed": "targeted_retrieval", "execution_status": "success", "results_achieved": ["additional_sector_data", "timeline_projections"], "performance_metrics": {"coverage_improvement": 0.25, "quality_increase": 0.15}, "issues_encountered": [], "next_recommendation": "proceed_to_answer_generation", "confidence": 0.85}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await smart_retrieval_controller_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'evidence_assessment')
            assert hasattr(result_state, 'control_decision')
            assert hasattr(result_state, 'action_plan')
            assert hasattr(result_state, 'control_execution')
            
            # Check control decision
            assert result_state.control_decision.decision in ["continue", "refine", "terminate", "expand"]
            assert result_state.control_decision.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_assess_evidence_node(self):
        """Test evidence assessment node with Pydantic validation."""
        with patch.object(smart_retrieval_controller_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "total_evidence": 2,\n                "quality_distribution": {"high": 1, "medium": 1, "low": 0},\n                "coverage_score": 0.75,\n                "confidence_score": 0.8,\n                "gaps_identified": ["sector-specific data", "regional variations", "timeline analysis"],\n                "assessment_confidence": 0.85\n            }'
            
            result_state = await smart_retrieval_controller_langgraph._assess_evidence_node(self.initial_state)
            
            # Verify evidence assessment results
            assert hasattr(result_state, 'evidence_assessment')
            assessment = result_state.evidence_assessment
            
            assert assessment.total_evidence == 2
            assert assessment.quality_distribution["high"] == 1
            assert assessment.quality_distribution["medium"] == 1
            assert assessment.coverage_score == 0.75
            assert assessment.confidence_score == 0.8
            assert "sector-specific data" in assessment.gaps_identified
            assert "regional variations" in assessment.gaps_identified
            assert assessment.assessment_confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_make_decision_node(self):
        """Test control decision making node."""
        # Set up state with evidence assessment
        state_with_assessment = ReactorState(original_query=self.user_query)
        state_with_assessment.add_evidence(self.high_quality_evidence)
        state_with_assessment.evidence_assessment = EvidenceAssessment(
            total_evidence=1,
            quality_distribution={"high": 1, "medium": 0, "low": 0},
            coverage_score=0.6,
            confidence_score=0.8,
            gaps_identified=["sector analysis", "timeline data"],
            assessment_confidence=0.8
        )
        
        with patch.object(smart_retrieval_controller_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "decision": "expand",\n                "decision_rationale": "Evidence quality is good but coverage is insufficient at 60%. Need additional sector-specific and timeline data to provide comprehensive answer.",\n                "priority_level": "high",\n                "expected_improvement": 0.35,\n                "resource_cost": "medium",\n                "confidence": 0.85\n            }'
            
            result_state = await smart_retrieval_controller_langgraph._make_decision_node(state_with_assessment)
            
            # Verify control decision results
            assert hasattr(result_state, 'control_decision')
            decision = result_state.control_decision
            
            assert decision.decision == "expand"
            assert "coverage is insufficient" in decision.decision_rationale
            assert decision.priority_level == "high"
            assert decision.expected_improvement == 0.35
            assert decision.resource_cost == "medium"
            assert decision.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_plan_action_node(self):
        """Test action planning node."""
        # Set up state with control decision
        state_with_decision = ReactorState(original_query=self.user_query)
        state_with_decision.control_decision = ControlDecision(
            decision="expand",
            decision_rationale="Need more comprehensive coverage",
            priority_level="high",
            expected_improvement=0.3,
            resource_cost="medium",
            confidence=0.85
        )
        
        with patch.object(smart_retrieval_controller_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "action_type": "targeted_retrieval",\n                "target_modules": ["M3", "M5", "M6"],\n                "parameters": {"focus_keywords": ["sector analysis", "employment timeline"], "quality_threshold": 0.8, "max_results": 10},\n                "success_criteria": ["sector_coverage > 80%", "timeline_data_available", "quality_score > 0.8"],\n                "fallback_plan": "proceed_with_existing_evidence_if_no_improvement",\n                "estimated_duration": "moderate",\n                "confidence": 0.8\n            }'
            
            result_state = await smart_retrieval_controller_langgraph._plan_action_node(state_with_decision)
            
            # Verify action plan results
            assert hasattr(result_state, 'action_plan')
            plan = result_state.action_plan
            
            assert plan.action_type == "targeted_retrieval"
            assert "M3" in plan.target_modules
            assert "M5" in plan.target_modules
            assert "focus_keywords" in plan.parameters
            assert "sector_coverage > 80%" in plan.success_criteria
            assert "proceed_with_existing_evidence" in plan.fallback_plan
            assert plan.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_execute_control_node(self):
        """Test control execution node."""
        # Set up state with action plan
        state_with_plan = ReactorState(original_query=self.user_query)
        state_with_plan.add_evidence(self.high_quality_evidence)
        state_with_plan.action_plan = ActionPlan(
            action_type="targeted_retrieval",
            target_modules=["M3", "M5"],
            parameters={"focus_areas": ["sector_analysis"], "quality_threshold": 0.8},
            success_criteria=["improved_coverage"],
            fallback_plan="proceed_with_current",
            estimated_duration="moderate",
            confidence=0.8
        )
        
        # Mock additional evidence retrieval
        with patch.object(smart_retrieval_controller_langgraph, '_execute_targeted_retrieval') as mock_retrieve:
            mock_retrieve.return_value = [
                EvidenceItem(
                    workunit_id=self.workunit1.id,
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    content="Sector-specific analysis shows manufacturing jobs face 40% displacement while healthcare jobs increase by 20%.",
                    title="AI Sector Impact Analysis",
                    score_raw=0.85,
                    provenance=Provenance(
                        source_type=SourceType.knowledge_base,
                        source_id="sector_analysis_db",
                        doc_id="ai_sectors_001"
                    )
                )
            ]
            
            result_state = await smart_retrieval_controller_langgraph._execute_control_node(state_with_plan)
            
            # Verify control execution results
            assert hasattr(result_state, 'control_execution')
            execution = result_state.control_execution
            
            assert execution.action_executed == "targeted_retrieval"
            assert execution.execution_status in ["success", "partial", "failed"]
            assert len(execution.results_achieved) >= 0
            assert isinstance(execution.performance_metrics, dict)
            assert execution.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_iteration_limit_handling(self):
        """Test handling of maximum iteration limit."""
        # Set up state that has reached max iterations
        max_iteration_state = ReactorState(original_query=self.user_query)
        max_iteration_state.control_iterations = 3  # At max limit
        
        result_state = await smart_retrieval_controller_langgraph.execute(max_iteration_state)
        
        # Should handle gracefully without further processing
        assert result_state is not None
        assert result_state.control_iterations == 3  # Should not increment further
    
    @pytest.mark.asyncio
    async def test_sufficient_evidence_handling(self):
        """Test handling when evidence is already sufficient."""
        # Create state with high-quality comprehensive evidence
        sufficient_state = ReactorState(original_query=self.user_query)
        sufficient_state.add_workunit(self.workunit1)
        
        # Add multiple high-quality evidence items
        for i in range(5):
            evidence = EvidenceItem(
                workunit_id=self.workunit1.id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                content=f"High-quality comprehensive evidence item {i} covering AI employment impacts with detailed analysis and data.",
                title=f"Comprehensive AI Employment Analysis {i}",
                score_raw=0.9,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="comprehensive_db",
                    doc_id=f"comprehensive_{i}"
                )
            )
            sufficient_state.add_evidence(evidence)
        
        with patch.object(smart_retrieval_controller_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"total_evidence": 5, "quality_distribution": {"high": 5, "medium": 0, "low": 0}, "coverage_score": 0.95, "confidence_score": 0.9, "gaps_identified": [], "assessment_confidence": 0.95}',
                '{"decision": "terminate", "decision_rationale": "Evidence is comprehensive and high-quality with 95% coverage. No additional retrieval needed.", "priority_level": "low", "expected_improvement": 0.05, "resource_cost": "low", "confidence": 0.9}',
                '{"action_type": "proceed_to_answer", "target_modules": [], "parameters": {}, "success_criteria": ["maintain_quality"], "fallback_plan": "none_needed", "estimated_duration": "immediate", "confidence": 0.9}',
                '{"action_executed": "proceed_to_answer", "execution_status": "success", "results_achieved": ["evidence_deemed_sufficient"], "performance_metrics": {"coverage": 0.95, "quality": 0.9}, "issues_encountered": [], "next_recommendation": "generate_answer", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await smart_retrieval_controller_langgraph.execute(sufficient_state)
            
            # Should decide to terminate/proceed
            assert result_state.control_decision.decision == "terminate"
            assert result_state.evidence_assessment.coverage_score >= 0.9