"""Tests for M12 Interaction Answer LangGraph implementation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, Answer, Citation, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m12_interaction_answer_langgraph import (
    interaction_answer_langgraph,
    InteractionAnswerLangGraph,
    AnswerFormatting,
    MetadataEnrichment,
    OutputValidation,
    DeliveryResponse
)


class TestM12InteractionAnswerLangGraph:
    """Test suite for M12 Interaction Answer LangGraph implementation."""
    
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
            text="How do electric vehicles contribute to reducing carbon emissions?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        # Create test citations
        self.citation1 = Citation(
            source="ev_emissions_study",
            text="EVs reduce lifecycle carbon emissions by 60-70% compared to gasoline vehicles",
            url="https://example.com/ev-emissions",
            doc_id="emissions_001"
        )
        
        self.citation2 = Citation(
            source="transportation_research",
            text="Electric vehicles produce zero direct emissions during operation",
            url="https://example.com/transport-research",
            doc_id="transport_001"
        )
        
        # Create comprehensive test answer
        self.test_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="Electric vehicles contribute significantly to reducing carbon emissions through multiple mechanisms. During operation, EVs produce zero direct emissions, unlike gasoline vehicles that emit CO2 and other pollutants. Lifecycle analysis shows that electric vehicles reduce overall carbon emissions by 60-70% compared to conventional gasoline vehicles, even accounting for electricity generation and battery manufacturing. As the electrical grid becomes cleaner with more renewable energy sources, the carbon footprint of EVs continues to decrease. Additionally, EVs are more energy-efficient, converting about 77% of electrical energy to power at the wheels compared to only 12-30% efficiency for gasoline vehicles.",
            citations=[self.citation1, self.citation2],
            limitations=["Emissions depend on local electricity grid composition", "Battery manufacturing has environmental impact"],
            confidence=0.88
        )
        
        # Create test evidence for context
        self.evidence1 = EvidenceItem(
            workunit_id=uuid4(),
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content="Electric vehicles produce zero direct emissions during operation, contributing to cleaner air in urban areas.",
            title="EV Direct Emissions",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.knowledge_base,
                source_id="ev_emissions_study",
                doc_id="emissions_001"
            )
        )
        
        # Create test state with final answer
        self.initial_state = ReactorState(original_query=self.user_query)
        self.initial_state.final_answer = self.test_answer
        self.initial_state.add_evidence(self.evidence1)
        
        # Add some quality metrics from previous modules
        self.initial_state.answer_quality_score = 0.85
    
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic M12 execution with answer delivery."""
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            # Mock LLM responses for different nodes
            mock_responses = [
                # Answer formatting
                '{"format_type": "structured_narrative", "formatting_applied": ["paragraph_structure", "citation_integration", "readability_enhancement"], "readability_score": 0.85, "presentation_quality": "high", "user_experience_score": 0.88, "confidence": 0.85}',
                # Metadata enrichment
                '{"confidence_indicators": {"content": 0.88, "citations": 0.9, "completeness": 0.85}, "source_summary": {"knowledge_base": 1, "research_studies": 1}, "processing_metadata": {"modules_used": 12, "evidence_processed": 1}, "quality_metrics": {"accuracy": 0.9, "relevance": 0.88}, "timestamp_info": {"processing_time": "2.5s"}, "confidence": 0.85}',
                # Output validation
                '{"validation_checks": ["content_accuracy", "citation_validity", "format_consistency", "completeness"], "validation_results": {"content_accuracy": true, "citation_validity": true, "format_consistency": true, "completeness": true}, "output_quality_score": 0.9, "issues_found": [], "recommendations": [], "confidence": 0.9}',
                # Delivery response
                '{"delivery_status": "success", "response_time_ms": 2500, "processing_stages": {"formatting": 200, "metadata": 150, "validation": 100, "delivery": 50}, "final_answer_length": 650, "user_satisfaction_prediction": 0.85, "delivery_metrics": {"format_quality": 0.9}, "confidence": 0.9}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await interaction_answer_langgraph.execute(self.initial_state)
            
            # Verify basic execution
            assert result_state is not None
            assert hasattr(result_state, 'answer_formatting')
            assert hasattr(result_state, 'metadata_enrichment')
            assert hasattr(result_state, 'output_validation')
            assert hasattr(result_state, 'delivery_response')
            
            # Check that final answer is still present and potentially enhanced
            assert result_state.final_answer is not None
            assert result_state.final_answer.text != ""
    
    @pytest.mark.asyncio
    async def test_format_answer_node(self):
        """Test answer formatting node with Pydantic validation."""
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "format_type": "structured_narrative",\n                "formatting_applied": ["paragraph_breaks", "citation_integration", "bullet_point_highlights", "readability_optimization"],\n                "readability_score": 0.9,\n                "presentation_quality": "excellent",\n                "user_experience_score": 0.92,\n                "confidence": 0.88\n            }'
            
            result_state = await interaction_answer_langgraph._format_answer_node(self.initial_state)
            
            # Verify answer formatting results
            assert hasattr(result_state, 'answer_formatting')
            formatting = result_state.answer_formatting
            
            assert formatting.format_type == "structured_narrative"
            assert "paragraph_breaks" in formatting.formatting_applied
            assert "citation_integration" in formatting.formatting_applied
            assert formatting.readability_score == 0.9
            assert formatting.presentation_quality == "excellent"
            assert formatting.user_experience_score == 0.92
            assert formatting.confidence == 0.88
    
    @pytest.mark.asyncio
    async def test_add_metadata_node(self):
        """Test metadata enrichment node."""
        # Set up state with answer formatting
        state_with_formatting = ReactorState(original_query=self.user_query)
        state_with_formatting.final_answer = self.test_answer
        state_with_formatting.add_evidence(self.evidence1)
        state_with_formatting.answer_quality_score = 0.85
        state_with_formatting.answer_formatting = AnswerFormatting(
            format_type="structured_narrative",
            formatting_applied=["paragraph_structure", "citations"],
            readability_score=0.85,
            presentation_quality="high",
            user_experience_score=0.88,
            confidence=0.85
        )
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "confidence_indicators": {"content_accuracy": 0.88, "citation_quality": 0.9, "completeness": 0.85, "relevance": 0.9},\n                "source_summary": {"knowledge_base": 1, "research_studies": 1, "total_sources": 2},\n                "processing_metadata": {"modules_executed": 12, "evidence_items": 1, "processing_time_ms": 2500},\n                "quality_metrics": {"overall_quality": 0.85, "accuracy_score": 0.9, "citation_score": 0.9},\n                "timestamp_info": {"query_received": "2024-01-15T10:00:00Z", "processing_completed": "2024-01-15T10:00:02Z"},\n                "confidence": 0.88\n            }'
            
            result_state = await interaction_answer_langgraph._add_metadata_node(state_with_formatting)
            
            # Verify metadata enrichment results
            assert hasattr(result_state, 'metadata_enrichment')
            metadata = result_state.metadata_enrichment
            
            assert "content_accuracy" in metadata.confidence_indicators
            assert metadata.confidence_indicators["content_accuracy"] == 0.88
            assert "knowledge_base" in metadata.source_summary
            assert metadata.source_summary["total_sources"] == 2
            assert "modules_executed" in metadata.processing_metadata
            assert metadata.processing_metadata["modules_executed"] == 12
            assert "overall_quality" in metadata.quality_metrics
            assert metadata.confidence == 0.88
    
    @pytest.mark.asyncio
    async def test_validate_output_node(self):
        """Test output validation node."""
        # Set up state with metadata enrichment
        state_with_metadata = ReactorState(original_query=self.user_query)
        state_with_metadata.final_answer = self.test_answer
        state_with_metadata.metadata_enrichment = MetadataEnrichment(
            confidence_indicators={"content": 0.88, "citations": 0.9},
            source_summary={"knowledge_base": 1, "total": 1},
            processing_metadata={"modules": 12},
            quality_metrics={"accuracy": 0.9},
            timestamp_info={"completed": "2024-01-15T10:00:02Z"},
            confidence=0.88
        )
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "validation_checks": ["content_accuracy", "citation_validity", "format_consistency", "completeness", "readability"],\n                "validation_results": {"content_accuracy": true, "citation_validity": true, "format_consistency": true, "completeness": true, "readability": true},\n                "output_quality_score": 0.92,\n                "issues_found": [],\n                "recommendations": ["Consider adding economic impact information"],\n                "confidence": 0.9\n            }'
            
            result_state = await interaction_answer_langgraph._validate_output_node(state_with_metadata)
            
            # Verify output validation results
            assert hasattr(result_state, 'output_validation')
            validation = result_state.output_validation
            
            assert "content_accuracy" in validation.validation_checks
            assert "citation_validity" in validation.validation_checks
            assert validation.validation_results["content_accuracy"] == True
            assert validation.validation_results["citation_validity"] == True
            assert validation.output_quality_score == 0.92
            assert len(validation.issues_found) == 0
            assert "Consider adding economic impact information" in validation.recommendations
            assert validation.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_deliver_response_node(self):
        """Test response delivery node."""
        # Set up state with output validation
        state_with_validation = ReactorState(original_query=self.user_query)
        state_with_validation.final_answer = self.test_answer
        state_with_validation.delivery_start_time = time.time() * 1000 - 2500  # 2.5 seconds ago
        state_with_validation.output_validation = OutputValidation(
            validation_checks=["accuracy", "completeness"],
            validation_results={"accuracy": True, "completeness": True},
            output_quality_score=0.9,
            issues_found=[],
            recommendations=[],
            confidence=0.9
        )
        
        result_state = await interaction_answer_langgraph._deliver_response_node(state_with_validation)
        
        # Verify delivery response results
        assert hasattr(result_state, 'delivery_response')
        delivery = result_state.delivery_response
        
        assert delivery.delivery_status in ["success", "partial", "failed"]
        assert delivery.response_time_ms > 0
        assert delivery.final_answer_length > 0
        assert 0.0 <= delivery.user_satisfaction_prediction <= 1.0
        assert 0.0 <= delivery.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_no_answer_handling(self):
        """Test handling when no final answer is available."""
        empty_state = ReactorState(original_query=self.user_query)
        # No final_answer set
        
        result_state = await interaction_answer_langgraph.execute(empty_state)
        
        # Should handle gracefully
        assert result_state is not None
        assert not hasattr(result_state, 'final_answer') or result_state.final_answer is None
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when LLM calls fail."""
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            # Mock LLM to raise an exception
            mock_llm.side_effect = Exception("LLM call failed")
            
            result_state = await interaction_answer_langgraph.execute(self.initial_state)
            
            # Should still complete with fallback delivery
            assert result_state is not None
            assert result_state.final_answer is not None
            # May have fallback delivery metrics
            if hasattr(result_state, 'delivery_response'):
                assert result_state.delivery_response.delivery_status in ["success", "partial", "failed"]
    
    def test_answer_formatting_pydantic_model(self):
        """Test AnswerFormatting Pydantic model validation."""
        # Valid data
        valid_data = {
            "format_type": "structured_narrative",
            "formatting_applied": ["paragraph_breaks", "citation_integration"],
            "readability_score": 0.85,
            "presentation_quality": "high",
            "user_experience_score": 0.88,
            "confidence": 0.85
        }
        formatting = AnswerFormatting(**valid_data)
        assert formatting.format_type == "structured_narrative"
        assert "paragraph_breaks" in formatting.formatting_applied
        assert formatting.readability_score == 0.85
        assert formatting.presentation_quality == "high"
        
        # Invalid data (score too high)
        with pytest.raises(Exception):  # Pydantic validation error
            AnswerFormatting(
                format_type="test",
                formatting_applied=[],
                readability_score=1.5,  # Invalid: > 1.0
                presentation_quality="test",
                user_experience_score=0.8,
                confidence=0.8
            )
    
    def test_metadata_enrichment_pydantic_model(self):
        """Test MetadataEnrichment Pydantic model validation."""
        # Valid data
        valid_data = {
            "confidence_indicators": {"accuracy": 0.9, "completeness": 0.8},
            "source_summary": {"knowledge_base": 2, "web_search": 1},
            "processing_metadata": {"modules": 12, "time_ms": 2500},
            "quality_metrics": {"overall": 0.85, "citation": 0.9},
            "timestamp_info": {"start": "10:00:00", "end": "10:00:02"},
            "confidence": 0.88
        }
        metadata = MetadataEnrichment(**valid_data)
        assert metadata.confidence_indicators["accuracy"] == 0.9
        assert metadata.source_summary["knowledge_base"] == 2
        assert metadata.processing_metadata["modules"] == 12
        assert metadata.quality_metrics["overall"] == 0.85
        
        # Test with empty dictionaries
        empty_data = {
            "confidence_indicators": {},
            "source_summary": {},
            "processing_metadata": {},
            "quality_metrics": {},
            "timestamp_info": {},
            "confidence": 0.5
        }
        empty_metadata = MetadataEnrichment(**empty_data)
        assert len(empty_metadata.confidence_indicators) == 0
        assert empty_metadata.confidence == 0.5
    
    def test_output_validation_pydantic_model(self):
        """Test OutputValidation Pydantic model validation."""
        # Valid data
        valid_data = {
            "validation_checks": ["accuracy", "completeness", "format"],
            "validation_results": {"accuracy": True, "completeness": True, "format": False},
            "output_quality_score": 0.85,
            "issues_found": ["Minor formatting issue"],
            "recommendations": ["Improve formatting", "Add more examples"],
            "confidence": 0.8
        }
        validation = OutputValidation(**valid_data)
        assert "accuracy" in validation.validation_checks
        assert validation.validation_results["accuracy"] == True
        assert validation.validation_results["format"] == False
        assert validation.output_quality_score == 0.85
        assert "Minor formatting issue" in validation.issues_found
        
        # Invalid data (quality score too low)
        with pytest.raises(Exception):  # Pydantic validation error
            OutputValidation(
                validation_checks=[],
                validation_results={},
                output_quality_score=-0.1,  # Invalid: < 0.0
                issues_found=[],
                recommendations=[],
                confidence=0.8
            )
    
    def test_delivery_response_pydantic_model(self):
        """Test DeliveryResponse Pydantic model validation."""
        # Valid data
        valid_data = {
            "delivery_status": "success",
            "response_time_ms": 2500.5,
            "processing_stages": {"formatting": 200, "validation": 150, "delivery": 50},
            "final_answer_length": 650,
            "user_satisfaction_prediction": 0.85,
            "delivery_metrics": {"format_quality": 0.9, "response_speed": 0.8},
            "confidence": 0.9
        }
        delivery = DeliveryResponse(**valid_data)
        assert delivery.delivery_status == "success"
        assert delivery.response_time_ms == 2500.5
        assert delivery.processing_stages["formatting"] == 200
        assert delivery.final_answer_length == 650
        assert delivery.user_satisfaction_prediction == 0.85
        
        # Test with different status
        failed_data = {
            "delivery_status": "failed",
            "response_time_ms": 5000,
            "processing_stages": {"error_handling": 1000},
            "final_answer_length": 0,
            "user_satisfaction_prediction": 0.1,
            "delivery_metrics": {"error_rate": 1.0},
            "confidence": 0.3
        }
        failed_delivery = DeliveryResponse(**failed_data)
        assert failed_delivery.delivery_status == "failed"
        assert failed_delivery.user_satisfaction_prediction == 0.1
    
    def test_calculate_response_time(self):
        """Test response time calculation utility."""
        start_time = time.time() * 1000
        time.sleep(0.1)  # Sleep for 100ms
        end_time = time.time() * 1000
        
        response_time = interaction_answer_langgraph._calculate_response_time(start_time, end_time)
        
        assert response_time > 90  # Should be around 100ms, allowing for some variance
        assert response_time < 200  # Should not be too much higher
    
    def test_predict_user_satisfaction(self):
        """Test user satisfaction prediction utility."""
        # High quality metrics should predict high satisfaction
        high_quality_metrics = {
            "answer_quality_score": 0.9,
            "output_quality_score": 0.9,
            "readability_score": 0.85,
            "completeness": 0.9
        }
        
        high_satisfaction = interaction_answer_langgraph._predict_user_satisfaction(high_quality_metrics)
        assert 0.8 <= high_satisfaction <= 1.0
        
        # Low quality metrics should predict low satisfaction
        low_quality_metrics = {
            "answer_quality_score": 0.3,
            "output_quality_score": 0.4,
            "readability_score": 0.5,
            "completeness": 0.3
        }
        
        low_satisfaction = interaction_answer_langgraph._predict_user_satisfaction(low_quality_metrics)
        assert 0.0 <= low_satisfaction <= 0.5
    
    def test_format_citations_for_display(self):
        """Test citation formatting for user display."""
        citations = [self.citation1, self.citation2]
        
        formatted_citations = interaction_answer_langgraph._format_citations_for_display(citations)
        
        assert isinstance(formatted_citations, str)
        assert len(formatted_citations) > 0
        # Should contain source information
        assert "ev_emissions_study" in formatted_citations or "transportation_research" in formatted_citations
    
    @pytest.mark.asyncio
    async def test_different_format_types(self):
        """Test different answer formatting types."""
        format_types = ["structured_narrative", "bullet_points", "numbered_list", "conversational"]
        
        for format_type in format_types:
            state = ReactorState(original_query=self.user_query)
            state.final_answer = self.test_answer
            
            with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
                mock_llm.return_value = f'{{\n                    "format_type": "{format_type}",\n                    "formatting_applied": ["format_specific_enhancement"],\n                    "readability_score": 0.8,\n                    "presentation_quality": "good",\n                    "user_experience_score": 0.8,\n                    "confidence": 0.8\n                }}'
                
                result_state = await interaction_answer_langgraph._format_answer_node(state)
                
                # Should handle different format types
                assert hasattr(result_state, 'answer_formatting')
                formatting = result_state.answer_formatting
                assert formatting.format_type == format_type
                assert formatting.readability_score == 0.8
    
    @pytest.mark.asyncio
    async def test_validation_with_issues(self):
        """Test output validation when issues are found."""
        state_with_issues = ReactorState(original_query=self.user_query)
        # Create answer with potential issues
        problematic_answer = Answer(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            query_id=self.query_id,
            text="Electric cars are good for environment.",  # Very brief, lacks detail
            citations=[],  # No citations
            limitations=[],
            confidence=0.4
        )
        state_with_issues.final_answer = problematic_answer
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_llm.return_value = '{\n                "validation_checks": ["content_accuracy", "citation_validity", "completeness", "detail_level"],\n                "validation_results": {"content_accuracy": true, "citation_validity": false, "completeness": false, "detail_level": false},\n                "output_quality_score": 0.4,\n                "issues_found": ["No citations provided", "Insufficient detail", "Too brief for complex topic"],\n                "recommendations": ["Add supporting citations", "Provide more detailed explanation", "Include specific examples"],\n                "confidence": 0.8\n            }'
            
            result_state = await interaction_answer_langgraph._validate_output_node(state_with_issues)
            
            # Should identify issues
            assert hasattr(result_state, 'output_validation')
            validation = result_state.output_validation
            
            assert validation.output_quality_score == 0.4
            assert len(validation.issues_found) > 0
            assert "No citations provided" in validation.issues_found
            assert len(validation.recommendations) > 0
            assert "Add supporting citations" in validation.recommendations


class TestM12Integration:
    """Integration tests for M12 with other components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="What are the key advantages of quantum computing over classical computing?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
    
    @pytest.mark.asyncio
    async def test_integration_with_high_quality_answer(self):
        """Test M12 integration with high-quality comprehensive answer."""
        # Create high-quality answer with multiple citations and good structure
        high_quality_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Quantum computing offers several key advantages over classical computing. First, quantum computers can solve certain problems exponentially faster than classical computers through quantum parallelism, where qubits can exist in superposition states. Second, quantum algorithms like Shor's algorithm can factor large numbers efficiently, which has significant implications for cryptography. Third, quantum computers excel at optimization problems and can simulate quantum systems naturally, making them valuable for drug discovery and materials science. However, current quantum computers are limited by quantum decoherence and error rates, requiring error correction techniques.",
            citations=[
                Citation(source="quantum_research_db", text="exponential speedup for certain problems", url="https://example.com/quantum-speedup"),
                Citation(source="cryptography_study", text="Shor's algorithm factoring capability", url="https://example.com/shors-algorithm"),
                Citation(source="quantum_applications", text="optimization and simulation advantages", url="https://example.com/quantum-apps")
            ],
            limitations=["Current quantum computers have high error rates", "Limited to specific problem types"],
            confidence=0.9
        )
        
        # Create supporting evidence
        evidence_items = [
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                content="Quantum computers leverage quantum parallelism to achieve exponential speedup for specific computational problems.",
                title="Quantum Parallelism Advantages",
                score_raw=0.95,
                provenance=Provenance(
                    source_type=SourceType.knowledge_base,
                    source_id="quantum_research_db",
                    doc_id="parallelism_study"
                )
            )
        ]
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = high_quality_answer
        for evidence in evidence_items:
            state.add_evidence(evidence)
        
        # Add quality metrics from previous modules
        state.answer_quality_score = 0.92
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            # Mock responses for high-quality answer
            mock_responses = [
                '{"format_type": "structured_narrative", "formatting_applied": ["paragraph_structure", "technical_clarity", "citation_integration"], "readability_score": 0.9, "presentation_quality": "excellent", "user_experience_score": 0.92, "confidence": 0.9}',
                '{"confidence_indicators": {"content_accuracy": 0.9, "citation_quality": 0.95, "technical_depth": 0.9, "completeness": 0.88}, "source_summary": {"knowledge_base": 1, "research_studies": 3, "total_sources": 3}, "processing_metadata": {"evidence_items": 1, "citations": 3, "processing_time_ms": 2200}, "quality_metrics": {"overall_quality": 0.92, "technical_accuracy": 0.9}, "timestamp_info": {"processing_completed": "2024-01-15T10:00:02Z"}, "confidence": 0.9}',
                '{"validation_checks": ["technical_accuracy", "citation_validity", "completeness", "clarity"], "validation_results": {"technical_accuracy": true, "citation_validity": true, "completeness": true, "clarity": true}, "output_quality_score": 0.93, "issues_found": [], "recommendations": ["Consider adding practical examples"], "confidence": 0.92}',
                '{"delivery_status": "success", "response_time_ms": 2200, "processing_stages": {"formatting": 180, "metadata": 120, "validation": 80, "delivery": 40}, "final_answer_length": 720, "user_satisfaction_prediction": 0.9, "delivery_metrics": {"technical_quality": 0.9, "presentation": 0.92}, "confidence": 0.92}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await interaction_answer_langgraph.execute(state)
            
            # Should deliver high-quality formatted answer
            assert result_state is not None
            assert result_state.delivery_response.delivery_status == "success"
            assert result_state.delivery_response.user_satisfaction_prediction >= 0.85
            
            # Check quality metrics
            assert result_state.answer_formatting.presentation_quality == "excellent"
            assert result_state.output_validation.output_quality_score >= 0.9
            assert len(result_state.output_validation.issues_found) == 0
    
    @pytest.mark.asyncio
    async def test_integration_with_poor_quality_answer(self):
        """Test M12 behavior with poor quality answer."""
        # Create poor quality answer
        poor_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Quantum computers are faster than regular computers.",
            citations=[],
            limitations=[],
            confidence=0.3
        )
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = poor_answer
        state.answer_quality_score = 0.25  # Low quality from previous modules
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"format_type": "basic_text", "formatting_applied": ["minimal_structure"], "readability_score": 0.4, "presentation_quality": "poor", "user_experience_score": 0.3, "confidence": 0.6}',
                '{"confidence_indicators": {"content_accuracy": 0.3, "citation_quality": 0.0, "completeness": 0.2}, "source_summary": {"total_sources": 0}, "processing_metadata": {"evidence_items": 0, "citations": 0}, "quality_metrics": {"overall_quality": 0.25}, "timestamp_info": {}, "confidence": 0.5}',
                '{"validation_checks": ["content_accuracy", "citation_validity", "completeness"], "validation_results": {"content_accuracy": false, "citation_validity": false, "completeness": false}, "output_quality_score": 0.2, "issues_found": ["No citations", "Insufficient detail", "Vague claims"], "recommendations": ["Add detailed explanation", "Include citations", "Provide specific examples"], "confidence": 0.8}',
                '{"delivery_status": "partial", "response_time_ms": 1500, "processing_stages": {"formatting": 100, "metadata": 80, "validation": 60, "delivery": 30}, "final_answer_length": 50, "user_satisfaction_prediction": 0.2, "delivery_metrics": {"quality_warning": true}, "confidence": 0.7}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await interaction_answer_langgraph.execute(state)
            
            # Should identify quality issues
            assert result_state is not None
            assert result_state.delivery_response.delivery_status == "partial"
            assert result_state.delivery_response.user_satisfaction_prediction <= 0.3
            
            # Check that issues were identified
            assert result_state.output_validation.output_quality_score <= 0.3
            assert len(result_state.output_validation.issues_found) > 0
            assert "No citations" in result_state.output_validation.issues_found
    
    @pytest.mark.asyncio
    async def test_integration_with_processing_metadata(self):
        """Test M12 integration with comprehensive processing metadata."""
        # Create answer with rich processing history
        answer_with_history = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Quantum computing provides computational advantages through quantum superposition and entanglement, enabling exponential speedup for specific algorithms.",
            citations=[Citation(source="quantum_theory", text="superposition and entanglement", url="")],
            limitations=[],
            confidence=0.8
        )
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = answer_with_history
        state.answer_quality_score = 0.8
        
        # Add processing metadata from previous modules
        state.processing_history = {
            "m1_preprocessing": {"time_ms": 150, "confidence": 0.85},
            "m2_routing": {"time_ms": 100, "paths_selected": 2},
            "m3_retrieval": {"time_ms": 800, "evidence_found": 5},
            "m10_answer_creation": {"time_ms": 600, "synthesis_quality": 0.8}
        }
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"format_type": "technical_explanation", "formatting_applied": ["technical_terms", "structured_flow"], "readability_score": 0.8, "presentation_quality": "good", "user_experience_score": 0.8, "confidence": 0.8}',
                f'{{"confidence_indicators": {{"content": 0.8, "citations": 0.8}}, "source_summary": {{"total": 1}}, "processing_metadata": {{"total_processing_time": 1650, "modules_executed": 4, "evidence_processed": 5}}, "quality_metrics": {{"synthesis_quality": 0.8}}, "timestamp_info": {{"total_time": "1.65s"}}, "confidence": 0.8}}',
                '{"validation_checks": ["accuracy", "completeness"], "validation_results": {"accuracy": true, "completeness": true}, "output_quality_score": 0.8, "issues_found": [], "recommendations": [], "confidence": 0.8}',
                '{"delivery_status": "success", "response_time_ms": 1650, "processing_stages": {"total_pipeline": 1650}, "final_answer_length": 150, "user_satisfaction_prediction": 0.8, "delivery_metrics": {"pipeline_efficiency": 0.85}, "confidence": 0.8}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await interaction_answer_langgraph.execute(state)
            
            # Should incorporate processing metadata
            assert result_state is not None
            assert result_state.metadata_enrichment.processing_metadata["modules_executed"] == 4
            assert result_state.metadata_enrichment.processing_metadata["evidence_processed"] == 5
            assert result_state.delivery_response.response_time_ms > 1000
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are recorded accurately."""
        # Create standard answer for performance testing
        test_answer = Answer(
            user_id=self.user_query.user_id,
            conversation_id=self.user_query.conversation_id,
            query_id=self.user_query.id,
            text="Quantum computing offers advantages in specific computational domains through quantum mechanical properties.",
            citations=[Citation(source="test_source", text="quantum properties", url="")],
            limitations=[],
            confidence=0.75
        )
        
        state = ReactorState(original_query=self.user_query)
        state.final_answer = test_answer
        state.answer_quality_score = 0.75
        
        # Record start time
        start_time = time.time() * 1000
        
        with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
            mock_responses = [
                '{"format_type": "standard", "formatting_applied": ["basic"], "readability_score": 0.75, "presentation_quality": "adequate", "user_experience_score": 0.75, "confidence": 0.75}',
                '{"confidence_indicators": {"content": 0.75}, "source_summary": {"total": 1}, "processing_metadata": {"time_ms": 1000}, "quality_metrics": {"overall": 0.75}, "timestamp_info": {}, "confidence": 0.75}',
                '{"validation_checks": ["basic"], "validation_results": {"basic": true}, "output_quality_score": 0.75, "issues_found": [], "recommendations": [], "confidence": 0.75}',
                '{"delivery_status": "success", "response_time_ms": 1000, "processing_stages": {"total": 1000}, "final_answer_length": 100, "user_satisfaction_prediction": 0.75, "delivery_metrics": {}, "confidence": 0.75}'
            ]
            mock_llm.side_effect = mock_responses
            
            result_state = await interaction_answer_langgraph.execute(state)
            
            # Check performance metrics
            assert result_state is not None
            assert result_state.delivery_response.response_time_ms > 0
            assert result_state.delivery_response.final_answer_length > 0
            assert 0.0 <= result_state.delivery_response.user_satisfaction_prediction <= 1.0
    
    @pytest.mark.asyncio
    async def test_delivery_consistency(self):
        """Test delivery consistency for similar answers."""
        # Create similar answers
        similar_answers = [
            Answer(
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                query_id=self.user_query.id,
                text="Quantum computing leverages quantum mechanics for computational advantages in specific problem domains.",
                citations=[Citation(source="quantum_source", text="quantum mechanics", url="")],
                limitations=[],
                confidence=0.8
            ),
            Answer(
                user_id=self.user_query.user_id,
                conversation_id=self.user_query.conversation_id,
                query_id=self.user_query.id,
                text="Computational advantages in quantum computing arise from quantum mechanical properties for certain problem types.",
                citations=[Citation(source="computing_source", text="quantum properties", url="")],
                limitations=[],
                confidence=0.8
            )
        ]
        
        delivery_results = []
        
        for answer in similar_answers:
            state = ReactorState(original_query=self.user_query)
            state.final_answer = answer
            state.answer_quality_score = 0.8
            
            with patch.object(interaction_answer_langgraph, '_call_llm') as mock_llm:
                # Consistent mock responses for similar content
                mock_responses = [
                    '{"format_type": "technical", "formatting_applied": ["structure"], "readability_score": 0.8, "presentation_quality": "good", "user_experience_score": 0.8, "confidence": 0.8}',
                    '{"confidence_indicators": {"content": 0.8}, "source_summary": {"total": 1}, "processing_metadata": {}, "quality_metrics": {"overall": 0.8}, "timestamp_info": {}, "confidence": 0.8}',
                    '{"validation_checks": ["accuracy"], "validation_results": {"accuracy": true}, "output_quality_score": 0.8, "issues_found": [], "recommendations": [], "confidence": 0.8}',
                    '{"delivery_status": "success", "response_time_ms": 1200, "processing_stages": {}, "final_answer_length": 120, "user_satisfaction_prediction": 0.8, "delivery_metrics": {}, "confidence": 0.8}'
                ]
                mock_llm.side_effect = mock_responses
                
                result_state = await interaction_answer_langgraph.execute(state)
                delivery_results.append(result_state.delivery_response)
        
        # Similar answers should get consistent delivery results
        assert len(delivery_results) == 2
        assert delivery_results[0].delivery_status == delivery_results[1].delivery_status
        
        # User satisfaction predictions should be similar
        satisfaction_diff = abs(delivery_results[0].user_satisfaction_prediction - delivery_results[1].user_satisfaction_prediction)
        assert satisfaction_diff < 0.1  # Should be very similar