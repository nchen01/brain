"""Tests for M7 Evidence Aggregator LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m7_evidence_aggregator_langgraph import (
    evidence_aggregator_langgraph,
    EvidenceAggregatorLangGraph,
    EvidenceCollection,
    DeduplicationResults,
    SourceMerging,
    ConsistencyValidation
)


class TestM7EvidenceAggregatorLangGraph:
    """Test suite for M7 Evidence Aggregator LangGraph implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        
        # Create test user query
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            text="What are the environmental benefits of renewable energy?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test evidence items with potential duplicates and overlaps
        self.evidence1 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Renewable energy sources like solar and wind power produce electricity without greenhouse gas emissions during operation.",
            title="Clean Energy Environmental Benefits",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="energy_research_db",
                doc_id="doc_001",
                chunk_id="chunk_001"
            )
        )
        
        # Similar content (potential duplicate)
        self.evidence2 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Solar and wind energy generate clean electricity without producing greenhouse gases during their operation phase.",
            title="Renewable Energy Clean Generation",
            score_raw=0.85,
            provenance=Provenance(
                source_type=SourceType.web_search,
                source_id="web_search",
                doc_id="doc_002",
                chunk_id="chunk_002"
            )
        )
        
        # Complementary content
        self.evidence3 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Renewable energy reduces air pollution and helps combat climate change by decreasing reliance on fossil fuels.",
            title="Renewable Energy Climate Impact",
            score_raw=0.88,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="climate_db",
                doc_id="doc_003",
                chunk_id="chunk_003"
            )
        )
        
        # Different perspective
        self.evidence4 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="While renewable energy has environmental benefits, the manufacturing of solar panels and wind turbines does have some environmental impact.",
            title="Renewable Energy Manufacturing Impact",
            score_raw=0.75,
            provenance=Provenance(
                source_type=SourceType.web_search,
                source_id="environmental_analysis",
                doc_id="doc_004",
                chunk_id="chunk_004"
            )
        )
        
        # Create test state with evidence
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.add_evidence(self.evidence1)
        self.initial_state.add_evidence(self.evidence2)
        self.initial_state.add_evidence(self.evidence3)
        self.initial_state.add_evidence(self.evidence4)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M7 execution with evidence aggregation."""
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Collection analysis
                '{"total_evidence": 4, "source_distribution": {"energy_research_db": 1, "web_search": 2, "climate_db": 1}, "quality_distribution": {"high": 3, "medium": 1}, "coverage_analysis": "Good coverage of environmental benefits", "confidence": 0.85}',
                # Deduplication
                '{"original_count": 4, "duplicate_count": 1, "final_count": 3, "duplicate_pairs": [{"id1": "' + str(self.evidence1.id) + '", "id2": "' + str(self.evidence2.id) + '"}], "deduplication_method": "semantic_similarity", "confidence": 0.8}',
                # Source merging
                '{"merged_groups": [{"group_id": "env_benefits", "evidence_ids": ["' + str(self.evidence1.id) + '", "' + str(self.evidence3.id) + '"]}], "merge_strategies": ["complementary_synthesis"], "quality_improvements": {"env_benefits": 0.1}, "information_gain": 0.15, "confidence": 0.8}',
                # Consistency validation
                '{"consistency_score": 0.85, "conflicting_evidence": [], "consensus_items": ["' + str(self.evidence1.id) + '", "' + str(self.evidence3.id) + '"], "uncertainty_areas": ["manufacturing_impact"], "validation_method": "cross_source_validation", "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await evidence_aggregator_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'evidence_collection')
            assert hasattr(result_state, 'deduplication_results')
            
            # Check that some aggregation occurred
            assert len(result_state.evidences) <= 4  # May have been deduplicated
    
    @pytest.mark.asyncio
    async def test_collect_evidence_node(self):
        """Test evidence collection analysis node."""
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "total_evidence": 4,\n                "source_distribution": {"energy_research_db": 1, "web_search": 2, "climate_db": 1},\n                "quality_distribution": {"high": 3, "medium": 1, "low": 0},\n                "coverage_analysis": "Comprehensive coverage of renewable energy environmental benefits with multiple perspectives",\n                "confidence": 0.9\n            }'
            
            result_state = await evidence_aggregator_langgraph._collect_evidence_node(self.initial_state)
            
            # Verify evidence collection analysis
            assert hasattr(result_state, 'evidence_collection')
            collection = result_state.evidence_collection
            
            assert collection.total_evidence == 4
            assert "energy_research_db" in collection.source_distribution
            assert "web_search" in collection.source_distribution
            assert "climate_db" in collection.source_distribution
            assert collection.source_distribution["web_search"] == 2
            assert "high" in collection.quality_distribution
            assert collection.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_deduplicate_node(self):
        """Test deduplication node."""
        # Set up state with evidence collection
        state_with_collection = ReactorState(original_query=self.user_query)
        state_with_collection.add_evidence(self.evidence1)
        state_with_collection.add_evidence(self.evidence2)  # Similar to evidence1
        state_with_collection.add_evidence(self.evidence3)
        state_with_collection.evidence_collection = EvidenceCollection(
            total_evidence=3,
            source_distribution={"energy_research_db": 1, "web_search": 1, "climate_db": 1},
            quality_distribution={"high": 3},
            coverage_analysis="Good coverage",
            confidence=0.8
        )
        
        with patch.object(evidence_aggregator_langgraph, '_identify_duplicates') as mock_identify:
            mock_identify.return_value = [(str(self.evidence1.id), str(self.evidence2.id))]
            
            result_state = await evidence_aggregator_langgraph._deduplicate_node(state_with_collection)
            
            # Verify deduplication results
            assert hasattr(result_state, 'deduplication_results')
            dedup = result_state.deduplication_results
            
            assert dedup.original_count == 3
            assert dedup.duplicate_count >= 0
            assert dedup.final_count <= dedup.original_count
            assert len(result_state.evidences) <= 3  # Some may have been removed
    
    @pytest.mark.asyncio
    async def test_merge_sources_node(self):
        """Test source merging node."""
        # Set up state with deduplication results
        state_with_dedup = ReactorState(original_query=self.user_query)
        state_with_dedup.add_evidence(self.evidence1)
        state_with_dedup.add_evidence(self.evidence3)
        state_with_dedup.deduplication_results = DeduplicationResults(
            original_count=4,
            duplicate_count=1,
            final_count=3,
            duplicate_pairs=[],
            deduplication_method="semantic_similarity",
            confidence=0.8
        )
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "merged_groups": [\n                    {\n                        "group_id": "environmental_benefits",\n                        "evidence_ids": ["' + str(self.evidence1.id) + '", "' + str(self.evidence3.id) + '"],\n                        "merge_type": "complementary"\n                    }\n                ],\n                "merge_strategies": ["complementary_synthesis", "cross_source_validation"],\n                "quality_improvements": {"environmental_benefits": 0.15},\n                "information_gain": 0.2,\n                "confidence": 0.85\n            }'
            
            result_state = await evidence_aggregator_langgraph._merge_sources_node(state_with_dedup)
            
            # Verify source merging results
            assert hasattr(result_state, 'source_merging')
            merging = result_state.source_merging
            
            assert len(merging.merged_groups) > 0
            assert "complementary_synthesis" in merging.merge_strategies
            assert merging.information_gain > 0.0
            assert merging.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_validate_consistency_node(self):
        """Test consistency validation node."""
        # Set up state with source merging
        state_with_merging = ReactorState(original_query=self.user_query)
        state_with_merging.add_evidence(self.evidence1)
        state_with_merging.add_evidence(self.evidence3)
        state_with_merging.add_evidence(self.evidence4)  # Potentially conflicting
        state_with_merging.source_merging = SourceMerging(
            merged_groups=[{"group_id": "env_benefits", "evidence_ids": [str(self.evidence1.id)]}],
            merge_strategies=["synthesis"],
            quality_improvements={"env_benefits": 0.1},
            information_gain=0.15,
            confidence=0.8
        )
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "consistency_score": 0.75,\n                "conflicting_evidence": [\n                    {\n                        "evidence_id": "' + str(self.evidence4.id) + '",\n                        "conflict_type": "perspective_difference",\n                        "description": "Mentions manufacturing impact while others focus on operational benefits"\n                    }\n                ],\n                "consensus_items": ["' + str(self.evidence1.id) + '", "' + str(self.evidence3.id) + '"],\n                "uncertainty_areas": ["manufacturing_lifecycle_impact"],\n                "validation_method": "cross_source_consistency_check",\n                "confidence": 0.8\n            }'
            
            result_state = await evidence_aggregator_langgraph._validate_consistency_node(state_with_merging)
            
            # Verify consistency validation results
            assert hasattr(result_state, 'consistency_validation')
            validation = result_state.consistency_validation
            
            assert 0.0 <= validation.consistency_score <= 1.0
            assert len(validation.conflicting_evidence) >= 0
            assert len(validation.consensus_items) >= 0
            assert len(validation.uncertainty_areas) >= 0
            assert validation.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_no_evidence_handling(self):
        """Test handling when no evidence is available."""
        empty_state = ReactorState(original_query=self.user_query)
        # No evidence added
        
        result_state = await evidence_aggregator_langgraph.execute(empty_state)
        
        # Should handle gracefully
        assert result_state is not None
        assert len(result_state.evidences) == 0
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise an exception
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await evidence_aggregator_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback aggregation
            assert result_state is not None
            assert len(result_state.evidences) > 0
            # May have fallback collection analysis
            if hasattr(result_state, 'evidence_collection'):
                assert result_state.evidence_collection.total_evidence > 0
    
    def test_evidence_collection_pydantic_model(self):
        """Test EvidenceCollection Pydantic model validation."""
        # Valid data
        valid_data = {
            "total_evidence": 5,
            "source_distribution": {"source1": 3, "source2": 2},
            "quality_distribution": {"high": 3, "medium": 2, "low": 0},
            "coverage_analysis": "Comprehensive coverage of the topic with multiple perspectives",
            "confidence": 0.85
        }
        collection = EvidenceCollection(**valid_data)
        assert collection.total_evidence == 5
        assert collection.source_distribution["source1"] == 3
        assert collection.confidence == 0.85
        
        # Invalid data (negative count)
        with pytest.raises(Exception):  # Pydantic validation error
            EvidenceCollection(
                total_evidence=-1,  # Invalid: negative count
                source_distribution={},
                quality_distribution={},
                coverage_analysis="test",
                confidence=0.5
            )
    
    def test_deduplication_results_pydantic_model(self):
        """Test DeduplicationResults Pydantic model validation."""
        # Valid data
        valid_data = {
            "original_count": 10,
            "duplicate_count": 3,
            "final_count": 7,
            "duplicate_pairs": [{"id1": "item1", "id2": "item2"}],
            "deduplication_method": "semantic_similarity",
            "confidence": 0.8
        }
        dedup = DeduplicationResults(**valid_data)
        assert dedup.original_count == 10
        assert dedup.duplicate_count == 3
        assert dedup.final_count == 7
        assert len(dedup.duplicate_pairs) == 1
        
        # Test with no duplicates
        no_dup_data = {
            "original_count": 5,
            "duplicate_count": 0,
            "final_count": 5,
            "duplicate_pairs": [],
            "deduplication_method": "exact_match",
            "confidence": 0.9
        }
        no_dup = DeduplicationResults(**no_dup_data)
        assert no_dup.duplicate_count == 0
        assert len(no_dup.duplicate_pairs) == 0
    
    def test_source_merging_pydantic_model(self):
        """Test SourceMerging Pydantic model validation."""
        # Valid data
        valid_data = {
            "merged_groups": [
                {"group_id": "group1", "evidence_ids": ["e1", "e2"]},
                {"group_id": "group2", "evidence_ids": ["e3", "e4"]}
            ],
            "merge_strategies": ["complementary_synthesis", "cross_validation"],
            "quality_improvements": {"group1": 0.15, "group2": 0.1},
            "information_gain": 0.2,
            "confidence": 0.85
        }
        merging = SourceMerging(**valid_data)
        assert len(merging.merged_groups) == 2
        assert "complementary_synthesis" in merging.merge_strategies
        assert merging.quality_improvements["group1"] == 0.15
        assert merging.information_gain == 0.2
        
        # Invalid data (information gain too high)
        with pytest.raises(Exception):  # Pydantic validation error
            SourceMerging(
                merged_groups=[],
                merge_strategies=[],
                quality_improvements={},
                information_gain=1.5,  # Invalid: > 1.0
                confidence=0.8
            )
    
    def test_consistency_validation_pydantic_model(self):
        """Test ConsistencyValidation Pydantic model validation."""
        # Valid data
        valid_data = {
            "consistency_score": 0.8,
            "conflicting_evidence": [
                {"evidence_id": "e1", "conflict_type": "contradiction", "description": "Conflicting claims"}
            ],
            "consensus_items": ["e2", "e3", "e4"],
            "uncertainty_areas": ["manufacturing_impact", "long_term_effects"],
            "validation_method": "cross_source_validation",
            "confidence": 0.85
        }
        validation = ConsistencyValidation(**valid_data)
        assert validation.consistency_score == 0.8
        assert len(validation.conflicting_evidence) == 1
        assert len(validation.consensus_items) == 3
        assert "manufacturing_impact" in validation.uncertainty_areas
        
        # Test with no conflicts
        no_conflict_data = {
            "consistency_score": 0.95,
            "conflicting_evidence": [],
            "consensus_items": ["e1", "e2", "e3"],
            "uncertainty_areas": [],
            "validation_method": "unanimous_consensus",
            "confidence": 0.95
        }
        no_conflict = ConsistencyValidation(**no_conflict_data)
        assert len(no_conflict.conflicting_evidence) == 0
        assert no_conflict.consistency_score == 0.95
    
    def test_identify_duplicates(self):
        """Test duplicate identification utility."""
        evidence_list = [self.evidence1, self.evidence2, self.evidence3]
        
        # Mock the duplicate identification
        with patch.object(evidence_aggregator_langgraph, '_calculate_similarity') as mock_similarity:
            mock_similarity.return_value = 0.85  # High similarity between evidence1 and evidence2
            
            duplicates = evidence_aggregator_langgraph._identify_duplicates(evidence_list)
            
            assert isinstance(duplicates, list)
            # Should identify similar content as duplicates
            if len(duplicates) > 0:
                assert len(duplicates[0]) == 2  # Pair of duplicate IDs
    
    def test_calculate_similarity(self):
        """Test similarity calculation between evidence items."""
        similarity = evidence_aggregator_langgraph._calculate_similarity(self.evidence1, self.evidence2)
        
        assert 0.0 <= similarity <= 1.0
        # Evidence1 and evidence2 have similar content, should have high similarity
        assert similarity > 0.5
        
        # Different evidence should have lower similarity
        similarity_diff = evidence_aggregator_langgraph._calculate_similarity(self.evidence1, self.evidence4)
        assert similarity_diff < similarity
    
    def test_merge_evidence_content(self):
        """Test evidence content merging utility."""
        evidence_group = [self.evidence1, self.evidence3]
        
        merged_content = evidence_aggregator_langgraph._merge_evidence_content(evidence_group)
        
        assert isinstance(merged_content, str)
        assert len(merged_content) > 0
        # Should contain information from both evidence items
        assert "renewable energy" in merged_content.lower()
        assert "greenhouse gas" in merged_content.lower() or "climate" in merged_content.lower()
    
    @pytest.mark.asyncio
    async def test_different_aggregation_scenarios(self):
        """Test aggregation with different evidence scenarios."""
        scenarios = [
            # Scenario 1: All similar evidence (high duplication)
            [self.evidence1, self.evidence2],
            # Scenario 2: All different evidence (no duplication)
            [self.evidence1, self.evidence3, self.evidence4],
            # Scenario 3: Mixed evidence (some duplication)
            [self.evidence1, self.evidence2, self.evidence3, self.evidence4]
        ]
        
        for i, evidence_list in enumerate(scenarios):
            state = ReactorState(original_query=self.user_query)
            for evidence in evidence_list:
                state.add_evidence(evidence)
            
            with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
                # Mock responses based on scenario
                if i == 0:  # High duplication
                    mock_responses = [
                        f'{{"total_evidence": {len(evidence_list)}, "source_distribution": {{"test": {len(evidence_list)}}}, "quality_distribution": {{"high": {len(evidence_list)}}}, "coverage_analysis": "Similar content", "confidence": 0.8}}',
                        f'{{"original_count": {len(evidence_list)}, "duplicate_count": 1, "final_count": {len(evidence_list)-1}, "duplicate_pairs": [], "deduplication_method": "similarity", "confidence": 0.9}}',
                        '{"merged_groups": [], "merge_strategies": [], "quality_improvements": {}, "information_gain": 0.1, "confidence": 0.7}',
                        '{"consistency_score": 0.9, "conflicting_evidence": [], "consensus_items": [], "uncertainty_areas": [], "validation_method": "consensus", "confidence": 0.9}'
                    ]
                else:  # Low/no duplication
                    mock_responses = [
                        f'{{"total_evidence": {len(evidence_list)}, "source_distribution": {{"test": {len(evidence_list)}}}, "quality_distribution": {{"high": {len(evidence_list)}}}, "coverage_analysis": "Diverse content", "confidence": 0.8}}',
                        f'{{"original_count": {len(evidence_list)}, "duplicate_count": 0, "final_count": {len(evidence_list)}, "duplicate_pairs": [], "deduplication_method": "similarity", "confidence": 0.8}}',
                        '{"merged_groups": [], "merge_strategies": ["synthesis"], "quality_improvements": {}, "information_gain": 0.2, "confidence": 0.8}',
                        '{"consistency_score": 0.8, "conflicting_evidence": [], "consensus_items": [], "uncertainty_areas": [], "validation_method": "cross_validation", "confidence": 0.8}'
                    ]
                
                mock_llm.side_effect = mock_responses
                
                result_state = await evidence_aggregator_langgraph.execute(state)
                
                # Should handle all scenarios appropriately
                assert result_state is not None
                assert len(result_state.evidences) > 0
                if hasattr(result_state, 'deduplication_results'):
                    dedup = result_state.deduplication_results
                    assert dedup.final_count <= dedup.original_count


class TestM7Integration:
    """Integration tests for M7 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="What are the advantages and disadvantages of electric vehicles?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_large_evidence_set(self):
        """Test M7 integration with large set of evidence."""
        # Create a larger set of evidence with various characteristics
        evidence_items = []
        
        # Create 10 evidence items with some duplicates and overlaps
        base_contents = [
            "Electric vehicles produce zero direct emissions and help reduce air pollution in urban areas.",
            "EVs have zero tailpipe emissions and contribute to cleaner air in cities.",  # Similar to above
            "Electric cars have lower operating costs due to cheaper electricity compared to gasoline.",
            "The cost of charging an electric vehicle is significantly less than fueling a gas car.",  # Similar to above
            "Electric vehicles have limited driving range compared to traditional gasoline vehicles.",
            "Battery technology in EVs is improving rapidly, with new models offering 300+ mile range.",
            "Charging infrastructure for electric vehicles is still developing in many regions.",
            "The environmental impact of EV battery production includes mining of lithium and cobalt.",
            "Electric vehicles offer instant torque and smooth acceleration performance.",
            "Government incentives and tax credits make electric vehicles more affordable for consumers."
        ]
        
        for i, content in enumerate(base_contents):
            evidence = EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content=content,
                title=f"EV Evidence {i+1}",
                score_raw=0.7 + (i % 3) * 0.1,  # Varying quality scores
                provenance=Provenance(
                    source_type=SourceType.knowledge_base if i % 2 == 0 else SourceType.web_search,
                    source_id=f"source_{i % 3}",  # Multiple sources
                    doc_id=f"doc_{i}",
                    chunk_id=f"chunk_{i}"
                )
            )
            evidence_items.append(evidence)
        
        state = ReactorState(original_query=self.user_query)
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            # Mock responses for large evidence set
            mock_responses = [
                '{"total_evidence": 10, "source_distribution": {"source_0": 4, "source_1": 3, "source_2": 3}, "quality_distribution": {"high": 6, "medium": 4}, "coverage_analysis": "Comprehensive coverage of EV advantages and disadvantages", "confidence": 0.85}',
                '{"original_count": 10, "duplicate_count": 2, "final_count": 8, "duplicate_pairs": [{"id1": "ev1", "id2": "ev2"}, {"id1": "ev3", "id2": "ev4"}], "deduplication_method": "semantic_similarity", "confidence": 0.8}',
                '{"merged_groups": [{"group_id": "environmental", "evidence_ids": ["ev1", "ev8"]}, {"group_id": "economic", "evidence_ids": ["ev3", "ev10"]}], "merge_strategies": ["thematic_grouping", "cross_source_validation"], "quality_improvements": {"environmental": 0.1, "economic": 0.15}, "information_gain": 0.25, "confidence": 0.8}',
                '{"consistency_score": 0.75, "conflicting_evidence": [{"evidence_id": "ev5", "conflict_type": "range_limitation", "description": "Conflicts with range improvement claims"}], "consensus_items": ["ev1", "ev3", "ev9"], "uncertainty_areas": ["charging_infrastructure", "battery_lifecycle"], "validation_method": "multi_source_consensus", "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await evidence_aggregator_langgraph.execute(state)
            
            # Should handle large evidence set effectively
            assert result_state is not None
            assert hasattr(result_state, 'evidence_collection')
            assert hasattr(result_state, 'deduplication_results')
            
            # Check aggregation results
            collection = result_state.evidence_collection
            assert collection.total_evidence == 10
            
            dedup = result_state.deduplication_results
            assert dedup.final_count <= dedup.original_count
            assert dedup.duplicate_count >= 0
    
    @pytest.mark.asyncio
    async def test_integration_with_conflicting_evidence(self):
        """Test M7 behavior with conflicting evidence."""
        # Create evidence with conflicting information
        conflicting_evidence = [
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Electric vehicles are significantly more expensive than gasoline cars, making them unaffordable for most consumers.",
                title="EV Cost Concerns",
                score_raw=0.7,
                provenance=Provenance(
                    source_type=SourceType.web_search,
                    source_id="cost_analysis_blog",
                    doc_id="cost_001"
                )
            ),
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="With government incentives and decreasing battery costs, electric vehicles are becoming price-competitive with traditional cars.",
                title="EV Affordability Trends",
                score_raw=0.8,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="automotive_research_db",
                    doc_id="trends_001"
                )
            ),
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Electric vehicle charging takes much longer than refueling a gas car, creating inconvenience for long trips.",
                title="EV Charging Limitations",
                score_raw=0.75,
                provenance=Provenance(
                    source_type=SourceType.web_search,
                    source_id="travel_blog",
                    doc_id="charging_001"
                )
            )
        ]
        
        state = ReactorState(original_query=self.user_query)
        for evidence in conflicting_evidence:
            state.add_evidence(evidence)
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"total_evidence": 3, "source_distribution": {"web_search": 2, "knowledge_base": 1}, "quality_distribution": {"high": 2, "medium": 1}, "coverage_analysis": "Mixed perspectives on EV costs and charging", "confidence": 0.8}',
                '{"original_count": 3, "duplicate_count": 0, "final_count": 3, "duplicate_pairs": [], "deduplication_method": "semantic_similarity", "confidence": 0.8}',
                '{"merged_groups": [], "merge_strategies": ["conflict_preservation"], "quality_improvements": {}, "information_gain": 0.1, "confidence": 0.7}',
                f'{{"consistency_score": 0.6, "conflicting_evidence": [{{"evidence_id": "{conflicting_evidence[0].id}", "conflict_type": "cost_disagreement", "description": "Conflicting views on EV affordability"}}, {{"evidence_id": "{conflicting_evidence[2].id}", "conflict_type": "charging_concern", "description": "Highlights charging limitations"}}], "consensus_items": [], "uncertainty_areas": ["cost_trends", "charging_convenience"], "validation_method": "conflict_identification", "confidence": 0.8}}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await evidence_aggregator_langgraph.execute(state)
            
            # Should identify and handle conflicts appropriately
            assert result_state is not None
            assert hasattr(result_state, 'consistency_validation')
            
            validation = result_state.consistency_validation
            assert validation.consistency_score < 0.8  # Lower due to conflicts
            assert len(validation.conflicting_evidence) > 0
            assert len(validation.uncertainty_areas) > 0
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded."""
        # Create moderate evidence set for performance testing
        evidence_items = []
        for i in range(5):
            evidence = EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content=f"Test evidence content {i} for performance measurement.",
                title=f"Performance Test Evidence {i}",
                score_raw=0.7 + i * 0.05,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="perf_test_db",
                    doc_id=f"perf_{i}"
                )
            )
            evidence_items.append(evidence)
        
        state = ReactorState(original_query=self.user_query)
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"total_evidence": 5, "source_distribution": {"perf_test_db": 5}, "quality_distribution": {"high": 5}, "coverage_analysis": "Performance test coverage", "confidence": 0.8}',
                '{"original_count": 5, "duplicate_count": 0, "final_count": 5, "duplicate_pairs": [], "deduplication_method": "exact_match", "confidence": 0.9}',
                '{"merged_groups": [], "merge_strategies": ["no_merge_needed"], "quality_improvements": {}, "information_gain": 0.05, "confidence": 0.8}',
                '{"consistency_score": 0.9, "conflicting_evidence": [], "consensus_items": ["all"], "uncertainty_areas": [], "validation_method": "performance_test", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await evidence_aggregator_langgraph.execute(state)
            
            # Check that aggregation was performed successfully
            assert result_state is not None
            assert hasattr(result_state, 'evidence_collection')
            assert result_state.evidence_collection.total_evidence == 5
    
    @pytest.mark.asyncio
    async def test_aggregation_quality_improvement(self):
        """Test that aggregation improves overall evidence quality."""
        # Create evidence that can benefit from aggregation
        complementary_evidence = [
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Electric vehicles reduce greenhouse gas emissions.",
                title="EV Environmental Benefits - Basic",
                score_raw=0.6,
                provenance=Provenance(
                    source_type=SourceType.web_search,
                    source_id="basic_source",
                    doc_id="basic_001"
                )
            ),
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Studies show EVs reduce CO2 emissions by 60-70% compared to gasoline vehicles when accounting for electricity generation.",
                title="EV Environmental Benefits - Detailed",
                score_raw=0.9,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="research_db",
                    doc_id="study_001"
                )
            )
        ]
        
        state = ReactorState(original_query=self.user_query)
        for evidence in complementary_evidence:
            state.add_evidence(evidence)
        
        with patch.object(evidence_aggregator_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"total_evidence": 2, "source_distribution": {"web_search": 1, "knowledge_base": 1}, "quality_distribution": {"high": 1, "medium": 1}, "coverage_analysis": "Complementary information on EV emissions", "confidence": 0.8}',
                '{"original_count": 2, "duplicate_count": 0, "final_count": 2, "duplicate_pairs": [], "deduplication_method": "semantic_similarity", "confidence": 0.8}',
                f'{{"merged_groups": [{{"group_id": "emissions_benefits", "evidence_ids": ["{complementary_evidence[0].id}", "{complementary_evidence[1].id}"], "merge_type": "complementary"}}], "merge_strategies": ["detail_enhancement"], "quality_improvements": {{"emissions_benefits": 0.2}}, "information_gain": 0.3, "confidence": 0.85}}',
                '{"consistency_score": 0.9, "conflicting_evidence": [], "consensus_items": ["emissions_reduction"], "uncertainty_areas": [], "validation_method": "complementary_validation", "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await evidence_aggregator_langgraph.execute(state)
            
            # Should show quality improvement through merging
            assert result_state is not None
            assert hasattr(result_state, 'source_merging')
            
            merging = result_state.source_merging
            assert merging.information_gain > 0.0
            if "emissions_benefits" in merging.quality_improvements:
                assert merging.quality_improvements["emissions_benefits"] > 0.0