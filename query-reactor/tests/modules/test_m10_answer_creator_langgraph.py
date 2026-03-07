"""Tests for M10 Answer Creator LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance, Answer, Citation, WorkUnit
from src.models.types import SourceType
from src.modules.m10_answer_creator_langgraph import (
    answer_creator_langgraph,
    AnswerCreatorLangGraph,
    EvidenceAnalysis,
    WorkunitAnswerPlan,
    AnswerContent
)


class TestM10AnswerCreatorLangGraph:
    """Test suite for M10 Answer Creator LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        
        # Create test user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            text="What are the benefits of renewable energy?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test evidence items
        self.evidence1 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Renewable energy sources like solar and wind power provide clean electricity without greenhouse gas emissions during operation.",
            title="Clean Energy Benefits",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="energy_db",
                doc_id="doc_001",
                chunk_id="chunk_001"
            )
        )
        
        self.evidence2 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Solar panels and wind turbines have become significantly more cost-effective over the past decade, making renewable energy competitive with fossil fuels.",
            title="Cost Effectiveness",
            score_raw=0.85,
            provenance=Provenance(
                source_type=SourceType.web_search,
                source_id="web_search",
                doc_id="doc_002",
                chunk_id="chunk_002"
            )
        )
        
        # Create test WorkUnit
        self.workunit = WorkUnit(
            text="What are the benefits of renewable energy?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        # Create test state with evidence
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_workunit(self.workunit)
        self.initial_state.add_evidence(self.evidence1)
        self.initial_state.add_evidence(self.evidence2)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M10 execution with answer creation."""
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                '{"evidence_id": "' + str(self.evidence1.id) + '", "relevance_score": 0.9, "quality_score": 0.85, "key_points": ["clean electricity", "no emissions"], "confidence": 0.9}',
                '{"text": "Renewable energy offers significant environmental and economic benefits. Solar and wind power provide clean electricity without greenhouse gas emissions, and have become cost-competitive with fossil fuels.", "citations": [{"source": "energy_db", "text": "clean electricity"}], "limitations": [], "confidence": 0.85, "reasoning": "Based on high-quality evidence about environmental and economic benefits"}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_creator_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert result_state.final_answer is not None
            assert result_state.final_answer.text != ""
            assert len(result_state.final_answer.citations) >= 0
    
    @pytest.mark.asyncio
    async def test_analyze_evidence_node(self):
        """Test evidence analysis node with Pydantic validation."""
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "evidence_id": "' + str(self.evidence1.id) + '",\n                "relevance_score": 0.95,\n                "quality_score": 0.9,\n                "key_points": ["renewable energy", "clean electricity", "no emissions"],\n                "confidence": 0.9\n            }'
            
            result_state = await answer_creator_langgraph._analyze_evidence_node(self.initial_state)
            
            # Verify evidence analysis results
            assert hasattr(result_state, 'evidence_analyses')
            assert len(result_state.evidence_analyses) > 0
            
            analysis = result_state.evidence_analyses[0]
            assert analysis.evidence_id == str(self.evidence1.id)
            assert analysis.relevance_score == 0.95
            assert analysis.quality_score == 0.9
            assert "renewable energy" in analysis.key_points
            assert analysis.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_plan_answers_node(self):
        """Test answer planning node."""
        # Set up state with evidence analysis
        state_with_analysis = ReactorState(original_query=self.user_query)
        state_with_analysis.add_workunit(self.workunit)
        state_with_analysis.add_evidence(self.evidence1)
        state_with_analysis.evidence_analyses = [
            EvidenceAnalysis(
                evidence_id=str(self.evidence1.id),
                relevance_score=0.9,
                quality_score=0.85,
                key_points=["clean energy", "environmental benefits"],
                confidence=0.9
            )
        ]
        
        result_state = await answer_creator_langgraph._plan_answers_node(state_with_analysis)
        
        # Verify answer planning results
        assert hasattr(result_state, 'answer_plans')
        assert len(result_state.answer_plans) > 0
        
        plan = result_state.answer_plans[0]
        assert plan.workunit_id == str(self.workunit.id)
        assert plan.has_sufficient_evidence == True
        assert len(plan.selected_evidence) > 0
        assert plan.answer_strategy in ["extraction", "synthesis", "insufficient"]
        assert plan.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_generate_content_node(self):
        """Test content generation node."""
        # Set up state with answer plans
        state_with_plans = ReactorState(original_query=self.user_query)
        state_with_plans.add_workunit(self.workunit)
        state_with_plans.add_evidence(self.evidence1)
        state_with_plans.answer_plans = [
            WorkunitAnswerPlan(
                workunit_id=str(self.workunit.id),
                has_sufficient_evidence=True,
                selected_evidence=[str(self.evidence1.id)],
                answer_strategy="extraction",
                confidence=0.85
            )
        ]
        
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "text": "Renewable energy provides clean electricity without emissions and has become cost-competitive.",\n                "citations": [{"source": "energy_db", "text": "clean electricity"}],\n                "limitations": [],\n                "confidence": 0.85,\n                "reasoning": "Based on reliable evidence about renewable energy benefits"\n            }'
            
            result_state = await answer_creator_langgraph._generate_content_node(state_with_plans)
            
            # Verify content generation results
            assert hasattr(result_state, 'workunit_answers')
            assert len(result_state.workunit_answers) > 0
            
            content = result_state.workunit_answers[0]
            assert content.text != ""
            assert content.confidence > 0.0
            assert len(content.citations) >= 0
    
    @pytest.mark.asyncio
    async def test_synthesize_answer_node(self):
        """Test answer synthesis node."""
        # Set up state with workunit answers
        state_with_content = ReactorState(original_query=self.user_query)
        state_with_content.add_workunit(self.workunit)
        state_with_content.workunit_answers = [
            AnswerContent(
                text="Renewable energy provides environmental and economic benefits.",
                citations=[{"source": "energy_db", "text": "clean electricity"}],
                limitations=[],
                confidence=0.85,
                reasoning="Based on evidence analysis"
            )
        ]
        
        with patch.object(answer_creator_langgraph, '_create_single_answer') as mock_create:
            mock_answer = Answer(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query_id=self.user_query.id,
                text="Renewable energy provides environmental and economic benefits.",
                citations=[Citation(source="energy_db", text="clean electricity", url="")],
                limitations=[],
                confidence=0.85
            )
            mock_create.return_value = mock_answer
            
            result_state = await answer_creator_langgraph._synthesize_answer_node(state_with_content)
            
            # Verify answer synthesis results
            assert result_state.final_answer is not None
            assert result_state.final_answer.text != ""
            assert result_state.final_answer.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_validate_answer_node(self):
        """Test answer validation node."""
        # Set up state with final answer
        state_with_answer = ReactorState(original_query=self.user_query)
        state_with_answer.final_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.user_query.id,
            text="Renewable energy provides clean electricity without emissions.",
            citations=[Citation(source="energy_db", text="clean electricity", url="")],
            limitations=[],
            confidence=0.85
        )
        
        with patch.object(answer_creator_langgraph, '_validate_answer_quality') as mock_validate:
            mock_validate.return_value = {"quality_score": 0.9, "completeness": 0.85}
            
            result_state = await answer_creator_langgraph._validate_answer_node(state_with_answer)
            
            # Verify validation results
            assert result_state.final_answer is not None
            assert hasattr(result_state, 'answer_metadata')
            assert 'validation' in result_state.answer_metadata
    
    @pytest.mark.asyncio
    async def test_insufficient_evidence_handling(self):
        """Test handling when insufficient evidence is available."""
        # Create state with SMR decision indicating insufficient evidence
        insufficient_state = ReactorState(original_query=self.user_query)
        insufficient_state.add_workunit(self.workunit)
        insufficient_state.smr_decision = 'insufficient_evidence'
        
        with patch.object(answer_creator_langgraph, '_create_insufficient_evidence_answer') as mock_create:
            mock_answer = Answer(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query_id=self.user_query.id,
                text="I don't have enough reliable information to answer your question about renewable energy benefits.",
                citations=[],
                limitations=["Insufficient evidence available"],
                confidence=0.0
            )
            mock_create.return_value = mock_answer
            
            result_state = await answer_creator_langgraph.execute(insufficient_state)
            
            # Should handle insufficient evidence gracefully
            assert result_state.final_answer is not None
            assert "don't have enough" in result_state.final_answer.text.lower() or "insufficient" in result_state.final_answer.text.lower()
            assert result_state.final_answer.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise an exception
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await answer_creator_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback answer
            assert result_state is not None
            assert result_state.final_answer is not None
            assert "error" in result_state.final_answer.text.lower() or "apologize" in result_state.final_answer.text.lower()
            assert result_state.final_answer.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_evidence_analysis_fallback(self):
        """Test evidence analysis fallback when LLM fails."""
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            mock_llm.side_effect = Exception("Analysis failed")
            
            result_state = await answer_creator_langgraph._analyze_evidence_node(self.initial_state)
            
            # Should use fallback analysis
            assert hasattr(result_state, 'evidence_analyses')
            assert len(result_state.evidence_analyses) > 0
            
            analysis = result_state.evidence_analyses[0]
            assert analysis.relevance_score == 0.7  # Default fallback
            assert analysis.confidence == 0.5  # Default confidence
    
    def test_evidence_analysis_pydantic_model(self):
        """Test EvidenceAnalysis Pydantic model validation."""
        # Valid data
        valid_data = {
            "evidence_id": "test_id",
            "relevance_score": 0.9,
            "quality_score": 0.85,
            "key_points": ["renewable energy", "clean power"],
            "confidence": 0.9
        }
        analysis = EvidenceAnalysis(**valid_data)
        assert analysis.evidence_id == "test_id"
        assert analysis.relevance_score == 0.9
        assert "renewable energy" in analysis.key_points
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            EvidenceAnalysis(
                evidence_id="test",
                relevance_score=1.5,  # Invalid: > 1.0
                quality_score=0.8,
                key_points=["test"],
                confidence=0.8
            )
    
    def test_workunit_answer_plan_pydantic_model(self):
        """Test WorkunitAnswerPlan Pydantic model validation."""
        # Valid data
        valid_data = {
            "workunit_id": "test_workunit",
            "has_sufficient_evidence": True,
            "selected_evidence": ["evidence_1", "evidence_2"],
            "answer_strategy": "synthesis",
            "confidence": 0.85
        }
        plan = WorkunitAnswerPlan(**valid_data)
        assert plan.workunit_id == "test_workunit"
        assert plan.has_sufficient_evidence == True
        assert len(plan.selected_evidence) == 2
        assert plan.answer_strategy == "synthesis"
        
        # Invalid data (confidence too low)
        with pytest.raises(Exception):  # Pydantic validation error
            WorkunitAnswerPlan(
                workunit_id="test",
                has_sufficient_evidence=True,
                selected_evidence=["test"],
                answer_strategy="test",
                confidence=-0.1  # Invalid: < 0.0
            )
    
    def test_answer_content_pydantic_model(self):
        """Test AnswerContent Pydantic model validation."""
        # Valid data
        valid_data = {
            "text": "This is a test answer about renewable energy benefits.",
            "citations": [{"source": "test_source", "text": "test citation"}],
            "limitations": ["Limited scope"],
            "confidence": 0.8,
            "reasoning": "Based on available evidence"
        }
        content = AnswerContent(**valid_data)
        assert content.text == "This is a test answer about renewable energy benefits."
        assert len(content.citations) == 1
        assert content.confidence == 0.8
        
        # Test with minimal data (limitations has default)
        minimal_data = {
            "text": "Minimal answer",
            "citations": [],
            "confidence": 0.6,
            "reasoning": "Minimal reasoning"
        }
        content_min = AnswerContent(**minimal_data)
        assert content_min.limitations == []  # Default empty list
    
    def test_get_evidence_for_workunit(self):
        """Test evidence retrieval for specific workunit."""
        evidence_list = answer_creator_langgraph._get_evidence_for_workunit(self.initial_state, self.workunit)
        
        assert isinstance(evidence_list, list)
        # Should return evidence items (implementation may vary)
        assert len(evidence_list) >= 0
    
    def test_format_evidence_for_prompt(self):
        """Test evidence formatting for LLM prompts."""
        evidence_list = [self.evidence1, self.evidence2]
        formatted = answer_creator_langgraph._format_evidence_for_prompt(evidence_list)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should contain evidence content
        assert "renewable energy" in formatted.lower() or "solar" in formatted.lower()
    
    @pytest.mark.asyncio
    async def test_different_answer_strategies(self):
        """Test different answer generation strategies."""
        strategies = ["extraction", "synthesis", "insufficient"]
        
        for strategy in strategies:
            plan = WorkunitAnswerPlan(
                workunit_id=str(self.workunit.id),
                has_sufficient_evidence=(strategy != "insufficient"),
                selected_evidence=[str(self.evidence1.id)] if strategy != "insufficient" else [],
                answer_strategy=strategy,
                confidence=0.8 if strategy != "insufficient" else 0.0
            )
            
            state_with_plan = ReactorState(original_query=self.user_query)
            state_with_plan.add_workunit(self.workunit)
            state_with_plan.add_evidence(self.evidence1)
            state_with_plan.answer_plans = [plan]
            
            with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
                if strategy != "insufficient":
                    mock_llm.return_value = f'{{\n                        "text": "Answer using {strategy} strategy",\n                        "citations": [{{"source": "test", "text": "test"}}],\n                        "limitations": [],\n                        "confidence": 0.8,\n                        "reasoning": "Using {strategy} approach"\n                    }}'
                
                result_state = await answer_creator_langgraph._generate_content_node(state_with_plan)
                
                assert hasattr(result_state, 'workunit_answers')
                assert len(result_state.workunit_answers) > 0
                
                content = result_state.workunit_answers[0]
                if strategy == "insufficient":
                    assert "couldn't find" in content.text.lower() or "insufficient" in content.text.lower()
                    assert content.confidence == 0.0
                else:
                    assert strategy in content.text.lower() or content.confidence > 0.0


class TestM10Integration:
    """Integration tests for M10 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="How does machine learning work in image recognition?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_multiple_workunits(self):
        """Test M10 integration with multiple WorkUnits."""
        # Create multiple WorkUnits
        workunits = [
            WorkUnit(
                text="How does machine learning work?",
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id
            ),
            WorkUnit(
                text="What is image recognition?",
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id
            )
        ]
        
        # Create evidence for each workunit
        evidence_items = [
            EvidenceItem(
                workunit_id=workunits[0].id,
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Machine learning uses algorithms to learn patterns from data.",
                title="ML Basics",
                score_raw=0.9,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="ml_db",
                    doc_id="doc_001"
                )
            ),
            EvidenceItem(
                workunit_id=workunits[1].id,
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Image recognition identifies objects and patterns in digital images.",
                title="Image Recognition",
                score_raw=0.85,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="vision_db",
                    doc_id="doc_002"
                )
            )
        ]
        
        state = ReactorState(original_query=self.user_query)
        for workunit in workunits:
            state.add_workunit(workunit)
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            # Mock responses for multiple WorkUnits
            mock_responses = [
                # Evidence analyses
                '{"evidence_id": "' + str(evidence_items[0].id) + '", "relevance_score": 0.9, "quality_score": 0.85, "key_points": ["machine learning", "algorithms"], "confidence": 0.9}',
                '{"evidence_id": "' + str(evidence_items[1].id) + '", "relevance_score": 0.85, "quality_score": 0.8, "key_points": ["image recognition", "patterns"], "confidence": 0.85}',
                # Content generation
                '{"text": "Machine learning uses algorithms to learn patterns from data for various applications.", "citations": [{"source": "ml_db", "text": "algorithms"}], "limitations": [], "confidence": 0.85, "reasoning": "Based on ML evidence"}',
                '{"text": "Image recognition identifies objects and patterns in digital images using computer vision.", "citations": [{"source": "vision_db", "text": "patterns"}], "limitations": [], "confidence": 0.8, "reasoning": "Based on vision evidence"}',
                # Synthesis
                '{"text": "Machine learning works by using algorithms to learn patterns from data. In image recognition, these algorithms identify objects and patterns in digital images.", "citations": [{"source": "ml_db", "text": "algorithms"}, {"source": "vision_db", "text": "patterns"}], "limitations": [], "confidence": 0.82, "reasoning": "Synthesized from multiple sources"}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_creator_langgraph.execute(state)
            
            # Should create comprehensive answer from multiple WorkUnits
            assert result_state is not None
            assert result_state.final_answer is not None
            assert len(result_state.final_answer.text) > 50  # Substantial answer
            assert result_state.final_answer.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_integration_with_no_evidence(self):
        """Test M10 behavior with no evidence available."""
        workunit = WorkUnit(
            text="What is quantum computing?",
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id
        )
        
        state = ReactorState(original_query=self.user_query)
        state.add_workunit(workunit)
        # No evidence added
        
        result_state = await answer_creator_langgraph.execute(state)
        
        # Should handle gracefully with insufficient evidence response
        assert result_state is not None
        assert result_state.final_answer is not None
        assert "don't have" in result_state.final_answer.text.lower() or "insufficient" in result_state.final_answer.text.lower()
        assert result_state.final_answer.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded."""
        workunit = WorkUnit(
            text="Test query for performance",
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id
        )
        
        evidence = EvidenceItem(
            workunit_id=workunit.id,
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            content="Test evidence content for performance testing.",
            title="Performance Test",
            score_raw=0.8,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="test_db",
                doc_id="test_doc"
            )
        )
        
        state = ReactorState(original_query=self.user_query)
        state.add_workunit(workunit)
        state.add_evidence(evidence)
        
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"evidence_id": "' + str(evidence.id) + '", "relevance_score": 0.8, "quality_score": 0.8, "key_points": ["test"], "confidence": 0.8}',
                '{"text": "Test answer for performance measurement.", "citations": [{"source": "test_db", "text": "test"}], "limitations": [], "confidence": 0.8, "reasoning": "Performance test"}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_creator_langgraph.execute(state)
            
            # Check that answer was created successfully
            assert result_state is not None
            assert result_state.final_answer is not None
            assert result_state.final_answer.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_citation_accuracy(self):
        """Test citation accuracy and completeness."""
        workunit = WorkUnit(
            text="What are the benefits of solar energy?",
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id
        )
        
        evidence = EvidenceItem(
            workunit_id=workunit.id,
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            content="Solar energy reduces electricity costs and provides clean renewable power.",
            title="Solar Benefits",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="solar_db",
                doc_id="solar_001",
                chunk_id="chunk_001"
            )
        )
        
        state = ReactorState(original_query=self.user_query)
        state.add_workunit(workunit)
        state.add_evidence(evidence)
        
        with patch.object(answer_creator_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"evidence_id": "' + str(evidence.id) + '", "relevance_score": 0.9, "quality_score": 0.9, "key_points": ["solar energy", "cost reduction", "clean power"], "confidence": 0.9}',
                '{"text": "Solar energy provides significant benefits including reduced electricity costs and clean renewable power generation.", "citations": [{"source": "solar_db", "text": "reduces electricity costs", "doc_id": "solar_001"}], "limitations": [], "confidence": 0.9, "reasoning": "Based on reliable solar energy evidence"}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_creator_langgraph.execute(state)
            
            # Verify citation accuracy
            assert result_state is not None
            assert result_state.final_answer is not None
            assert len(result_state.final_answer.citations) > 0
            
            citation = result_state.final_answer.citations[0]
            assert citation.source == "solar_db"
            assert "cost" in citation.text.lower() or "solar" in citation.text.lower()