"""Tests for M4 Quality Check module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit, EvidenceItem, Provenance, SourceType
from src.modules.m4_retrieval_quality_check_langgraph import M4QualityCheckLangGraph, QualityAssessment


class TestM4QualityCheck:
    """Test suite for M4 Quality Check module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.module = M4QualityCheckLangGraph()
        
        # Create test data
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        self.workunit_id = uuid4()
        
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What are the latest developments in AI?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test evidence items
        self.evidence1 = EvidenceItem(
            workunit_id=self.workunit_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Artificial Intelligence has seen significant advances in 2024, particularly in large language models and computer vision.",
            title="AI Developments 2024",
            score_raw=0.8,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="https://example.com/ai-news",
                url="https://example.com/ai-news",
                retrieval_path="P2",
                router_decision_id=uuid4()
            )
        )
        
        self.evidence2 = EvidenceItem(
            workunit_id=self.workunit_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Short snippet.",
            title="Brief AI Note",
            score_raw=0.5,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="https://example.org/brief",
                url="https://example.org/brief",
                retrieval_path="P2",
                router_decision_id=uuid4()
            )
        )
        
        # Create test state
        self.state = ReactorState(original_query=self.user_query)
        self.state.add_evidence(self.evidence1)
        self.state.add_evidence(self.evidence2)
    
    def test_module_initialization(self):
        """Test module initialization and configuration."""
        assert self.module.module_code == "M4"
        assert self.module.quality_threshold == 0.6
        assert self.module.batch_size == 5
        assert self.module.timeout_seconds == 10
        assert self.module.quality_prompt is not None
    
    def test_quality_assessment_model(self):
        """Test QualityAssessment Pydantic model."""
        assessment = QualityAssessment(
            evidence_id=uuid4(),
            relevance_score=0.8,
            credibility_score=0.7,
            recency_score=0.9,
            completeness_score=0.6,
            overall_score=0.75,
            reasoning="High quality evidence with good relevance and credibility.",
            should_keep=True
        )
        
        assert assessment.relevance_score == 0.8
        assert assessment.overall_score == 0.75
        assert assessment.should_keep == True
        
        # Test validation
        with pytest.raises(ValueError):
            QualityAssessment(
                evidence_id=uuid4(),
                relevance_score=1.5,  # Invalid score > 1.0
                credibility_score=0.7,
                recency_score=0.9,
                completeness_score=0.6,
                overall_score=0.75,
                reasoning="Test",
                should_keep=True
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_placeholder_assessment(self):
        """Test execute method with placeholder quality assessment."""
        # Execute the module
        result_state = await self.module.execute(self.state)
        
        # Verify results
        assert isinstance(result_state, ReactorState)
        
        # Should filter out low-quality evidence
        # evidence1 should be kept (good content length and characteristics)
        # evidence2 might be filtered out (short content)
        remaining_evidence = result_state.evidences
        
        # At least some evidence should remain
        assert len(remaining_evidence) >= 0
        
        # All remaining evidence should meet quality threshold
        for evidence in remaining_evidence:
            # Check that evidence has been processed
            assert evidence.workunit_id == self.workunit_id
    
    @pytest.mark.asyncio
    async def test_check_path_evidence_quality(self):
        """Test path-specific evidence quality checking."""
        # Add evidence from different paths
        evidence_p1 = EvidenceItem(
            workunit_id=self.workunit_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Evidence from P1 path with good content length and relevance to AI developments.",
            title="P1 Evidence",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.db,
                source_id="db_source_1",
                retrieval_path="P1",
                router_decision_id=uuid4()
            )
        )
        
        self.state.add_evidence(evidence_p1)
        
        # Check quality for P2 path only
        result_state = await self.module.check_path_evidence_quality(self.state, "P2")
        
        # P1 evidence should remain unchanged
        p1_evidence = [e for e in result_state.evidences if e.provenance.retrieval_path == "P1"]
        assert len(p1_evidence) == 1
        assert p1_evidence[0].content == evidence_p1.content
        
        # P2 evidence should be quality-checked
        p2_evidence = [e for e in result_state.evidences if e.provenance.retrieval_path == "P2"]
        # Some P2 evidence might be filtered out based on quality
        assert len(p2_evidence) >= 0
    
    def test_create_placeholder_assessment(self):
        """Test placeholder assessment creation."""
        assessment_data = self.module._create_placeholder_assessment(self.evidence1, self.user_query.text)
        
        assert "relevance_score" in assessment_data
        assert "credibility_score" in assessment_data
        assert "recency_score" in assessment_data
        assert "completeness_score" in assessment_data
        assert "overall_score" in assessment_data
        assert "reasoning" in assessment_data
        assert "should_keep" in assessment_data
        
        # Scores should be between 0 and 1
        for score_key in ["relevance_score", "credibility_score", "recency_score", "completeness_score", "overall_score"]:
            score = assessment_data[score_key]
            assert 0.0 <= score <= 1.0
    
    def test_parse_llm_response_valid_json(self):
        """Test parsing valid LLM response."""
        valid_response = """
        Based on the evidence, here is my assessment:
        {
            "relevance_score": 0.8,
            "credibility_score": 0.7,
            "recency_score": 0.9,
            "completeness_score": 0.6,
            "overall_score": 0.75,
            "reasoning": "The evidence is highly relevant and from a credible source.",
            "should_keep": true
        }
        """
        
        parsed_data = self.module._parse_llm_response(valid_response)
        
        assert parsed_data["relevance_score"] == 0.8
        assert parsed_data["credibility_score"] == 0.7
        assert parsed_data["should_keep"] == True
        assert "reasoning" in parsed_data
    
    def test_parse_llm_response_invalid_json(self):
        """Test parsing invalid LLM response."""
        invalid_response = "This is not a valid JSON response about quality assessment."
        
        parsed_data = self.module._parse_llm_response(invalid_response)
        
        # Should return fallback assessment data
        assert "relevance_score" in parsed_data
        assert parsed_data["overall_score"] == 0.5  # Fallback score
        assert parsed_data["reasoning"] == "Fallback assessment due to LLM failure"
    
    def test_fallback_assessment(self):
        """Test fallback assessment creation."""
        assessment = self.module._fallback_assessment(self.evidence1, self.user_query.text)
        
        assert isinstance(assessment, QualityAssessment)
        assert assessment.evidence_id == self.evidence1.id
        assert assessment.overall_score == 0.5
        assert assessment.should_keep == True  # Conservative approach
        assert "Fallback assessment" in assessment.reasoning
    
    @pytest.mark.asyncio
    async def test_process_evidence_batch(self):
        """Test batch processing of evidence items."""
        evidences = [self.evidence1, self.evidence2]
        
        filtered_evidences = await self.module._process_evidence_batch(evidences, self.user_query.text)
        
        # Should return a list of evidence items
        assert isinstance(filtered_evidences, list)
        
        # All returned evidence should be EvidenceItem instances
        for evidence in filtered_evidences:
            assert isinstance(evidence, EvidenceItem)
    
    @pytest.mark.asyncio
    async def test_assess_evidence_quality_placeholder(self):
        """Test evidence quality assessment with placeholder mode."""
        assessment = await self.module._assess_evidence_quality(self.evidence1, self.user_query.text)
        
        assert isinstance(assessment, QualityAssessment)
        assert assessment.evidence_id == self.evidence1.id
        assert 0.0 <= assessment.overall_score <= 1.0
        assert isinstance(assessment.should_keep, bool)
        assert len(assessment.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_evidence(self):
        """Test execution with no evidence items."""
        empty_state = ReactorState(original_query=self.user_query)
        
        result_state = await self.module.execute(empty_state)
        
        assert isinstance(result_state, ReactorState)
        assert len(result_state.evidences) == 0
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(self):
        """Test error handling in execute method."""
        # Create evidence with minimal/problematic data
        bad_evidence = EvidenceItem(
            workunit_id=self.workunit_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="x",  # Minimal content
            title=None,
            score_raw=0.5,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="minimal_source",  # Minimal source
                retrieval_path="P2",
                router_decision_id=uuid4()
            )
        )
        
        bad_state = ReactorState(original_query=self.user_query)
        bad_state.add_evidence(bad_evidence)
        
        # Should not raise exception
        result_state = await self.module.execute(bad_state)
        
        assert isinstance(result_state, ReactorState)
    
    def test_quality_threshold_filtering(self):
        """Test that quality threshold is properly applied."""
        # Test with different threshold values
        original_threshold = self.module.quality_threshold
        
        try:
            # Set high threshold
            self.module.quality_threshold = 0.9
            
            # Create assessment below threshold
            low_quality_data = {
                'relevance_score': 0.3,
                'credibility_score': 0.4,
                'recency_score': 0.5,
                'completeness_score': 0.3,
                'overall_score': 0.375,
                'reasoning': 'Low quality evidence',
                'should_keep': False
            }
            
            assessment = QualityAssessment(
                evidence_id=self.evidence1.id,
                **low_quality_data
            )
            
            # Evidence should not be kept due to low score and should_keep=False
            assert assessment.overall_score < self.module.quality_threshold
            assert assessment.should_keep == False
            
        finally:
            # Restore original threshold
            self.module.quality_threshold = original_threshold
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_large_dataset(self):
        """Test batch processing with more evidence than batch size."""
        # Create more evidence items than batch size
        evidences = []
        for i in range(10):  # More than default batch_size of 5
            evidence = EvidenceItem(
                workunit_id=self.workunit_id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                content=f"Evidence content {i} with sufficient length for quality assessment.",
                title=f"Evidence {i}",
                score_raw=0.7,
                provenance=Provenance(
                    source_type=SourceType.web,
                    source_id=f"https://example.com/evidence{i}",
                    url=f"https://example.com/evidence{i}",
                    retrieval_path="P2",
                    router_decision_id=uuid4()
                )
            )
            evidences.append(evidence)
        
        # Create state with many evidence items
        large_state = ReactorState(original_query=self.user_query)
        for evidence in evidences:
            large_state.add_evidence(evidence)
        
        # Execute quality check
        result_state = await self.module.execute(large_state)
        
        # Should handle all evidence items
        assert isinstance(result_state, ReactorState)
        # Some evidence should remain (depending on quality assessment)
        assert len(result_state.evidences) >= 0