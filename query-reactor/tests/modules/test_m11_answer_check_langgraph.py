"""Tests for M11 Answer Check LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, Answer, Citation, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m11_answer_check_langgraph import (
    answer_check_langgraph,
    AnswerCheckLangGraph,
    AnswerAnalysis,
    AccuracyCheck,
    CitationValidation,
    CompletenessAssessment
)


class TestM11AnswerCheckLangGraph:
    """Test suite for M11 Answer Check LangGraph implementation."""
    
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
            text="What are the main benefits of renewable energy for the environment?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test citations
        self.citation1 = Citation(
            source="renewable_energy_research_db",
            text="Solar and wind power produce no greenhouse gas emissions during operation",
            url="https://example.com/renewable-research",
            doc_id="doc_001"
        )
        
        self.citation2 = Citation(
            source="environmental_impact_study",
            text="Renewable energy reduces air pollution by 70% compared to fossil fuels",
            url="https://example.com/environmental-study",
            doc_id="doc_002"
        )
        
        # Create test answer with good quality
        self.good_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="Renewable energy provides significant environmental benefits. Solar and wind power produce no greenhouse gas emissions during operation, helping to combat climate change. Additionally, renewable energy reduces air pollution by approximately 70% compared to fossil fuels, leading to cleaner air and improved public health. These technologies also reduce dependence on finite fossil fuel resources, promoting long-term environmental sustainability.",
            citations=[self.citation1, self.citation2],
            limitations=["Data primarily from developed countries"],
            confidence=0.85
        )
        
        # Create test answer with poor quality
        self.poor_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="Renewable energy is good for environment. It helps.",
            citations=[],
            limitations=[],
            confidence=0.3
        )
        
        # Create test evidence for validation
        self.evidence1 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Solar and wind power produce no greenhouse gas emissions during operation, making them environmentally sustainable alternatives to fossil fuels.",
            title="Renewable Energy Environmental Benefits",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="renewable_energy_research_db",
                doc_id="doc_001",
                chunk_id="chunk_001"
            )
        )
        
        self.evidence2 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Studies show renewable energy reduces air pollution by 70% compared to fossil fuel-based power generation.",
            title="Air Pollution Reduction Study",
            score_raw=0.85,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="environmental_impact_study",
                doc_id="doc_002",
                chunk_id="chunk_002"
            )
        )
        
        # Create test state with good answer
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.final_answer = self.good_answer
        self.initial_state.add_evidence(self.evidence1)
        self.initial_state.add_evidence(self.evidence2)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M11 execution with answer checking."""
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Answer analysis
                '{"answer_length": 387, "structure_score": 0.85, "clarity_score": 0.9, "coherence_score": 0.88, "key_points_covered": ["greenhouse gas reduction", "air pollution reduction", "sustainability"], "missing_elements": [], "confidence": 0.85}',
                # Accuracy check
                '{"accuracy_score": 0.9, "verified_facts": ["no greenhouse gas emissions", "70% pollution reduction"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.95, "confidence": 0.9}',
                # Citation validation
                '{"total_citations": 2, "valid_citations": 2, "citation_accuracy": 0.9, "missing_citations": [], "citation_quality": "high", "source_diversity": 0.8, "confidence": 0.85}',
                # Completeness assessment
                '{"completeness_score": 0.85, "query_coverage": 0.9, "depth_score": 0.8, "breadth_score": 0.85, "unanswered_aspects": [], "additional_context_needed": ["economic benefits"], "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_check_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'answer_analysis')
            assert hasattr(result_state, 'accuracy_check')
            assert hasattr(result_state, 'citation_validation')
            assert hasattr(result_state, 'completeness_assessment')
            assert hasattr(result_state, 'answer_quality_score')
            
            # Check overall quality score
            assert 0.0 <= result_state.answer_quality_score <= 1.0
            assert result_state.answer_quality_score > 0.7  # Should be high for good answer
    
    @pytest.mark.asyncio
    async def test_analyze_answer_node(self):
        """Test answer analysis node with Pydantic validation."""
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "answer_length": 387,\n                "structure_score": 0.9,\n                "clarity_score": 0.85,\n                "coherence_score": 0.88,\n                "key_points_covered": ["environmental benefits", "greenhouse gas emissions", "air pollution", "sustainability"],\n                "missing_elements": ["economic aspects"],\n                "confidence": 0.85\n            }'
            
            result_state = await answer_check_langgraph._analyze_answer_node(self.initial_state)
            
            # Verify answer analysis results
            assert hasattr(result_state, 'answer_analysis')
            analysis = result_state.answer_analysis
            
            assert analysis.answer_length == 387
            assert analysis.structure_score == 0.9
            assert analysis.clarity_score == 0.85
            assert analysis.coherence_score == 0.88
            assert "environmental benefits" in analysis.key_points_covered
            assert "greenhouse gas emissions" in analysis.key_points_covered
            assert "economic aspects" in analysis.missing_elements
            assert analysis.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_check_accuracy_node(self):
        """Test accuracy checking node."""
        # Set up state with answer analysis
        state_with_analysis = ReactorState(original_query=self.user_query)
        state_with_analysis.final_answer = self.good_answer
        state_with_analysis.add_evidence(self.evidence1)
        state_with_analysis.add_evidence(self.evidence2)
        state_with_analysis.answer_analysis = AnswerAnalysis(
            answer_length=387,
            structure_score=0.85,
            clarity_score=0.9,
            coherence_score=0.88,
            key_points_covered=["greenhouse gas reduction", "air pollution"],
            missing_elements=[],
            confidence=0.85
        )
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "accuracy_score": 0.92,\n                "verified_facts": ["no greenhouse gas emissions during operation", "70% air pollution reduction", "environmental sustainability"],\n                "questionable_claims": [],\n                "contradictions": [],\n                "evidence_support_ratio": 0.95,\n                "confidence": 0.9\n            }'
            
            result_state = await answer_check_langgraph._check_accuracy_node(state_with_analysis)
            
            # Verify accuracy check results
            assert hasattr(result_state, 'accuracy_check')
            accuracy = result_state.accuracy_check
            
            assert accuracy.accuracy_score == 0.92
            assert "no greenhouse gas emissions during operation" in accuracy.verified_facts
            assert "70% air pollution reduction" in accuracy.verified_facts
            assert len(accuracy.questionable_claims) == 0
            assert len(accuracy.contradictions) == 0
            assert accuracy.evidence_support_ratio == 0.95
            assert accuracy.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_validate_citations_node(self):
        """Test citation validation node."""
        # Set up state with accuracy check
        state_with_accuracy = ReactorState(original_query=self.user_query)
        state_with_accuracy.final_answer = self.good_answer
        state_with_accuracy.add_evidence(self.evidence1)
        state_with_accuracy.add_evidence(self.evidence2)
        state_with_accuracy.accuracy_check = AccuracyCheck(
            accuracy_score=0.9,
            verified_facts=["no greenhouse gas emissions", "70% pollution reduction"],
            questionable_claims=[],
            contradictions=[],
            evidence_support_ratio=0.95,
            confidence=0.9
        )
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "total_citations": 2,\n                "valid_citations": 2,\n                "citation_accuracy": 0.9,\n                "missing_citations": [],\n                "citation_quality": "high",\n                "source_diversity": 0.8,\n                "confidence": 0.85\n            }'
            
            result_state = await answer_check_langgraph._validate_citations_node(state_with_accuracy)
            
            # Verify citation validation results
            assert hasattr(result_state, 'citation_validation')
            citation = result_state.citation_validation
            
            assert citation.total_citations == 2
            assert citation.valid_citations == 2
            assert citation.citation_accuracy == 0.9
            assert len(citation.missing_citations) == 0
            assert citation.citation_quality == "high"
            assert citation.source_diversity == 0.8
            assert citation.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_assess_completeness_node(self):
        """Test completeness assessment node."""
        # Set up state with citation validation
        state_with_citations = ReactorState(original_query=self.user_query)
        state_with_citations.final_answer = self.good_answer
        state_with_citations.citation_validation = CitationValidation(
            total_citations=2,
            valid_citations=2,
            citation_accuracy=0.9,
            missing_citations=[],
            citation_quality="high",
            source_diversity=0.8,
            confidence=0.85
        )
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "completeness_score": 0.85,\n                "query_coverage": 0.9,\n                "depth_score": 0.8,\n                "breadth_score": 0.85,\n                "unanswered_aspects": [],\n                "additional_context_needed": ["economic benefits", "implementation challenges"],\n                "confidence": 0.8\n            }'
            
            result_state = await answer_check_langgraph._assess_completeness_node(state_with_citations)
            
            # Verify completeness assessment results
            assert hasattr(result_state, 'completeness_assessment')
            completeness = result_state.completeness_assessment
            
            assert completeness.completeness_score == 0.85
            assert completeness.query_coverage == 0.9
            assert completeness.depth_score == 0.8
            assert completeness.breadth_score == 0.85
            assert len(completeness.unanswered_aspects) == 0
            assert "economic benefits" in completeness.additional_context_needed
            assert "implementation challenges" in completeness.additional_context_needed
            assert completeness.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_no_answer_handling(self):
        """Test handling when no answer is available."""
        empty_state = ReactorState(original_query=self.user_query)
        # No final_answer set
        
        result_state = await answer_check_langgraph.execute(empty_state)
        
        # Should handle gracefully
        assert result_state is not None
        assert not hasattr(result_state, 'final_answer') or result_state.final_answer is None
    
    @pytest.mark.asyncio
    async def test_poor_quality_answer_checking(self):
        """Test checking of poor quality answer."""
        poor_state = ReactorState(original_query=self.user_query)
        poor_state.final_answer = self.poor_answer
        poor_state.add_evidence(self.evidence1)
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            # Mock responses for poor quality answer
            mock_responses = [
                # Answer analysis - poor scores
                '{"answer_length": 47, "structure_score": 0.3, "clarity_score": 0.4, "coherence_score": 0.2, "key_points_covered": ["general environmental benefit"], "missing_elements": ["specific benefits", "supporting evidence", "detailed explanation"], "confidence": 0.8}',
                # Accuracy check - low accuracy due to vague claims
                '{"accuracy_score": 0.4, "verified_facts": [], "questionable_claims": ["vague environmental benefit"], "contradictions": [], "evidence_support_ratio": 0.1, "confidence": 0.7}',
                # Citation validation - no citations
                '{"total_citations": 0, "valid_citations": 0, "citation_accuracy": 0.0, "missing_citations": ["environmental benefits claim"], "citation_quality": "poor", "source_diversity": 0.0, "confidence": 0.9}',
                # Completeness assessment - very incomplete
                '{"completeness_score": 0.2, "query_coverage": 0.3, "depth_score": 0.1, "breadth_score": 0.2, "unanswered_aspects": ["specific environmental benefits", "supporting data"], "additional_context_needed": ["detailed explanation", "evidence"], "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_check_langgraph.execute(poor_state)
            
            # Verify poor quality detection
            assert result_state is not None
            assert hasattr(result_state, 'answer_quality_score')
            assert result_state.answer_quality_score < 0.5  # Should be low for poor answer
            
            # Check specific quality issues
            assert result_state.answer_analysis.structure_score < 0.5
            assert result_state.accuracy_check.accuracy_score < 0.5
            assert result_state.citation_validation.total_citations == 0
            assert result_state.completeness_assessment.completeness_score < 0.5
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise an exception
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await answer_check_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback analysis
            assert result_state is not None
            assert result_state.final_answer is not None
            # May have fallback quality assessments
            if hasattr(result_state, 'answer_quality_score'):
                assert 0.0 <= result_state.answer_quality_score <= 1.0
    
    def test_answer_analysis_pydantic_model(self):
        """Test AnswerAnalysis Pydantic model validation."""
        # Valid data
        valid_data = {
            "answer_length": 250,
            "structure_score": 0.85,
            "clarity_score": 0.9,
            "coherence_score": 0.8,
            "key_points_covered": ["environmental benefits", "sustainability"],
            "missing_elements": ["economic aspects"],
            "confidence": 0.85
        }
        analysis = AnswerAnalysis(**valid_data)
        assert analysis.answer_length == 250
        assert analysis.structure_score == 0.85
        assert "environmental benefits" in analysis.key_points_covered
        assert "economic aspects" in analysis.missing_elements
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            AnswerAnalysis(
                answer_length=100,
                structure_score=1.5,  # Invalid: > 1.0
                clarity_score=0.8,
                coherence_score=0.8,
                key_points_covered=[],
                missing_elements=[],
                confidence=0.8
            )
    
    def test_accuracy_check_pydantic_model(self):
        """Test AccuracyCheck Pydantic model validation."""
        # Valid data
        valid_data = {
            "accuracy_score": 0.9,
            "verified_facts": ["fact1", "fact2"],
            "questionable_claims": ["claim1"],
            "contradictions": [],
            "evidence_support_ratio": 0.85,
            "confidence": 0.9
        }
        accuracy = AccuracyCheck(**valid_data)
        assert accuracy.accuracy_score == 0.9
        assert "fact1" in accuracy.verified_facts
        assert "claim1" in accuracy.questionable_claims
        assert accuracy.evidence_support_ratio == 0.85
        
        # Invalid data (negative ratio)
        with pytest.raises(Exception):  # Pydantic validation error
            AccuracyCheck(
                accuracy_score=0.8,
                verified_facts=[],
                questionable_claims=[],
                contradictions=[],
                evidence_support_ratio=-0.1,  # Invalid: < 0.0
                confidence=0.8
            )
    
    def test_citation_validation_pydantic_model(self):
        """Test CitationValidation Pydantic model validation."""
        # Valid data
        valid_data = {
            "total_citations": 5,
            "valid_citations": 4,
            "citation_accuracy": 0.8,
            "missing_citations": ["claim without citation"],
            "citation_quality": "good",
            "source_diversity": 0.7,
            "confidence": 0.85
        }
        citation = CitationValidation(**valid_data)
        assert citation.total_citations == 5
        assert citation.valid_citations == 4
        assert citation.citation_accuracy == 0.8
        assert "claim without citation" in citation.missing_citations
        
        # Test with no citations
        no_citations_data = {
            "total_citations": 0,
            "valid_citations": 0,
            "citation_accuracy": 0.0,
            "missing_citations": ["all claims need citations"],
            "citation_quality": "poor",
            "source_diversity": 0.0,
            "confidence": 0.9
        }
        no_citations = CitationValidation(**no_citations_data)
        assert no_citations.total_citations == 0
        assert no_citations.citation_quality == "poor"
    
    def test_completeness_assessment_pydantic_model(self):
        """Test CompletenessAssessment Pydantic model validation."""
        # Valid data
        valid_data = {
            "completeness_score": 0.8,
            "query_coverage": 0.85,
            "depth_score": 0.75,
            "breadth_score": 0.8,
            "unanswered_aspects": ["economic impact"],
            "additional_context_needed": ["more examples", "recent data"],
            "confidence": 0.8
        }
        completeness = CompletenessAssessment(**valid_data)
        assert completeness.completeness_score == 0.8
        assert completeness.query_coverage == 0.85
        assert "economic impact" in completeness.unanswered_aspects
        assert "more examples" in completeness.additional_context_needed
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            CompletenessAssessment(
                completeness_score=1.2,  # Invalid: > 1.0
                query_coverage=0.8,
                depth_score=0.8,
                breadth_score=0.8,
                unanswered_aspects=[],
                additional_context_needed=[],
                confidence=0.8
            )
    
    def test_calculate_overall_quality_score(self):
        """Test overall quality score calculation."""
        # Create mock assessment results
        analysis = AnswerAnalysis(
            answer_length=300,
            structure_score=0.8,
            clarity_score=0.85,
            coherence_score=0.9,
            key_points_covered=["point1", "point2"],
            missing_elements=[],
            confidence=0.8
        )
        
        accuracy = AccuracyCheck(
            accuracy_score=0.9,
            verified_facts=["fact1", "fact2"],
            questionable_claims=[],
            contradictions=[],
            evidence_support_ratio=0.95,
            confidence=0.9
        )
        
        citation = CitationValidation(
            total_citations=2,
            valid_citations=2,
            citation_accuracy=0.9,
            missing_citations=[],
            citation_quality="high",
            source_diversity=0.8,
            confidence=0.85
        )
        
        completeness = CompletenessAssessment(
            completeness_score=0.85,
            query_coverage=0.9,
            depth_score=0.8,
            breadth_score=0.85,
            unanswered_aspects=[],
            additional_context_needed=[],
            confidence=0.8
        )
        
        overall_score = answer_check_langgraph._calculate_overall_quality_score_from_components(
            analysis, accuracy, citation, completeness
        )
        
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.8  # Should be high given good component scores
    
    def test_extract_key_points(self):
        """Test key point extraction from answer text."""
        answer_text = "Renewable energy provides environmental benefits including reduced greenhouse gas emissions and improved air quality. It also promotes energy independence and creates jobs."
        
        key_points = answer_check_langgraph._extract_key_points(answer_text)
        
        assert isinstance(key_points, list)
        assert len(key_points) > 0
        # Should identify main concepts
        key_points_text = " ".join(key_points).lower()
        assert "environmental" in key_points_text or "greenhouse" in key_points_text
    
    def test_validate_citation_accuracy(self):
        """Test citation accuracy validation against evidence."""
        citations = [self.citation1, self.citation2]
        evidence_list = [self.evidence1, self.evidence2]
        
        accuracy_score = answer_check_langgraph._validate_citation_accuracy(citations, evidence_list)
        
        assert 0.0 <= accuracy_score <= 1.0
        # Should be high since citations match evidence
        assert accuracy_score > 0.7
    
    @pytest.mark.asyncio
    async def test_different_answer_qualities(self):
        """Test checking answers of different quality levels."""
        # Create answers with different quality characteristics
        test_answers = [
            # High quality: comprehensive, well-cited
            Answer(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query_id=self.query_id,
                text="Renewable energy offers substantial environmental benefits. Solar and wind power generate electricity without producing greenhouse gas emissions during operation, significantly reducing carbon footprint. Studies indicate renewable energy can reduce air pollution by up to 70% compared to fossil fuels, improving public health outcomes. Additionally, renewable technologies promote environmental sustainability by reducing dependence on finite fossil fuel resources.",
                citations=[self.citation1, self.citation2],
                limitations=["Regional variations in effectiveness"],
                confidence=0.9
            ),
            # Medium quality: adequate but brief
            Answer(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query_id=self.query_id,
                text="Renewable energy helps the environment by reducing emissions and pollution. Solar and wind power are clean energy sources.",
                citations=[self.citation1],
                limitations=[],
                confidence=0.7
            ),
            # Low quality: vague and unsupported
            Answer(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query_id=self.query_id,
                text="Renewable energy is better for the environment.",
                citations=[],
                limitations=[],
                confidence=0.4
            )
        ]
        
        quality_scores = []
        
        for i, answer in enumerate(test_answers):
            state = ReactorState(original_query=self.user_query)
            state.final_answer = answer
            state.add_evidence(self.evidence1)
            state.add_evidence(self.evidence2)
            
            with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
                # Mock responses based on answer quality
                if i == 0:  # High quality
                    mock_responses = [
                        '{"answer_length": 450, "structure_score": 0.9, "clarity_score": 0.9, "coherence_score": 0.95, "key_points_covered": ["greenhouse gas reduction", "air pollution", "sustainability"], "missing_elements": [], "confidence": 0.9}',
                        '{"accuracy_score": 0.95, "verified_facts": ["no greenhouse gas emissions", "70% pollution reduction"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.95, "confidence": 0.95}',
                        '{"total_citations": 2, "valid_citations": 2, "citation_accuracy": 0.9, "missing_citations": [], "citation_quality": "excellent", "source_diversity": 0.8, "confidence": 0.9}',
                        '{"completeness_score": 0.9, "query_coverage": 0.95, "depth_score": 0.9, "breadth_score": 0.85, "unanswered_aspects": [], "additional_context_needed": [], "confidence": 0.9}'
                    ]
                elif i == 1:  # Medium quality
                    mock_responses = [
                        '{"answer_length": 120, "structure_score": 0.7, "clarity_score": 0.75, "coherence_score": 0.7, "key_points_covered": ["emissions reduction"], "missing_elements": ["detailed explanation"], "confidence": 0.8}',
                        '{"accuracy_score": 0.8, "verified_facts": ["clean energy sources"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.7, "confidence": 0.8}',
                        '{"total_citations": 1, "valid_citations": 1, "citation_accuracy": 0.8, "missing_citations": ["pollution reduction claim"], "citation_quality": "adequate", "source_diversity": 0.5, "confidence": 0.8}',
                        '{"completeness_score": 0.6, "query_coverage": 0.7, "depth_score": 0.5, "breadth_score": 0.6, "unanswered_aspects": ["specific benefits"], "additional_context_needed": ["more detail"], "confidence": 0.8}'
                    ]
                else:  # Low quality
                    mock_responses = [
                        '{"answer_length": 45, "structure_score": 0.3, "clarity_score": 0.4, "coherence_score": 0.3, "key_points_covered": [], "missing_elements": ["all specific benefits", "supporting evidence"], "confidence": 0.8}',
                        '{"accuracy_score": 0.4, "verified_facts": [], "questionable_claims": ["vague environmental claim"], "contradictions": [], "evidence_support_ratio": 0.1, "confidence": 0.7}',
                        '{"total_citations": 0, "valid_citations": 0, "citation_accuracy": 0.0, "missing_citations": ["environmental benefits claim"], "citation_quality": "none", "source_diversity": 0.0, "confidence": 0.9}',
                        '{"completeness_score": 0.2, "query_coverage": 0.3, "depth_score": 0.1, "breadth_score": 0.2, "unanswered_aspects": ["all specific benefits"], "additional_context_needed": ["complete rewrite needed"], "confidence": 0.8}'
                    ]
                
                mock_llm.side_effect = mock_responses
                
                result_state = await answer_check_langgraph.execute(state)
                quality_scores.append(result_state.answer_quality_score)
        
        # Quality scores should decrease with answer quality
        assert len(quality_scores) == 3
        assert quality_scores[0] > quality_scores[1] > quality_scores[2]  # High > Medium > Low
        assert quality_scores[0] > 0.8  # High quality
        assert 0.5 < quality_scores[1] < 0.8  # Medium quality
        assert quality_scores[2] < 0.5  # Low quality


class TestM11Integration:
    """Integration tests for M11 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="How does machine learning improve medical diagnosis accuracy?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_comprehensive_answer(self):
        """Test M11 integration with comprehensive, well-researched answer."""
        # Create comprehensive answer with multiple citations
        comprehensive_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Machine learning significantly improves medical diagnosis accuracy through several mechanisms. Deep learning algorithms can analyze medical images with 95% accuracy, often exceeding human radiologist performance in detecting early-stage cancers. Natural language processing helps extract insights from electronic health records, identifying patterns that might be missed by human analysis. Additionally, ensemble methods combining multiple ML models achieve diagnostic accuracy rates of 92-98% across various medical conditions, while reducing false positive rates by 30% compared to traditional diagnostic methods.",
            citations=[
                Citation(source="medical_ai_research", text="95% accuracy in cancer detection", url="https://example.com/cancer-ai"),
                Citation(source="diagnostic_accuracy_study", text="92-98% accuracy across conditions", url="https://example.com/diagnostic-study"),
                Citation(source="false_positive_reduction", text="30% reduction in false positives", url="https://example.com/fp-reduction")
            ],
            limitations=["Performance varies by medical specialty", "Requires large training datasets"],
            confidence=0.88
        )
        
        # Create supporting evidence
        evidence_items = [
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Deep learning algorithms achieve 95% accuracy in medical image analysis for cancer detection, surpassing human radiologist performance in early-stage identification.",
                title="AI Cancer Detection Performance",
                score_raw=0.95,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="medical_ai_research",
                    doc_id="cancer_detection_2024"
                )
            ),
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Ensemble machine learning methods demonstrate diagnostic accuracy rates of 92-98% across various medical conditions in clinical trials.",
                title="Ensemble ML Diagnostic Performance",
                score_raw=0.9,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="diagnostic_accuracy_study",
                    doc_id="ensemble_methods_2024"
                )
            )
        ]
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = comprehensive_answer
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            # Mock responses for comprehensive answer
            mock_responses = [
                '{"answer_length": 580, "structure_score": 0.95, "clarity_score": 0.9, "coherence_score": 0.92, "key_points_covered": ["deep learning accuracy", "NLP insights", "ensemble methods", "false positive reduction"], "missing_elements": [], "confidence": 0.9}',
                '{"accuracy_score": 0.95, "verified_facts": ["95% accuracy", "92-98% accuracy rates", "30% false positive reduction"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.95, "confidence": 0.95}',
                '{"total_citations": 3, "valid_citations": 3, "citation_accuracy": 0.95, "missing_citations": [], "citation_quality": "excellent", "source_diversity": 0.9, "confidence": 0.9}',
                '{"completeness_score": 0.9, "query_coverage": 0.95, "depth_score": 0.9, "breadth_score": 0.85, "unanswered_aspects": [], "additional_context_needed": ["implementation challenges"], "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_check_langgraph.execute(state)
            
            # Should receive high quality scores
            assert result_state is not None
            assert result_state.answer_quality_score > 0.9
            
            # Check individual assessment quality
            assert result_state.answer_analysis.structure_score > 0.9
            assert result_state.accuracy_check.accuracy_score > 0.9
            assert result_state.citation_validation.citation_accuracy > 0.9
            assert result_state.completeness_assessment.completeness_score > 0.8
    
    @pytest.mark.asyncio
    async def test_integration_with_contradictory_evidence(self):
        """Test M11 behavior when answer contradicts available evidence."""
        # Create answer that contradicts evidence
        contradictory_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Machine learning has minimal impact on medical diagnosis accuracy, with most AI systems performing worse than human doctors in clinical settings.",
            citations=[],
            limitations=[],
            confidence=0.6
        )
        
        # Create evidence that contradicts the answer
        contradicting_evidence = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            content="Multiple studies demonstrate that machine learning algorithms consistently outperform human doctors in diagnostic accuracy, achieving 95% accuracy rates compared to 85% for human physicians.",
            title="ML Outperforms Human Diagnosis",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="comparative_study_db",
                doc_id="ml_vs_human_2024"
            )
        )
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = contradictory_answer
        state.add_evidence(contradicting_evidence)
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"answer_length": 150, "structure_score": 0.6, "clarity_score": 0.7, "coherence_score": 0.6, "key_points_covered": ["minimal impact claim"], "missing_elements": ["supporting evidence"], "confidence": 0.8}',
                '{"accuracy_score": 0.3, "verified_facts": [], "questionable_claims": ["minimal impact", "worse than humans"], "contradictions": ["contradicts evidence showing 95% ML accuracy vs 85% human accuracy"], "evidence_support_ratio": 0.1, "confidence": 0.9}',
                '{"total_citations": 0, "valid_citations": 0, "citation_accuracy": 0.0, "missing_citations": ["minimal impact claim", "performance comparison"], "citation_quality": "none", "source_diversity": 0.0, "confidence": 0.9}',
                '{"completeness_score": 0.4, "query_coverage": 0.5, "depth_score": 0.3, "breadth_score": 0.4, "unanswered_aspects": ["actual ML performance data"], "additional_context_needed": ["evidence-based claims"], "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_check_langgraph.execute(state)
            
            # Should detect contradictions and low quality
            assert result_state is not None
            assert result_state.answer_quality_score < 0.5
            
            # Check that contradictions were identified
            assert len(result_state.accuracy_check.contradictions) > 0
            assert "contradicts evidence" in result_state.accuracy_check.contradictions[0].lower()
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded."""
        # Create standard answer for performance testing
        test_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Machine learning improves medical diagnosis through pattern recognition and data analysis capabilities.",
            citations=[Citation(source="test_source", text="pattern recognition", url="")],
            limitations=[],
            confidence=0.75
        )
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = test_answer
        
        with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"answer_length": 100, "structure_score": 0.7, "clarity_score": 0.75, "coherence_score": 0.7, "key_points_covered": ["pattern recognition"], "missing_elements": ["specific examples"], "confidence": 0.8}',
                '{"accuracy_score": 0.75, "verified_facts": ["pattern recognition"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.8, "confidence": 0.8}',
                '{"total_citations": 1, "valid_citations": 1, "citation_accuracy": 0.8, "missing_citations": [], "citation_quality": "adequate", "source_diversity": 0.5, "confidence": 0.8}',
                '{"completeness_score": 0.7, "query_coverage": 0.75, "depth_score": 0.6, "breadth_score": 0.7, "unanswered_aspects": ["specific improvements"], "additional_context_needed": ["examples"], "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await answer_check_langgraph.execute(state)
            
            # Check that quality assessment was performed
            assert result_state is not None
            assert hasattr(result_state, 'answer_quality_score')
            assert 0.0 <= result_state.answer_quality_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_quality_consistency(self):
        """Test quality assessment consistency for similar answers."""
        # Create similar answers with slight variations
        similar_answers = [
            Answer(
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                query_id=self.user_query.id,
                text="Machine learning enhances medical diagnosis accuracy by analyzing large datasets and identifying patterns that human doctors might miss.",
                citations=[Citation(source="ml_study", text="pattern identification", url="")],
                limitations=[],
                confidence=0.8
            ),
            Answer(
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                query_id=self.user_query.id,
                text="Medical diagnosis accuracy improves through machine learning by processing vast amounts of data and detecting patterns beyond human capability.",
                citations=[Citation(source="medical_ai", text="data processing", url="")],
                limitations=[],
                confidence=0.8
            )
        ]
        
        quality_scores = []
        
        for answer in similar_answers:
            state = ReactorState(original_query=self.user_query)
            state.final_answer = answer
            
            with patch.object(answer_check_langgraph, '_call_llm') as mock_llm:
                # Consistent mock responses for similar content
                mock_responses = [
                    '{"answer_length": 130, "structure_score": 0.75, "clarity_score": 0.8, "coherence_score": 0.75, "key_points_covered": ["pattern analysis", "data processing"], "missing_elements": ["specific metrics"], "confidence": 0.8}',
                    '{"accuracy_score": 0.8, "verified_facts": ["pattern identification"], "questionable_claims": [], "contradictions": [], "evidence_support_ratio": 0.8, "confidence": 0.8}',
                    '{"total_citations": 1, "valid_citations": 1, "citation_accuracy": 0.8, "missing_citations": [], "citation_quality": "good", "source_diversity": 0.5, "confidence": 0.8}',
                    '{"completeness_score": 0.75, "query_coverage": 0.8, "depth_score": 0.7, "breadth_score": 0.75, "unanswered_aspects": [], "additional_context_needed": ["specific examples"], "confidence": 0.8}'
                ]
                mock_llm.side_effect = mock_responses
                
                result_state = await answer_check_langgraph.execute(state)
                quality_scores.append(result_state.answer_quality_score)
        
        # Similar answers should get similar quality scores
        assert len(quality_scores) == 2
        score_difference = abs(quality_scores[0] - quality_scores[1])
        assert score_difference < 0.1  # Should be very similar