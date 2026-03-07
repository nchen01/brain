"""M4 - Retrieval Quality Check using LLM assessment."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field
import logging

from ..models import ReactorState, EvidenceItem
from .base import LLMModule
from ..config.loader import config_loader

logger = logging.getLogger(__name__)


class QualityAssessment(BaseModel):
    """Quality assessment result for an evidence item."""
    evidence_id: UUID
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to query")
    credibility_score: float = Field(ge=0.0, le=1.0, description="Source credibility")
    recency_score: float = Field(ge=0.0, le=1.0, description="Information recency")
    completeness_score: float = Field(ge=0.0, le=1.0, description="Information completeness")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    reasoning: str = Field(description="Assessment reasoning")
    should_keep: bool = Field(description="Whether to keep this evidence")


class M4QualityCheckLangGraph(LLMModule):
    """M4 - Quality check module for retrieved evidence."""
    
    def __init__(self):
        super().__init__("M4", "m4.model")
        
        # Load configuration
        self.quality_threshold = self._get_config("m4.quality_threshold", 0.6)
        self.batch_size = self._get_config("m4.batch_size", 5)
        self.timeout_seconds = self._get_config("m4.timeout_seconds", 10)
        
        # Load prompt template
        self.quality_prompt = self._get_prompt("m4_quality_assessment", 
            "Assess the quality and relevance of the provided evidence.")
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute quality check on all evidence in the state."""
        self._log_execution_start(state, f"Checking quality of {len(state.evidences)} evidence items")
        
        try:
            # Process evidence in batches
            filtered_evidences = []
            
            for i in range(0, len(state.evidences), self.batch_size):
                batch = state.evidences[i:i + self.batch_size]
                filtered_batch = await self._process_evidence_batch(batch, state.original_query.text)
                filtered_evidences.extend(filtered_batch)
            
            # Update state with filtered evidence
            state.evidences = filtered_evidences
            
            self._log_execution_end(state, f"Kept {len(filtered_evidences)} high-quality evidence items")
            return state
            
        except Exception as e:
            self._log_error(state, e)
            # Return original state if quality check fails
            return state
    
    async def check_path_evidence_quality(self, state: ReactorState, path_id: str) -> ReactorState:
        """Check quality of evidence from a specific retrieval path."""
        self._log_execution_start(state, f"Checking quality for path {path_id}")
        
        try:
            # Filter evidence from this path
            path_evidences = [
                evidence for evidence in state.evidences 
                if evidence.provenance.retrieval_path == path_id
            ]
            
            if not path_evidences:
                self.logger.info(f"[{self.module_code}] No evidence found for path {path_id}")
                return state
            
            # Process evidence in batches
            filtered_evidences = []
            other_evidences = [
                evidence for evidence in state.evidences 
                if evidence.provenance.retrieval_path != path_id
            ]
            
            for i in range(0, len(path_evidences), self.batch_size):
                batch = path_evidences[i:i + self.batch_size]
                filtered_batch = await self._process_evidence_batch(batch, state.original_query.text)
                filtered_evidences.extend(filtered_batch)
            
            # Update state with filtered evidence from this path plus other evidence
            state.evidences = other_evidences + filtered_evidences
            
            self._log_execution_end(state, f"Path {path_id}: kept {len(filtered_evidences)}/{len(path_evidences)} evidence items")
            return state
            
        except Exception as e:
            self._log_error(state, e)
            # Return original state if quality check fails
            return state
    
    async def _process_evidence_batch(self, evidences: List[EvidenceItem], 
                                    original_query: str) -> List[EvidenceItem]:
        """Process a batch of evidence items for quality assessment."""
        try:
            # Create assessment tasks
            assessment_tasks = [
                self._assess_evidence_quality(evidence, original_query)
                for evidence in evidences
            ]
            
            # Execute assessments in parallel
            assessments = await asyncio.gather(*assessment_tasks, return_exceptions=True)
            
            # Filter evidence based on assessments
            filtered_evidences = []
            
            for evidence, assessment in zip(evidences, assessments):
                if isinstance(assessment, Exception):
                    # Use fallback assessment if LLM assessment failed
                    self.logger.warning(f"[{self.module_code}] Assessment failed for evidence {evidence.id}: {assessment}")
                    print(f"🔄 FALLBACK TRIGGERED: M4 Evidence Assessment - {assessment}")
                    print(f"   → Using heuristic assessment for evidence {evidence.id}")
                    assessment = self._fallback_assessment(evidence, original_query)
                
                # Add quality metadata to evidence
                if hasattr(evidence.provenance, 'authority_score'):
                    evidence.provenance.authority_score = assessment.overall_score
                
                # Keep evidence if it meets quality threshold
                if assessment.should_keep and assessment.overall_score >= self.quality_threshold:
                    filtered_evidences.append(evidence)
                    self.logger.debug(f"[{self.module_code}] Kept evidence {evidence.id} (score: {assessment.overall_score:.2f})")
                else:
                    self.logger.debug(f"[{self.module_code}] Filtered out evidence {evidence.id} (score: {assessment.overall_score:.2f})")
            
            return filtered_evidences
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Batch processing failed: {e}")
            # Return original evidence if batch processing fails
            return evidences
    
    async def _assess_evidence_quality(self, evidence: EvidenceItem, original_query: str) -> QualityAssessment:
        """Use LLM to assess evidence quality and relevance."""
        try:
            # Prepare prompt with evidence details
            prompt = self.quality_prompt.format(
                original_query=original_query,
                evidence_source=evidence.provenance.url or evidence.provenance.source_id,
                evidence_title=evidence.title or "No title",
                evidence_content=evidence.content[:2000]  # Limit content length for prompt
            )
            
            # Check if we should use actual LLM or placeholder
            use_actual_llm = self._get_config("llm.use_actual_calls", False)
            
            if use_actual_llm:
                response = await self._call_llm(prompt)
                assessment_data = self._parse_llm_response(response)
            else:
                assessment_data = self._create_placeholder_assessment(evidence, original_query)
            
            # Create QualityAssessment object
            assessment = QualityAssessment(
                evidence_id=evidence.id,
                **assessment_data
            )
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] LLM assessment failed for evidence {evidence.id}: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M4 LLM Assessment - {e}")
            print(f"   → Using fallback assessment for evidence {evidence.id}")
            return self._fallback_assessment(evidence, original_query)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract quality assessment."""
        try:
            # Try to parse as JSON
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['relevance_score', 'credibility_score', 'recency_score', 
                                 'completeness_score', 'overall_score', 'reasoning', 'should_keep']
                
                if all(field in data for field in required_fields):
                    return data
            
            # If parsing fails, use fallback
            self.logger.warning(f"[{self.module_code}] Failed to parse LLM response: {response[:100]}...")
            print(f"🔄 FALLBACK TRIGGERED: M4 Response Parsing - Invalid JSON response")
            print(f"   → Using fallback assessment data")
            return self._create_fallback_assessment_data()
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Response parsing error: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M4 Response Parsing - {e}")
            print(f"   → Using fallback assessment data")
            return self._create_fallback_assessment_data()
    
    def _create_placeholder_assessment(self, evidence: EvidenceItem, original_query: str) -> Dict[str, Any]:
        """Create placeholder assessment for testing/development."""
        # Simple heuristic scoring
        content_length = len(evidence.content)
        has_title = bool(evidence.title)
        has_url = bool(evidence.provenance.url)
        
        # Basic scoring based on content characteristics
        relevance_score = 0.7 if content_length > 100 else 0.5
        credibility_score = 0.8 if has_url and not evidence.provenance.url.startswith('https://example.') else 0.6
        recency_score = 0.7  # Default recency
        completeness_score = 0.8 if content_length > 500 else 0.6
        
        overall_score = (relevance_score + credibility_score + recency_score + completeness_score) / 4
        should_keep = overall_score >= self.quality_threshold
        
        return {
            'relevance_score': relevance_score,
            'credibility_score': credibility_score,
            'recency_score': recency_score,
            'completeness_score': completeness_score,
            'overall_score': overall_score,
            'reasoning': f'Placeholder assessment based on content length ({content_length} chars) and source characteristics.',
            'should_keep': should_keep
        }
    
    def _fallback_assessment(self, evidence: EvidenceItem, original_query: str) -> QualityAssessment:
        """Create fallback assessment when LLM assessment fails."""
        print(f"🔄 EXECUTING FALLBACK: M4 Quality Assessment - Using heuristic assessment for {evidence.id}")
        assessment_data = self._create_fallback_assessment_data()
        return QualityAssessment(
            evidence_id=evidence.id,
            **assessment_data
        )
    
    def _create_fallback_assessment_data(self) -> Dict[str, Any]:
        """Create fallback assessment data with default values."""
        print(f"🔄 EXECUTING FALLBACK: M4 Assessment Data - Using default quality scores")
        return {
            'relevance_score': 0.7,
            'credibility_score': 0.7,
            'recency_score': 0.7,
            'completeness_score': 0.7,
            'overall_score': 0.7,
            'reasoning': 'Fallback assessment due to LLM failure - keeping evidence conservatively',
            'should_keep': True  # Conservative approach - keep evidence when unsure
        }


# Global instance
m4_quality_check = M4QualityCheckLangGraph()


# LangGraph node function for integration
async def retrieval_quality_check_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M4 - Retrieval Quality Check."""
    return await m4_quality_check.execute(state)