"""M12 - Interaction Answer (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, EvidenceItem
from .base import LLMModule
import time


class AnswerFormatting(BaseModel):
    """Pydantic model for answer formatting and presentation."""
    format_type: str = Field(description="Format type: structured, narrative, bullet_points, etc.")
    formatting_applied: List[str] = Field(description="Formatting enhancements applied")
    readability_score: float = Field(ge=0.0, le=1.0, description="Readability improvement score")
    presentation_quality: str = Field(description="Overall presentation quality assessment")
    user_experience_score: float = Field(ge=0.0, le=1.0, description="User experience quality")
    confidence: float = Field(ge=0.0, le=1.0, description="Formatting confidence")


class MetadataEnrichment(BaseModel):
    """Pydantic model for additional metadata and context."""
    confidence_indicators: Dict[str, float] = Field(description="Confidence levels for different aspects")
    source_summary: Dict[str, int] = Field(description="Summary of sources used")
    processing_metadata: Dict[str, Any] = Field(description="Processing pipeline metadata")
    quality_metrics: Dict[str, float] = Field(description="Various quality metrics")
    timestamp_info: Dict[str, str] = Field(description="Timing information")
    confidence: float = Field(ge=0.0, le=1.0, description="Metadata confidence")


class OutputValidation(BaseModel):
    """Pydantic model for final output validation."""
    validation_checks: List[str] = Field(description="Validation checks performed")
    validation_results: Dict[str, bool] = Field(description="Results of validation checks")
    output_quality_score: float = Field(ge=0.0, le=1.0, description="Overall output quality")
    issues_found: List[str] = Field(description="Issues identified in output")
    recommendations: List[str] = Field(description="Recommendations for improvement")
    confidence: float = Field(ge=0.0, le=1.0, description="Validation confidence")


class DeliveryResponse(BaseModel):
    """Pydantic model for delivery confirmation and metrics."""
    delivery_status: str = Field(description="Delivery status: success, partial, failed")
    response_time_ms: float = Field(description="Total response time in milliseconds")
    processing_stages: Dict[str, float] = Field(description="Time spent in each processing stage")
    final_answer_length: int = Field(description="Length of final answer")
    user_satisfaction_prediction: float = Field(ge=0.0, le=1.0, description="Predicted user satisfaction")
    delivery_metrics: Dict[str, Any] = Field(description="Additional delivery metrics")
    confidence: float = Field(ge=0.0, le=1.0, description="Delivery confidence")


class InteractionAnswerLangGraph(LLMModule):
    """M12 - Interaction answer with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M12_LG", "ia.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for interaction answer delivery."""
        workflow = StateGraph(ReactorState)
        
        workflow.add_node("format_answer", self._format_answer_node)
        workflow.add_node("add_metadata", self._add_metadata_node)
        workflow.add_node("validate_output", self._validate_output_node)
        workflow.add_node("deliver_response", self._deliver_response_node)
        
        workflow.add_edge("format_answer", "add_metadata")
        workflow.add_edge("add_metadata", "validate_output")
        workflow.add_edge("validate_output", "deliver_response")
        workflow.add_edge("deliver_response", END)
        
        workflow.set_entry_point("format_answer")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute interaction answer delivery using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Preparing final answer delivery")
        
        # Check for different routing scenarios from previous modules
        routing_context = self._analyze_routing_context(state)
        self.logger.info(f"[{self.module_code}] Routing context: {routing_context['source']} - {routing_context['scenario']}")
        
        if not hasattr(state, 'final_answer') or not state.final_answer:
            # Handle no answer scenario
            if routing_context['scenario'] == 'no_retrieval_data':
                state.final_answer = self._create_no_data_response(routing_context)
            else:
                self._log_execution_end(state, "No final answer to deliver")
                return state
        
        try:
            # Record start time for delivery metrics
            state.delivery_start_time = time.time() * 1000
            
            # Add routing context to state for processing
            state.routing_context = routing_context
            
            thread_config = {"configurable": {"thread_id": str(uuid4())}}
            result_state = await self.graph.ainvoke(state, config=thread_config)
            
            if not isinstance(result_state, ReactorState):
                result_state = state
            
            delivery_status = getattr(result_state, 'delivery_response', {}).get('delivery_status', 'unknown')
            answer_length = len(result_state.final_answer) if result_state.final_answer else 0
            
            self._log_execution_end(result_state, f"Answer delivered: {delivery_status}, length: {answer_length}, context: {routing_context['scenario']}")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M12 Execute - {e}")
            print(f"   → Creating fallback delivery response")
            return state
    
    async def _format_answer_node(self, state: ReactorState) -> ReactorState:
        """Format the answer for optimal presentation."""
        formatting = await self._format_final_answer(state.final_answer, state)
        
        # Apply formatting to the answer
        if formatting.format_type != "no_change":
            state.final_answer = await self._apply_formatting(state.final_answer, formatting)
        
        state.answer_formatting = formatting
        return state
    
    async def _add_metadata_node(self, state: ReactorState) -> ReactorState:
        """Add rich metadata and context to the response."""
        metadata = await self._enrich_with_metadata(state)
        state.metadata_enrichment = metadata
        return state
    
    async def _validate_output_node(self, state: ReactorState) -> ReactorState:
        """Validate the final output before delivery."""
        validation = await self._validate_final_output(state)
        state.output_validation = validation
        
        # Apply any critical fixes if validation fails
        if validation.output_quality_score < 0.5:
            state.final_answer = await self._apply_emergency_fixes(state.final_answer, validation)
        
        return state
    
    async def _deliver_response_node(self, state: ReactorState) -> ReactorState:
        """Finalize delivery and record metrics."""
        delivery_response = await self._finalize_delivery(state)
        state.delivery_response = delivery_response
        return state
    
    def _analyze_routing_context(self, state: ReactorState) -> Dict[str, Any]:
        """Analyze the routing context from previous modules to understand delivery scenario."""
        
        # Check M11 gatekeeper decision
        if hasattr(state, 'gatekeeper_decision'):
            gatekeeper = state.gatekeeper_decision
            if gatekeeper.retrieval_compliance:
                return {
                    'source': 'M11_Gatekeeper',
                    'scenario': 'retrieval_compliant',
                    'message': 'Answer meets all retrieval requirements',
                    'quality_confirmed': True,
                    'limitations': []
                }
            else:
                return {
                    'source': 'M11_Gatekeeper', 
                    'scenario': 'max_attempts_reached',
                    'message': gatekeeper.message_for_target,
                    'quality_confirmed': False,
                    'limitations': gatekeeper.issues_found
                }
        
        # Check M9 routing decision
        if hasattr(state, 'routing_decision'):
            routing = state.routing_decision
            if routing.get('next_module') == 'M12':
                if routing.get('retrieval_limitations'):
                    return {
                        'source': 'M9_Controller',
                        'scenario': 'no_retrieval_data',
                        'message': routing.get('message_for_m12', 'No relevant data found'),
                        'quality_confirmed': False,
                        'limitations': routing.get('retrieval_limitations', {}).get('evidence_gaps', [])
                    }
        
        # Default scenario - normal processing
        return {
            'source': 'Normal_Flow',
            'scenario': 'standard_delivery',
            'message': 'Answer ready for delivery',
            'quality_confirmed': True,
            'limitations': []
        }
    
    def _create_no_data_response(self, routing_context: Dict[str, Any]) -> str:
        """Create appropriate response when no retrieval data is available."""
        base_message = routing_context.get('message', 'Unable to find relevant information')
        limitations = routing_context.get('limitations', [])
        
        response = f"I apologize, but {base_message.lower()}."
        
        if limitations:
            response += f" Specifically, I was unable to find information about: {', '.join(limitations[:3])}."
        
        response += " You might want to try rephrasing your question or asking about a different aspect of the topic."
        
        return response

    async def _format_final_answer(self, answer: str, state: ReactorState) -> AnswerFormatting:
        """Determine and apply optimal formatting for the answer."""
        prompt = self._get_prompt("m12_answer_formatting",
            "Analyze this answer and determine the best formatting approach."
        )
        
        query_text = state.original_query.text if state.original_query else "Unknown query"
        
        full_prompt = f"""{prompt}

