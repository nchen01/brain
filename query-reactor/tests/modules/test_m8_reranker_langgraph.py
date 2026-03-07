"""Tests for M8 ReRanker LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance, WorkUnit
from src.models.types import SourceType
from src.modules.m8_reranker_langgraph import (
    reranker_langgraph,
    ReRankerLangGraph,
    EvidenceScoring,
    RankingCalculation,
    RankingValidation,
    AdaptiveStrategy
)


class TestM8ReRankerLangGraph:
    """Test suite for M8 ReRanker LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        
        # Create test user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            text="What are the most effective renewable energy technologies?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test evidence items with different characteristics for ranking
        self.high_relevance_evidence = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Solar photovoltaic and wind turbine technologies are currently the most cost-effective and scalable renewable energy solutions, with efficiency rates of 20-22% for solar and capacity factors of 35-45% for wind.",
            title="Most Effective Renewable Technologies - Research Analysis",
            score_raw=0.95,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="renewable_energy_research_db",
                doc_id="effectiveness_study_2024",
                chunk_id="chunk_001"
            )
        )
        
        self.medium_relevance_evidence = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Hydroelectric power has been a reliable renewable energy source for decades, providing consistent baseload power generation.",
            title="Hydroelectric Power Reliability",
            score_raw=0.75,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="energy_systems_db",
                doc_id="hydro_analysis_2023",
                chunk_id="chunk_002"
            )
        )
        
        self.lower_relevance_evidence = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Renewable energy sources include various technologies that harness natural processes.",
            title="General Renewable Energy Overview",
            score_raw=0.6,
            provenance=Provenance(
                source_type=SourceType.web_search,
                source_id="general_web_source",
                doc_id="overview_article",
                chunk_id="chunk_003"
            )
        )
        
        self.outdated_evidence = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Solar panel efficiency was around 15% in early 2010s, making it less competitive with fossil fuels.",
            title="Historical Solar Efficiency Data",
            score_raw=0.7,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="historical_energy_db",
                doc_id="solar_history_2012",
                chunk_id="chunk_004"
            )
        )
        
        # Create test WorkUnit
        self.workunit = WorkUnit(
            text="What are the most effective renewable energy technologies?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            original_query_id=self.user_query.id
        )
        
        # Create test state with evidence
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_workunit(self.workunit)
        self.initial_state.add_evidence(self.high_relevance_evidence)
        self.initial_state.add_evidence(self.medium_relevance_evidence)
        self.initial_state.add_evidence(self.lower_relevance_evidence)
        self.initial_state.add_evidence(self.outdated_evidence)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M8 execution with evidence reranking."""
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Evidence analysis
                '{"query_complexity": "medium", "domain_specificity": "technical", "ranking_requirements": ["relevance", "recency", "quality"], "adaptive_strategy": "effectiveness_focused"}',
                # Scoring responses for each evidence item
                '{"evidence_id": "' + str(self.high_relevance_evidence.id) + '", "relevance_score": 0.95, "quality_score": 0.9, "credibility_score": 0.95, "recency_score": 0.9, "completeness_score": 0.85, "composite_score": 0.91, "confidence": 0.9}',
                '{"evidence_id": "' + str(self.medium_relevance_evidence.id) + '", "relevance_score": 0.8, "quality_score": 0.8, "credibility_score": 0.85, "recency_score": 0.7, "completeness_score": 0.75, "composite_score": 0.78, "confidence": 0.8}',
                '{"evidence_id": "' + str(self.lower_relevance_evidence.id) + '", "relevance_score": 0.6, "quality_score": 0.5, "credibility_score": 0.6, "recency_score": 0.8, "completeness_score": 0.4, "composite_score": 0.58, "confidence": 0.7}',
                '{"evidence_id": "' + str(self.outdated_evidence.id) + '", "relevance_score": 0.7, "quality_score": 0.7, "credibility_score": 0.8, "recency_score": 0.3, "completeness_score": 0.6, "composite_score": 0.64, "confidence": 0.75}',
                # Ranking calculation
                '{"algorithm_used": "weighted_composite", "total_items": 4, "ranking_factors": ["relevance", "quality", "credibility", "recency"], "score_distribution": {"high": 1, "medium": 2, "low": 1}, "ranking_quality": 0.85, "confidence": 0.8}',
                # Ranking validation
                '{"validation_method": "score_consistency", "ranking_consistency": 0.9, "top_items_quality": 0.9, "diversity_score": 0.7, "validation_issues": [], "confidence": 0.85}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await reranker_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'evidence_scores')
            assert hasattr(result_state, 'ranking_calculation')
            
            # Check that evidence was reordered by score
            assert len(result_state.evidences) == 4
            # High relevance evidence should be first after reranking
            assert result_state.evidences[0].id == self.high_relevance_evidence.id
    
    @pytest.mark.asyncio
    async def test_analyze_evidence_node(self):
        """Test evidence analysis node for ranking strategy."""
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "query_complexity": "high",\n                "domain_specificity": "specialized",\n                "ranking_requirements": ["relevance", "recency", "quality", "credibility"],\n                "adaptive_strategy": "comprehensive_analysis",\n                "weight_adjustments": {"relevance": 0.4, "quality": 0.3, "recency": 0.2, "credibility": 0.1}\n            }'
            
            result_state = await reranker_langgraph._analyze_evidence_node(self.initial_state)
            
            # Verify analysis results
            assert hasattr(result_state, 'adaptive_strategy')
            strategy = result_state.adaptive_strategy
            
            assert strategy.strategy_name == "comprehensive_analysis"
            assert "relevance" in strategy.weight_adjustments
            assert "quality" in strategy.weight_adjustments
            assert strategy.weight_adjustments["relevance"] == 0.4
            assert 0.0 <= strategy.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_scores_node(self):
        """Test score calculation node."""
        # Set up state with adaptive strategy
        state_with_strategy = ReactorState(original_query=self.user_query)
        state_with_strategy.add_evidence(self.high_relevance_evidence)
        state_with_strategy.add_evidence(self.medium_relevance_evidence)
        state_with_strategy.adaptive_strategy = AdaptiveStrategy(
            strategy_name="effectiveness_focused",
            query_characteristics={"complexity": 0.7, "specificity": 0.8},
            weight_adjustments={"relevance": 0.4, "quality": 0.3, "recency": 0.2, "credibility": 0.1},
            strategy_rationale="Focus on most effective technologies",
            expected_improvement=0.15,
            confidence=0.8
        )
        
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"evidence_id": "' + str(self.high_relevance_evidence.id) + '", "relevance_score": 0.95, "quality_score": 0.9, "credibility_score": 0.95, "recency_score": 0.9, "completeness_score": 0.85, "composite_score": 0.91, "confidence": 0.9}',
                '{"evidence_id": "' + str(self.medium_relevance_evidence.id) + '", "relevance_score": 0.8, "quality_score": 0.8, "credibility_score": 0.85, "recency_score": 0.7, "completeness_score": 0.75, "composite_score": 0.78, "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await reranker_langgraph._calculate_scores_node(state_with_strategy)
            
            # Verify scoring results
            assert hasattr(result_state, 'evidence_scores')
            assert len(result_state.evidence_scores) == 2
            
            # Check high relevance evidence score
            high_score = next(s for s in result_state.evidence_scores if s.evidence_id == str(self.high_relevance_evidence.id))
            assert high_score.relevance_score == 0.95
            assert high_score.quality_score == 0.9
            assert high_score.composite_score == 0.91
            assert high_score.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_apply_ranking_node(self):
        """Test ranking application node."""
        # Set up state with evidence scores
        state_with_scores = ReactorState(original_query=self.user_query)
        state_with_scores.add_evidence(self.high_relevance_evidence)
        state_with_scores.add_evidence(self.medium_relevance_evidence)
        state_with_scores.add_evidence(self.lower_relevance_evidence)
        
        state_with_scores.evidence_scores = [
            EvidenceScoring(
                evidence_id=str(self.high_relevance_evidence.id),
                relevance_score=0.95,
                quality_score=0.9,
                credibility_score=0.95,
                recency_score=0.9,
                completeness_score=0.85,
                composite_score=0.91,
                confidence=0.9
            ),
            EvidenceScoring(
                evidence_id=str(self.medium_relevance_evidence.id),
                relevance_score=0.8,
                quality_score=0.8,
                credibility_score=0.85,
                recency_score=0.7,
                completeness_score=0.75,
                composite_score=0.78,
                confidence=0.8
            ),
            EvidenceScoring(
                evidence_id=str(self.lower_relevance_evidence.id),
                relevance_score=0.6,
                quality_score=0.5,
                credibility_score=0.6,
                recency_score=0.8,
                completeness_score=0.4,
                composite_score=0.58,
                confidence=0.7
            )
        ]
        
        result_state = await reranker_langgraph._apply_ranking_node(state_with_scores)
        
        # Verify ranking application
        assert hasattr(result_state, 'ranking_calculation')
        ranking = result_state.ranking_calculation
        
        assert ranking.total_items == 3
        assert "relevance" in ranking.ranking_factors
        assert 0.0 <= ranking.ranking_quality <= 1.0
        
        # Check that evidence is sorted by composite score (highest first)
        assert result_state.evidences[0].id == self.high_relevance_evidence.id  # Highest score
        assert result_state.evidences[1].id == self.medium_relevance_evidence.id  # Medium score
        assert result_state.evidences[2].id == self.lower_relevance_evidence.id  # Lowest score
    
    @pytest.mark.asyncio
    async def test_validate_ranking_node(self):
        """Test ranking validation node."""
        # Set up state with ranking calculation
        state_with_ranking = ReactorState(original_query=self.user_query)
        state_with_ranking.add_evidence(self.high_relevance_evidence)
        state_with_ranking.add_evidence(self.medium_relevance_evidence)
        
        state_with_ranking.ranking_calculation = RankingCalculation(
            algorithm_used="weighted_composite",
            total_items=2,
            ranking_factors=["relevance", "quality", "credibility"],
            score_distribution={"high": 1, "medium": 1},
            ranking_quality=0.85,
            confidence=0.8
        )
        
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "validation_method": "consistency_check",\n                "ranking_consistency": 0.9,\n                "top_items_quality": 0.95,\n                "diversity_score": 0.8,\n                "validation_issues": [],\n                "confidence": 0.9\n            }'
            
            result_state = await reranker_langgraph._validate_ranking_node(state_with_ranking)
            
            # Verify validation results
            assert hasattr(result_state, 'ranking_validation')
            validation = result_state.ranking_validation
            
            assert validation.validation_method == "consistency_check"
            assert validation.ranking_consistency == 0.9
            assert validation.top_items_quality == 0.95
            assert validation.diversity_score == 0.8
            assert len(validation.validation_issues) == 0
            assert validation.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_no_evidence_handling(self):
        """Test handling when no evidence is available."""
        empty_state = ReactorState(original_query=self.user_query)
        # No evidence added
        
        result_state = await reranker_langgraph.execute(empty_state)
        
        # Should handle gracefully
        assert result_state is not None
        assert len(result_state.evidences) == 0
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise an exception
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await reranker_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback ranking
            assert result_state is not None
            assert len(result_state.evidences) == 4
            # Evidence should still be present, possibly in original order or simple fallback ranking
    
    def test_evidence_scoring_pydantic_model(self):
        """Test EvidenceScoring Pydantic model validation."""
        # Valid data
        valid_data = {
            "evidence_id": "test_evidence",
            "relevance_score": 0.9,
            "quality_score": 0.85,
            "credibility_score": 0.8,
            "recency_score": 0.75,
            "completeness_score": 0.7,
            "composite_score": 0.8,
            "confidence": 0.85
        }
        scoring = EvidenceScoring(**valid_data)
        assert scoring.evidence_id == "test_evidence"
        assert scoring.relevance_score == 0.9
        assert scoring.composite_score == 0.8
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            EvidenceScoring(
                evidence_id="test",
                relevance_score=1.5,  # Invalid: > 1.0
                quality_score=0.8,
                credibility_score=0.8,
                recency_score=0.8,
                completeness_score=0.8,
                composite_score=0.8,
                confidence=0.8
            )
    
    def test_ranking_calculation_pydantic_model(self):
        """Test RankingCalculation Pydantic model validation."""
        # Valid data
        valid_data = {
            "algorithm_used": "weighted_composite",
            "total_items": 10,
            "ranking_factors": ["relevance", "quality", "recency"],
            "score_distribution": {"high": 3, "medium": 5, "low": 2},
            "ranking_quality": 0.85,
            "confidence": 0.8
        }
        ranking = RankingCalculation(**valid_data)
        assert ranking.algorithm_used == "weighted_composite"
        assert ranking.total_items == 10
        assert "relevance" in ranking.ranking_factors
        assert ranking.score_distribution["high"] == 3
        
        # Invalid data (negative total items)
        with pytest.raises(Exception):  # Pydantic validation error
            RankingCalculation(
                algorithm_used="test",
                total_items=-1,  # Invalid: negative count
                ranking_factors=[],
                score_distribution={},
                ranking_quality=0.8,
                confidence=0.8
            )
    
    def test_ranking_validation_pydantic_model(self):
        """Test RankingValidation Pydantic model validation."""
        # Valid data
        valid_data = {
            "validation_method": "consistency_check",
            "ranking_consistency": 0.9,
            "top_items_quality": 0.95,
            "diversity_score": 0.8,
            "validation_issues": ["Minor score clustering"],
            "confidence": 0.85
        }
        validation = RankingValidation(**valid_data)
        assert validation.validation_method == "consistency_check"
        assert validation.ranking_consistency == 0.9
        assert validation.top_items_quality == 0.95
        assert "Minor score clustering" in validation.validation_issues
        
        # Test with no issues
        no_issues_data = {
            "validation_method": "perfect_ranking",
            "ranking_consistency": 1.0,
            "top_items_quality": 1.0,
            "diversity_score": 0.9,
            "validation_issues": [],
            "confidence": 0.95
        }
        no_issues = RankingValidation(**no_issues_data)
        assert len(no_issues.validation_issues) == 0
        assert no_issues.ranking_consistency == 1.0
    
    def test_adaptive_strategy_pydantic_model(self):
        """Test AdaptiveStrategy Pydantic model validation."""
        # Valid data
        valid_data = {
            "strategy_name": "effectiveness_focused",
            "query_characteristics": {"complexity": 0.7, "specificity": 0.8, "domain_depth": 0.6},
            "weight_adjustments": {"relevance": 0.4, "quality": 0.3, "recency": 0.2, "credibility": 0.1},
            "strategy_rationale": "Prioritize most effective renewable technologies based on query focus",
            "expected_improvement": 0.15,
            "confidence": 0.8
        }
        strategy = AdaptiveStrategy(**valid_data)
        assert strategy.strategy_name == "effectiveness_focused"
        assert strategy.query_characteristics["complexity"] == 0.7
        assert strategy.weight_adjustments["relevance"] == 0.4
        assert strategy.expected_improvement == 0.15
        
        # Invalid data (expected improvement too high)
        with pytest.raises(Exception):  # Pydantic validation error
            AdaptiveStrategy(
                strategy_name="test",
                query_characteristics={},
                weight_adjustments={},
                strategy_rationale="test",
                expected_improvement=1.5,  # Invalid: > 1.0
                confidence=0.8
            )
    
    def test_calculate_composite_score(self):
        """Test composite score calculation utility."""
        scores = {
            "relevance": 0.9,
            "quality": 0.8,
            "credibility": 0.85,
            "recency": 0.7,
            "completeness": 0.75
        }
        weights = {
            "relevance": 0.4,
            "quality": 0.3,
            "credibility": 0.15,
            "recency": 0.1,
            "completeness": 0.05
        }
        
        composite = reranker_langgraph._calculate_composite_score(scores, weights)
        
        assert 0.0 <= composite <= 1.0
        # Should be weighted average: 0.9*0.4 + 0.8*0.3 + 0.85*0.15 + 0.7*0.1 + 0.75*0.05
        expected = 0.36 + 0.24 + 0.1275 + 0.07 + 0.0375
        assert abs(composite - expected) < 0.01
    
    def test_assess_recency_score(self):
        """Test recency score assessment utility."""
        # Recent evidence (2024)
        recent_score = reranker_langgraph._assess_recency_score("effectiveness_study_2024")
        assert recent_score > 0.8
        
        # Older evidence (2012)
        old_score = reranker_langgraph._assess_recency_score("solar_history_2012")
        assert old_score < 0.5
        
        # No date information
        no_date_score = reranker_langgraph._assess_recency_score("general_article")
        assert 0.4 <= no_date_score <= 0.6  # Default/neutral score
    
    def test_calculate_diversity_score(self):
        """Test diversity score calculation for ranking."""
        evidence_list = [self.high_relevance_evidence, self.medium_relevance_evidence, self.lower_relevance_evidence]
        
        diversity = reranker_langgraph._calculate_diversity_score(evidence_list)
        
        assert 0.0 <= diversity <= 1.0
        # Should be higher when evidence comes from different sources/types
        assert diversity > 0.5  # Mixed sources should have reasonable diversity
    
    @pytest.mark.asyncio
    async def test_different_ranking_strategies(self):
        """Test different adaptive ranking strategies."""
        strategies = [
            ("relevance_focused", {"relevance": 0.6, "quality": 0.2, "recency": 0.1, "credibility": 0.1}),
            ("quality_focused", {"relevance": 0.3, "quality": 0.5, "recency": 0.1, "credibility": 0.1}),
            ("recency_focused", {"relevance": 0.3, "quality": 0.2, "recency": 0.4, "credibility": 0.1}),
            ("balanced", {"relevance": 0.25, "quality": 0.25, "recency": 0.25, "credibility": 0.25})
        ]
        
        for strategy_name, weights in strategies:
            state = ReactorState(original_query=self.user_query)
            state.add_evidence(self.high_relevance_evidence)
            state.add_evidence(self.outdated_evidence)  # Lower recency
            
            state.adaptive_strategy = AdaptiveStrategy(
                strategy_name=strategy_name,
                query_characteristics={"complexity": 0.7},
                weight_adjustments=weights,
                strategy_rationale=f"Testing {strategy_name} strategy",
                expected_improvement=0.1,
                confidence=0.8
            )
            
            with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
                # Mock scoring based on strategy
                if strategy_name == "recency_focused":
                    # High relevance evidence should score lower due to recency weight
                    mock_responses = [
                        '{"evidence_id": "' + str(self.high_relevance_evidence.id) + '", "relevance_score": 0.95, "quality_score": 0.9, "credibility_score": 0.95, "recency_score": 0.9, "completeness_score": 0.85, "composite_score": 0.91, "confidence": 0.9}',
                        '{"evidence_id": "' + str(self.outdated_evidence.id) + '", "relevance_score": 0.7, "quality_score": 0.7, "credibility_score": 0.8, "recency_score": 0.3, "completeness_score": 0.6, "composite_score": 0.55, "confidence": 0.75}'
                    ]
                else:
                    # Standard scoring
                    mock_responses = [
                        '{"evidence_id": "' + str(self.high_relevance_evidence.id) + '", "relevance_score": 0.95, "quality_score": 0.9, "credibility_score": 0.95, "recency_score": 0.9, "completeness_score": 0.85, "composite_score": 0.91, "confidence": 0.9}',
                        '{"evidence_id": "' + str(self.outdated_evidence.id) + '", "relevance_score": 0.7, "quality_score": 0.7, "credibility_score": 0.8, "recency_score": 0.3, "completeness_score": 0.6, "composite_score": 0.64, "confidence": 0.75}'
                    ]
                
                mock_llm.side_effect = mock_responses
                
                result_state = await reranker_langgraph._calculate_scores_node(state)
                
                # Should apply strategy-specific scoring
                assert hasattr(result_state, 'evidence_scores')
                assert len(result_state.evidence_scores) == 2
                
                # Verify scores reflect strategy
                high_score = next(s for s in result_state.evidence_scores if s.evidence_id == str(self.high_relevance_evidence.id))
                old_score = next(s for s in result_state.evidence_scores if s.evidence_id == str(self.outdated_evidence.id))
                
                # High relevance evidence should generally score higher
                assert high_score.composite_score >= old_score.composite_score


class TestM8Integration:
    """Integration tests for M8 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="What are the latest developments in artificial intelligence for healthcare?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_large_evidence_set(self):
        """Test M8 integration with large set of evidence."""
        # Create 8 evidence items with varying characteristics
        evidence_items = []
        
        contents_and_scores = [
            ("AI-powered diagnostic imaging systems achieved 95% accuracy in detecting early-stage cancers in 2024 clinical trials.", 0.95, "2024"),
            ("Machine learning algorithms help radiologists identify patterns in medical images more efficiently.", 0.85, "2023"),
            ("Healthcare AI applications include diagnostic support, drug discovery, and personalized treatment plans.", 0.8, "2023"),
            ("Artificial intelligence in medicine has shown promising results in various applications.", 0.6, "2022"),
            ("AI systems can process large amounts of medical data to support clinical decision-making.", 0.75, "2023"),
            ("Recent advances in deep learning have improved medical image analysis capabilities significantly.", 0.9, "2024"),
            ("Healthcare professionals are increasingly adopting AI tools to enhance patient care quality.", 0.7, "2022"),
            ("AI-assisted surgery robots provide precision and reduce human error in complex procedures.", 0.88, "2024")
        ]
        
        for i, (content, score, year) in enumerate(contents_and_scores):
            evidence = EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content=content,
                title=f"AI Healthcare Development {i+1}",
                score_raw=score,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base if i % 2 == 0 else SourceType.web_search,
                    source_id=f"healthcare_ai_db_{year}",
                    doc_id=f"ai_dev_{i+1}_{year}",
                    chunk_id=f"chunk_{i+1}"
                )
            )
            evidence_items.append(evidence)
        
        state = ReactorState(original_query=self.user_query)
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:
            # Mock responses for large evidence set
            analysis_response = '{"query_complexity": "high", "domain_specificity": "specialized", "ranking_requirements": ["relevance", "recency", "quality"], "adaptive_strategy": "latest_developments_focused", "weight_adjustments": {"relevance": 0.35, "quality": 0.25, "recency": 0.3, "credibility": 0.1}}'
            
            scoring_responses = []
            for i, (_, score, year) in enumerate(contents_and_scores):
                recency_score = 0.9 if year == "2024" else 0.7 if year == "2023" else 0.5
                composite = (score * 0.35) + (score * 0.25) + (recency_score * 0.3) + (0.8 * 0.1)
                scoring_responses.append(f'{{"evidence_id": "{evidence_items[i].id}", "relevance_score": {score}, "quality_score": {score}, "credibility_score": 0.8, "recency_score": {recency_score}, "completeness_score": {score-0.1}, "composite_score": {composite:.2f}, "confidence": 0.8}}')\n            \n            ranking_response = '{"algorithm_used": "adaptive_weighted", "total_items": 8, "ranking_factors": ["relevance", "recency", "quality", "credibility"], "score_distribution": {"high": 3, "medium": 4, "low": 1}, "ranking_quality": 0.85, "confidence": 0.8}'\n            validation_response = '{"validation_method": "comprehensive_check", "ranking_consistency": 0.9, "top_items_quality": 0.92, "diversity_score": 0.75, "validation_issues": [], "confidence": 0.85}'\n            \n            mock_responses = [analysis_response] + scoring_responses + [ranking_response, validation_response]\n            mock_llm.side_effect = mock_responses\n            \n            result_state = await reranker_langgraph.execute(state)\n            \n            # Should handle large evidence set effectively\n            assert result_state is not None\n            assert len(result_state.evidences) == 8\n            assert hasattr(result_state, 'evidence_scores')\n            assert hasattr(result_state, 'ranking_calculation')\n            \n            # Check that recent, high-quality evidence is ranked higher\n            top_evidence = result_state.evidences[0]\n            # Should be one of the 2024 high-score items\n            assert "2024" in top_evidence.provenance.doc_id\n    \n    @pytest.mark.asyncio\n    async def test_integration_with_similar_scores(self):
        \"\"\"Test M8 behavior with evidence having similar scores.\"\"\"\n        # Create evidence with very similar initial scores\n        similar_evidence = []\n        for i in range(4):\n            evidence = EvidenceItem(\n                workunit_id=uuid4(),\n                user_id=self.user_query.user_id,\n                conversation_id=self.user_query.conversation_id,\n                content=f\"AI healthcare application {i+1} shows promising results in clinical settings.\",\n                title=f\"AI Healthcare Study {i+1}\",\n                score_raw=0.75 + i * 0.01,  # Very similar scores: 0.75, 0.76, 0.77, 0.78\n                provenance=Provenance(\n                    source_type=SourceType.knowledge_base,\n                    source_id=f\"study_db_{i+1}\",\n                    doc_id=f\"study_{i+1}\",\n                    chunk_id=f\"chunk_{i+1}\"\n                )\n            )\n            similar_evidence.append(evidence)\n        \n        state = ReactorState(original_query=self.user_query)\n        for evidence in similar_evidence:\n            state.add_evidence(evidence)\n        \n        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:\n            # Mock responses for similar evidence\n            mock_responses = [\n                '{"query_complexity": "medium", "domain_specificity": "technical", "ranking_requirements": ["relevance", "quality"], "adaptive_strategy": "fine_grained_analysis", "weight_adjustments": {"relevance": 0.4, "quality": 0.3, "credibility": 0.2, "completeness": 0.1}}',\n                # Slightly different scores to create ranking\n                f'{{"evidence_id": "{similar_evidence[0].id}", "relevance_score": 0.76, "quality_score": 0.75, "credibility_score": 0.8, "recency_score": 0.8, "completeness_score": 0.7, "composite_score": 0.76, "confidence": 0.8}}',\n                f'{{"evidence_id": "{similar_evidence[1].id}", "relevance_score": 0.78, "quality_score": 0.77, "credibility_score": 0.8, "recency_score": 0.8, "completeness_score": 0.72, "composite_score": 0.78, "confidence": 0.8}}',\n                f'{{"evidence_id": "{similar_evidence[2].id}", "relevance_score": 0.75, "quality_score": 0.76, "credibility_score": 0.8, "recency_score": 0.8, "completeness_score": 0.71, "composite_score": 0.75, "confidence": 0.8}}',\n                f'{{"evidence_id": "{similar_evidence[3].id}", "relevance_score": 0.79, "quality_score": 0.78, "credibility_score": 0.8, "recency_score": 0.8, "completeness_score": 0.73, "composite_score": 0.79, "confidence": 0.8}}',\n                '{"algorithm_used": "fine_grained_ranking", "total_items": 4, "ranking_factors": ["relevance", "quality", "credibility"], "score_distribution": {"high": 4}, "ranking_quality": 0.8, "confidence": 0.8}',\n                '{"validation_method": "similarity_handling", "ranking_consistency": 0.85, "top_items_quality": 0.8, "diversity_score": 0.6, "validation_issues": ["Similar score clustering"], "confidence": 0.8}'\n            ]\n            mock_llm.side_effect = mock_responses\n            \n            result_state = await reranker_langgraph.execute(state)\n            \n            # Should handle similar scores appropriately\n            assert result_state is not None\n            assert len(result_state.evidences) == 4\n            \n            # Check that ranking validation identified the similarity issue\n            if hasattr(result_state, 'ranking_validation'):\n                validation = result_state.ranking_validation\n                assert "Similar score clustering" in validation.validation_issues\n    \n    @pytest.mark.asyncio\n    async def test_performance_metrics(self):\n        \"\"\"Test that performance metrics are recorded.\"\"\"\n        # Create moderate evidence set for performance testing\n        evidence_items = []\n        for i in range(6):\n            evidence = EvidenceItem(\n                workunit_id=uuid4(),\n                user_id=self.user_query.user_id,\n                conversation_id=self.user_query.conversation_id,\n                content=f\"Performance test evidence {i} for AI healthcare ranking.\",\n                title=f\"Performance Test {i}\",\n                score_raw=0.6 + i * 0.05,\n                provenance=Provenance(\n                    source_type=SourceType.knowledge_base,\n                    source_id="perf_test_db",\n                    doc_id=f"perf_{i}"\n                )\n            )\n            evidence_items.append(evidence)\n        \n        state = ReactorState(original_query=self.user_query)\n        for evidence in evidence_items:\n            state.add_evidence(evidence)\n        \n        with patch.object(reranker_langgraph, '_call_llm') as mock_llm:\n            # Mock responses for performance test\n            mock_responses = [\n                '{"query_complexity": "medium", "domain_specificity": "technical", "ranking_requirements": ["relevance"], "adaptive_strategy": "performance_test", "weight_adjustments": {"relevance": 1.0}}'\n            ]\n            \n            # Add scoring responses\n            for i, evidence in enumerate(evidence_items):\n                score = 0.6 + i * 0.05\n                mock_responses.append(f'{{"evidence_id": "{evidence.id}", "relevance_score": {score}, "quality_score": {score}, "credibility_score": 0.8, "recency_score": 0.8, "completeness_score": {score}, "composite_score": {score}, "confidence": 0.8}}')\n            \n            mock_responses.extend([\n                '{"algorithm_used": "performance_ranking", "total_items": 6, "ranking_factors": ["relevance"], "score_distribution": {"varied": 6}, "ranking_quality": 0.8, "confidence": 0.8}',\n                '{"validation_method": "performance_validation", "ranking_consistency": 0.9, "top_items_quality": 0.85, "diversity_score": 0.7, "validation_issues": [], "confidence": 0.8}'\n            ])\n            \n            mock_llm.side_effect = mock_responses\n            \n            result_state = await reranker_langgraph.execute(state)\n            \n            # Check that ranking was performed successfully\n            assert result_state is not None\n            assert len(result_state.evidences) == 6\n            assert hasattr(result_state, 'ranking_calculation')\n            \n            ranking = result_state.ranking_calculation\n            assert ranking.total_items == 6\n            assert ranking.ranking_quality > 0.0\n    \n    @pytest.mark.asyncio\n    async def test_ranking_stability(self):\n        \"\"\"Test ranking stability with repeated execution.\"\"\"\n        # Create consistent evidence set\n        stable_evidence = [\n            EvidenceItem(\n                workunit_id=uuid4(),\n                user_id=self.user_query.user_id,\n                conversation_id=self.user_query.conversation_id,\n                content=\"High-quality AI healthcare research with comprehensive data analysis.\",\n                title=\"High Quality Research\",\n                score_raw=0.9,\n                provenance=Provenance(\n                    source_type=SourceType.knowledge_base,\n                    source_id=\"research_db\",\n                    doc_id=\"high_quality_001\"\n                )\n            ),\n            EvidenceItem(\n                workunit_id=uuid4(),\n                user_id=self.user_query.user_id,\n                conversation_id=self.user_query.conversation_id,\n                content=\"Medium-quality overview of AI applications in healthcare settings.\",\n                title=\"Medium Quality Overview\",\n                score_raw=0.7,\n                provenance=Provenance(\n                    source_type=SourceType.web_search,\n                    source_id=\"web_source\",\n                    doc_id=\"medium_quality_001\"\n                )\n            )\n        ]\n        \n        ranking_results = []\n        \n        for run in range(2):  # Run twice to check stability\n            state = ReactorState(original_query=self.user_query)\n            for evidence in stable_evidence:\n                state.add_evidence(evidence)\n            \n            with patch.object(reranker_langgraph, '_call_llm') as mock_llm:\n                # Consistent mock responses\n                mock_responses = [\n                    '{"query_complexity": "medium", "domain_specificity": "technical", "ranking_requirements": ["relevance", "quality"], "adaptive_strategy": "stability_test", "weight_adjustments": {"relevance": 0.5, "quality": 0.5}}',\n                    f'{{"evidence_id": "{stable_evidence[0].id}", "relevance_score": 0.9, "quality_score": 0.9, "credibility_score": 0.9, "recency_score": 0.8, "completeness_score": 0.85, "composite_score": 0.9, "confidence": 0.9}}',\n                    f'{{"evidence_id": "{stable_evidence[1].id}", "relevance_score": 0.7, "quality_score": 0.7, "credibility_score": 0.7, "recency_score": 0.8, "completeness_score": 0.65, "composite_score": 0.7, "confidence": 0.8}}',\n                    '{"algorithm_used": "stable_ranking", "total_items": 2, "ranking_factors": ["relevance", "quality"], "score_distribution": {"high": 1, "medium": 1}, "ranking_quality": 0.85, "confidence": 0.85}',\n                    '{"validation_method": "stability_check", "ranking_consistency": 0.95, "top_items_quality": 0.9, "diversity_score": 0.8, "validation_issues": [], "confidence": 0.9}'\n                ]\n                mock_llm.side_effect = mock_responses\n                \n                result_state = await reranker_langgraph.execute(state)\n                ranking_results.append([e.id for e in result_state.evidences])\n        \n        # Rankings should be consistent across runs\n        assert len(ranking_results) == 2\n        assert ranking_results[0] == ranking_results[1]  # Same order both times\n        # High quality evidence should be first\n        assert ranking_results[0][0] == stable_evidence[0].id