<query>{query_text}</query>
<answer>
{answer}
</answer>

Return JSON with:
- format_type: "structured" | "narrative" | "bullet_points" | "numbered_list" | "no_change"
- formatting_applied: ["enhancement1", "enhancement2"]
- readability_score: 0.0-1.0
- presentation_quality: "excellent" | "good" | "fair" | "poor"
- user_experience_score: 0.0-1.0
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return AnswerFormatting(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Answer formatting failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M12 Answer Formatting - {e}")
            print(f"   → Using heuristic formatting")
            return self._fallback_answer_formatting(answer)
    
    async def _enrich_with_metadata(self, state: ReactorState) -> MetadataEnrichment:
        """Enrich the response with comprehensive metadata."""
        # Collect confidence indicators
        confidence_indicators = {}
        if hasattr(state, 'answer_quality_score'):
            confidence_indicators['answer_quality'] = state.answer_quality_score
        if hasattr(state, 'evidence_assessment'):
            confidence_indicators['evidence_quality'] = state.evidence_assessment.confidence_score
        
        # Add routing context confidence
        routing_context = getattr(state, 'routing_context', {})
        if routing_context.get('quality_confirmed'):
            confidence_indicators['routing_quality'] = 1.0
        else:
            confidence_indicators['routing_quality'] = 0.5
        
        # Summarize sources
        source_summary = {}
        for evidence in (state.evidences or []):
            if evidence.provenance:
                source_id = evidence.provenance.source_id
                source_summary[source_id] = source_summary.get(source_id, 0) + 1
        
        # Collect processing metadata including routing context
        processing_metadata = {
            'total_evidence': len(state.evidences) if state.evidences else 0,
            'processing_modules': self._get_processing_modules(state),
            'query_complexity': getattr(state, 'query_complexity', 'unknown'),
            'routing_source': routing_context.get('source', 'unknown'),
            'delivery_scenario': routing_context.get('scenario', 'unknown'),
            'quality_confirmed': routing_context.get('quality_confirmed', False)
        }
        
        # Add limitations if present
        limitations = routing_context.get('limitations', [])
        if limitations:
            processing_metadata['limitations'] = limitations[:5]  # Limit to 5 items
        
        # Calculate quality metrics
        quality_metrics = {
            'evidence_count': len(state.evidences) if state.evidences else 0,
            'source_diversity': len(source_summary),
            'processing_completeness': 1.0 if routing_context.get('quality_confirmed') else 0.7,
            'retrieval_compliance': 1.0 if routing_context.get('scenario') == 'retrieval_compliant' else 0.5
        }
        
        # Add timestamp information
        current_time = time.time() * 1000
        start_time = getattr(state, 'delivery_start_time', current_time)
        
        timestamp_info = {
            'processing_start': str(int(start_time)),
            'current_time': str(int(current_time)),
            'processing_duration_ms': str(int(current_time - start_time))
        }
        
        return MetadataEnrichment(
            confidence_indicators=confidence_indicators,
            source_summary=source_summary,
            processing_metadata=processing_metadata,
            quality_metrics=quality_metrics,
            timestamp_info=timestamp_info,
            confidence=0.9
        )
    
    async def _validate_final_output(self, state: ReactorState) -> OutputValidation:
        """Perform final validation of the output before delivery."""
        validation_checks = [
            "answer_length_check",
            "content_quality_check", 
            "formatting_check",
            "metadata_completeness_check"
        ]
        
        validation_results = {}
        issues_found = []
        recommendations = []
        
        # Answer length check
        answer_length = len(state.final_answer) if state.final_answer else 0
        validation_results["answer_length_check"] = answer_length >= 50
        if not validation_results["answer_length_check"]:
            issues_found.append("Answer too short")
            recommendations.append("Expand answer with more detail")
        
        # Content quality check
        quality_score = getattr(state, 'answer_quality_score', 0.5)
        validation_results["content_quality_check"] = quality_score >= 0.6
        if not validation_results["content_quality_check"]:
            issues_found.append("Low content quality score")
            recommendations.append("Review and improve answer quality")
        
        # Formatting check
        formatting = getattr(state, 'answer_formatting', None)
        validation_results["formatting_check"] = formatting is not None
        if not validation_results["formatting_check"]:
            issues_found.append("Formatting not applied")
            recommendations.append("Apply proper formatting")
        
        # Metadata completeness check
        metadata = getattr(state, 'metadata_enrichment', None)
        validation_results["metadata_completeness_check"] = metadata is not None
        if not validation_results["metadata_completeness_check"]:
            issues_found.append("Metadata incomplete")
            recommendations.append("Add comprehensive metadata")
        
        # Calculate overall quality score
        passed_checks = sum(1 for result in validation_results.values() if result)
        output_quality_score = passed_checks / len(validation_checks)
        
        return OutputValidation(
            validation_checks=validation_checks,
            validation_results=validation_results,
            output_quality_score=output_quality_score,
            issues_found=issues_found,
            recommendations=recommendations,
            confidence=0.9
        )
    
    async def _finalize_delivery(self, state: ReactorState) -> DeliveryResponse:
        """Finalize the delivery and record comprehensive metrics."""
        current_time = time.time() * 1000
        start_time = getattr(state, 'delivery_start_time', current_time)
        response_time = current_time - start_time
        
        # Determine delivery status
        validation = getattr(state, 'output_validation', None)
        if validation and validation.output_quality_score >= 0.8:
            delivery_status = "success"
        elif validation and validation.output_quality_score >= 0.5:
            delivery_status = "partial"
        else:
            delivery_status = "failed"
        
        # Estimate processing stages (simplified)
        processing_stages = {
            "formatting": response_time * 0.2,
            "metadata_enrichment": response_time * 0.3,
            "validation": response_time * 0.3,
            "finalization": response_time * 0.2
        }
        
        # Calculate user satisfaction prediction
        quality_score = validation.output_quality_score if validation else 0.5
        answer_length = len(state.final_answer) if state.final_answer else 0
        
        # Simple satisfaction model
        length_factor = min(1.0, answer_length / 200)  # Optimal around 200 chars
        satisfaction = (quality_score * 0.7) + (length_factor * 0.3)
        
        # Additional delivery metrics
        delivery_metrics = {
            "evidence_used": len(state.evidences) if state.evidences else 0,
            "modules_executed": len(self._get_processing_modules(state)),
            "quality_score": quality_score,
            "formatting_applied": bool(getattr(state, 'answer_formatting', None))
        }
        
        return DeliveryResponse(
            delivery_status=delivery_status,
            response_time_ms=response_time,
            processing_stages=processing_stages,
            final_answer_length=answer_length,
            user_satisfaction_prediction=satisfaction,
            delivery_metrics=delivery_metrics,
            confidence=0.9
        )
    
    async def _apply_formatting(self, answer: str, formatting: AnswerFormatting) -> str:
        """Apply the determined formatting to the answer."""
        if formatting.format_type == "structured":
            return await self._apply_structured_formatting(answer)
        elif formatting.format_type == "bullet_points":
            return await self._apply_bullet_formatting(answer)
        elif formatting.format_type == "numbered_list":
            return await self._apply_numbered_formatting(answer)
        else:
            return answer  # No change or narrative (already formatted)
    
    async def _apply_structured_formatting(self, answer: str) -> str:
        """Apply structured formatting to the answer."""
        # Simple structured formatting
        sections = answer.split('\n\n')
        if len(sections) > 1:
            formatted = "## Summary\n\n"
            formatted += sections[0] + "\n\n"
            
            if len(sections) > 1:
                formatted += "## Details\n\n"
                formatted += '\n\n'.join(sections[1:])
            
            return formatted
        return answer
    
    async def _apply_bullet_formatting(self, answer: str) -> str:
        """Apply bullet point formatting to the answer."""
        sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 10]
        if len(sentences) > 2:
            formatted = "Key Points:\n\n"
            for sentence in sentences[:5]:  # Limit to 5 key points
                formatted += f"• {sentence.strip()}\n"
            return formatted
        return answer
    
    async def _apply_numbered_formatting(self, answer: str) -> str:
        """Apply numbered list formatting to the answer."""
        sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 10]
        if len(sentences) > 2:
            formatted = "Answer:\n\n"
            for i, sentence in enumerate(sentences[:5], 1):
                formatted += f"{i}. {sentence.strip()}\n"
            return formatted
        return answer
    
    async def _apply_emergency_fixes(self, answer: str, validation: OutputValidation) -> str:
        """Apply emergency fixes for critical validation failures."""
        fixed_answer = answer
        
        # Fix length issues
        if "Answer too short" in validation.issues_found:
            fixed_answer += "\n\nNote: This answer provides the key information available. Additional details may require further research."
        
        # Add disclaimer for quality issues
        if "Low content quality score" in validation.issues_found:
            fixed_answer = "Please note: This answer is based on available information and may require verification.\n\n" + fixed_answer
        
        return fixed_answer
    
    def _get_processing_modules(self, state: ReactorState) -> List[str]:
        """Get list of modules that processed this request."""
        modules = []
        
        # Check for various processing artifacts to infer module usage
        if hasattr(state, 'preprocessed_query'):
            modules.append("M1_Preprocessor")
        if hasattr(state, 'route_plans'):
            modules.append("M2_Router")
        if hasattr(state, 'evidences') and state.evidences:
            modules.append("M3_Retrieval")
        if hasattr(state, 'quality_report'):
            modules.append("M4_QualityCheck")
        if hasattr(state, 'answer_analysis'):
            modules.append("M11_AnswerCheck")
        
        return modules
    
    def _fallback_answer_formatting(self, answer: str) -> AnswerFormatting:
        """Fallback answer formatting when LLM analysis fails."""
        print(f"🔄 EXECUTING FALLBACK: M12 Answer Formatting - Using heuristic formatting")
        length = len(answer)
        
        # Simple heuristic formatting decision
        if length > 300:
            format_type = "structured"
        elif '\n' in answer or '.' in answer:
            format_type = "narrative"
        else:
            format_type = "no_change"
        
        readability_score = 0.7 if length > 100 else 0.5
        presentation_quality = "good" if length > 150 else "fair"
        user_experience_score = min(1.0, length / 200)
        
        return AnswerFormatting(
            format_type=format_type,
            formatting_applied=["basic_formatting"],
            readability_score=readability_score,
            presentation_quality=presentation_quality,
            user_experience_score=user_experience_score,
            confidence=0.6
        )


# Module instance
interaction_answer_langgraph = InteractionAnswerLangGraph()


# LangGraph node function
async def interaction_answer_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M12 - Interaction Answer."""
    return await interaction_answer_langgraph.execute(state)