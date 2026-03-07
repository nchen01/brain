"""M11 - Answer Check (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, EvidenceItem
from .base import LLMModule


class AnswerAnalysis(BaseModel):
    """Pydantic model for answer structure and content analysis."""
    answer_length: int = Field(description="Length of the answer in characters")
    structure_score: float = Field(ge=0.0, le=1.0, description="Quality of answer structure")
    clarity_score: float = Field(ge=0.0, le=1.0, description="Clarity and readability score")
    coherence_score: float = Field(ge=0.0, le=1.0, description="Logical coherence score")
    key_points_covered: List[str] = Field(description="Key points addressed in answer")
    missing_elements: List[str] = Field(description="Missing important elements")
    confidence: float = Field(ge=0.0, le=1.0, description="Analysis confidence")


class AccuracyCheck(BaseModel):
    """Pydantic model for factual accuracy assessment."""
    accuracy_score: float = Field(ge=0.0, le=1.0, description="Overall accuracy score")
    verified_facts: List[str] = Field(description="Facts verified against evidence")
    questionable_claims: List[str] = Field(description="Claims that need verification")
    contradictions: List[str] = Field(description="Contradictions found")
    evidence_support_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of claims supported by evidence")
    confidence: float = Field(ge=0.0, le=1.0, description="Accuracy assessment confidence")


class CitationValidation(BaseModel):
    """Pydantic model for citation quality and accuracy."""
    total_citations: int = Field(description="Total number of citations")
    valid_citations: int = Field(description="Number of valid citations")
    citation_accuracy: float = Field(ge=0.0, le=1.0, description="Citation accuracy score")
    missing_citations: List[str] = Field(description="Claims that need citations")
    citation_quality: str = Field(description="Overall citation quality assessment")
    source_diversity: float = Field(ge=0.0, le=1.0, description="Diversity of cited sources")
    confidence: float = Field(ge=0.0, le=1.0, description="Citation validation confidence")


class CompletenessAssessment(BaseModel):
    """Pydantic model for answer completeness evaluation."""
    completeness_score: float = Field(ge=0.0, le=1.0, description="Overall completeness score")
    query_coverage: float = Field(ge=0.0, le=1.0, description="How well the query is addressed")
    depth_score: float = Field(ge=0.0, le=1.0, description="Depth of information provided")
    breadth_score: float = Field(ge=0.0, le=1.0, description="Breadth of coverage")
    unanswered_aspects: List[str] = Field(description="Aspects of query not addressed")
    additional_context_needed: List[str] = Field(description="Areas needing more context")
    confidence: float = Field(ge=0.0, le=1.0, description="Completeness assessment confidence")


class RetrievalValidation(BaseModel):
    """Pydantic model for retrieval-based answer validation."""
    is_retrieval_based: bool = Field(description="Whether answer is fully based on retrieval data")
    retrieval_coverage: float = Field(ge=0.0, le=1.0, description="Percentage of answer based on retrieval")
    non_retrieval_parts: List[str] = Field(description="Parts of answer not based on retrieval")
    missing_citations: List[str] = Field(description="Claims without proper citations")
    citation_accuracy: float = Field(ge=0.0, le=1.0, description="Accuracy of citations")
    evidence_support_score: float = Field(ge=0.0, le=1.0, description="How well evidence supports claims")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in validation")


class GatekeeperDecision(BaseModel):
    """Pydantic model for M11 gatekeeper routing decision."""
    decision: str = Field(description="Routing decision: pass_to_m12, return_to_m10, or error")
    reason: str = Field(description="Detailed reasoning for the decision")
    retrieval_compliance: bool = Field(description="Whether answer meets retrieval requirements")
    issues_found: List[str] = Field(description="Issues identified with the answer")
    message_for_target: str = Field(description="Message for the target module (M10 or M12)")
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence")


class AnswerCheckLangGraph(LLMModule):
    """M11 - Answer Check Gatekeeper with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M11_LG", "ac.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self.max_return_attempts = 2  # Maximum times to return to M10
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for answer gatekeeper checking."""
        workflow = StateGraph(ReactorState)
        
        # Simplified workflow for gatekeeper functionality
        workflow.add_node("validate_retrieval", self._validate_retrieval_node)
        workflow.add_node("make_gatekeeper_decision", self._make_gatekeeper_decision_node)
        
        workflow.add_edge("validate_retrieval", "make_gatekeeper_decision")
        workflow.add_edge("make_gatekeeper_decision", END)
        
        workflow.set_entry_point("validate_retrieval")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute answer gatekeeper checking using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Gatekeeper: Validating answer retrieval compliance")
        
        if not hasattr(state, 'final_answer') or not state.final_answer:
            self._log_execution_end(state, "No answer to validate")
            return state
        
        # Initialize return attempt counter
        if not hasattr(state, 'm11_return_attempts'):
            state.m11_return_attempts = 0
        
        try:
            # Call pipeline nodes directly (avoids LangGraph sub-graph dict serialization issues)
            result_state = await self._validate_retrieval_node(state)
            result_state = await self._make_gatekeeper_decision_node(result_state)

            # Get gatekeeper decision
            decision = getattr(result_state, 'gatekeeper_decision', None)
            if decision:
                decision_text = f"{decision.decision} - {decision.reason}"
                self._log_execution_end(result_state, f"Gatekeeper decision: {decision_text}")
            else:
                self._log_execution_end(result_state, "Gatekeeper validation completed")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M11 Execute - {e}")
            print(f"   → Creating fallback gatekeeper decision")
            
            # Fallback: pass to M12 with error message
            state.gatekeeper_decision = GatekeeperDecision(
                decision="pass_to_m12",
                reason="Gatekeeper validation failed due to system error",
                retrieval_compliance=False,
                issues_found=["System error during validation"],
                message_for_target="Answer validation failed due to technical issues",
                confidence=0.0
            )
            return state
    
    async def _validate_retrieval_node(self, state: ReactorState) -> ReactorState:
        """Validate that the answer is based on retrieval data."""
        try:
            # Extract text string from Answer object if needed
            answer_text = state.final_answer.text if hasattr(state.final_answer, 'text') else str(state.final_answer)
            validation = await self._validate_retrieval_compliance(answer_text, state)
            state.retrieval_validation = validation
            return state
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Retrieval validation failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Retrieval Validation - {e}")
            print(f"   → Using fallback validation")

            # Fallback validation
            answer_text = state.final_answer.text if hasattr(state.final_answer, 'text') else str(state.final_answer)
            state.retrieval_validation = self._fallback_retrieval_validation(answer_text, state)
            return state
    
    async def _make_gatekeeper_decision_node(self, state: ReactorState) -> ReactorState:
        """Make gatekeeper routing decision based on retrieval validation."""
        try:
            validation = getattr(state, 'retrieval_validation', None)
            decision = await self._make_gatekeeper_routing_decision(validation, state)
            state.gatekeeper_decision = decision
            return state
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Gatekeeper decision failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Gatekeeper Decision - {e}")
            print(f"   → Using fallback decision")
            
            # Fallback decision: pass to M12 with error
            state.gatekeeper_decision = GatekeeperDecision(
                decision="pass_to_m12",
                reason="Decision making failed, passing to M12 with error notice",
                retrieval_compliance=False,
                issues_found=["Gatekeeper decision system error"],
                message_for_target="Answer validation encountered technical issues",
                confidence=0.0
            )
            return state
    
    async def _validate_retrieval_compliance(self, answer: str, state: ReactorState) -> RetrievalValidation:
        """Validate that the answer is fully based on retrieval data with proper citations."""
        
        prompt = self._get_prompt("m11_retrieval_validation",
            "Validate that this answer is fully based on retrieval data with proper source citations."
        )
        
        # Prepare evidence context
        evidence_context = self._prepare_evidence_context(state.evidences)
        
        full_prompt = f"""{prompt}

<answer>
{answer}
</answer>

<available_evidence>
{evidence_context}
</available_evidence>

Return JSON with:
- is_retrieval_based: true/false (whether answer is fully based on retrieval)
- retrieval_coverage: 0.0-1.0 (percentage of answer based on retrieval)
- non_retrieval_parts: ["part1", "part2"] (parts not based on retrieval)
- missing_citations: ["claim1", "claim2"] (claims without citations)
- citation_accuracy: 0.0-1.0 (accuracy of citations)
- evidence_support_score: 0.0-1.0 (how well evidence supports claims)
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return RetrievalValidation(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Retrieval validation failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Retrieval Validation - {e}")
            print(f"   → Using heuristic validation")
            return self._fallback_retrieval_validation(answer, state)
    
    async def _make_gatekeeper_routing_decision(self, validation: RetrievalValidation, state: ReactorState) -> GatekeeperDecision:
        """Make routing decision based on retrieval validation and return attempt count."""
        
        if not validation:
            return GatekeeperDecision(
                decision="pass_to_m12",
                reason="No validation data available",
                retrieval_compliance=False,
                issues_found=["Validation failed"],
                message_for_target="Answer validation was unsuccessful",
                confidence=0.0
            )
        
        current_attempts = getattr(state, 'm11_return_attempts', 0)
        max_attempts_reached = current_attempts >= self.max_return_attempts
        
        # Decision logic based on your requirements
        if validation.is_retrieval_based and validation.retrieval_coverage >= 0.9:
            # Path 1: Answer is fully retrieval-based → Pass to M12
            print(f"🔄 M11 GATEKEEPER: Answer is retrieval-compliant ({validation.retrieval_coverage:.2f})")
            print(f"   → Passing to M12 with compliance confirmation")
            
            return GatekeeperDecision(
                decision="pass_to_m12",
                reason=f"Answer is fully based on retrieval data (coverage: {validation.retrieval_coverage:.2f})",
                retrieval_compliance=True,
                issues_found=[],
                message_for_target="Answer meets all retrieval requirements and is ready for user delivery",
                confidence=validation.confidence
            )
        
        elif not max_attempts_reached:
            # Path 2: Not retrieval-based but can return to M10
            print(f"🔄 M11 GATEKEEPER: Answer not retrieval-compliant ({validation.retrieval_coverage:.2f})")
            print(f"   → Returning to M10 (attempt {current_attempts + 1}/{self.max_return_attempts})")
            
            # Increment return attempts
            state.m11_return_attempts = current_attempts + 1
            
            return GatekeeperDecision(
                decision="return_to_m10",
                reason=f"Answer not fully retrieval-based (coverage: {validation.retrieval_coverage:.2f}), returning for improvement",
                retrieval_compliance=False,
                issues_found=validation.non_retrieval_parts + validation.missing_citations,
                message_for_target=f"Answer needs improvement: {', '.join(validation.non_retrieval_parts[:3])}",
                confidence=validation.confidence
            )
        
        else:
            # Path 3: Max attempts reached → Pass to M12 with issues noted
            print(f"🔄 M11 GATEKEEPER: Max attempts reached ({self.max_return_attempts})")
            print(f"   → Passing to M12 with non-retrieval parts noted")
            
            return GatekeeperDecision(
                decision="pass_to_m12",
                reason=f"Maximum return attempts reached ({self.max_return_attempts}), passing with limitations",
                retrieval_compliance=False,
                issues_found=validation.non_retrieval_parts + validation.missing_citations,
                message_for_target=f"Answer has limitations: {', '.join(validation.non_retrieval_parts[:3])}. Some information may not be from retrieval sources.",
                confidence=validation.confidence
            )
    
    def _prepare_evidence_context(self, evidences: List[EvidenceItem]) -> str:
        """Prepare evidence context for validation."""
        if not evidences:
            return "No evidence available"
        
        evidence_items = []
        for i, evidence in enumerate(evidences[:10]):  # Limit to top 10
            evidence_text = f"Evidence ID: {evidence.id}\n"
            evidence_text += f"Title: {getattr(evidence, 'title', 'No title')}\n"
            evidence_text += f"Content: {evidence.content}\n"
            if evidence.provenance:
                evidence_text += f"Source: {evidence.provenance.source_id}\n"
            evidence_items.append(evidence_text)
        
        return "\n---\n".join(evidence_items)
    
    def _fallback_retrieval_validation(self, answer: str, state: ReactorState) -> RetrievalValidation:
        """Fallback retrieval validation using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M11 Retrieval Validation - Using heuristic validation")
        
        # Simple heuristic checks
        citation_count = self._count_citations(answer)
        evidence_count = len(state.evidences) if state.evidences else 0
        
        # Check for citation patterns
        has_evidence_ids = "[Evidence ID:" in answer or "[ev_" in answer
        has_source_references = any(phrase in answer.lower() for phrase in 
                                  ["according to", "based on", "source shows", "evidence indicates"])
        
        # Estimate retrieval coverage
        if has_evidence_ids and citation_count > 0:
            retrieval_coverage = min(1.0, citation_count / max(1, len(answer.split('.'))))
        elif has_source_references:
            retrieval_coverage = 0.7
        else:
            retrieval_coverage = 0.3
        
        is_retrieval_based = retrieval_coverage >= 0.8 and citation_count > 0
        
        non_retrieval_parts = []
        missing_citations = []
        
        if not has_evidence_ids:
            non_retrieval_parts.append("Missing evidence ID citations")
        if citation_count == 0:
            missing_citations.append("No citations found in answer")
        if retrieval_coverage < 0.5:
            non_retrieval_parts.append("Large portions appear to lack retrieval support")
        
        return RetrievalValidation(
            is_retrieval_based=is_retrieval_based,
            retrieval_coverage=retrieval_coverage,
            non_retrieval_parts=non_retrieval_parts,
            missing_citations=missing_citations,
            citation_accuracy=0.7 if citation_count > 0 else 0.0,
            evidence_support_score=min(1.0, evidence_count / 5),
            confidence=0.6
        )

    async def _analyze_answer_structure(self, answer: str, state: ReactorState) -> AnswerAnalysis:
        """Analyze the structure and quality of the answer."""
        prompt = self._get_prompt("m11_structure_analysis",
            "Analyze the structure, clarity, and coherence of this answer."
        )
        
        full_prompt = f"""{prompt}

<answer>
{answer}
</answer>

Return JSON with:
- answer_length: {len(answer)}
- structure_score: 0.0-1.0 (organization and flow)
- clarity_score: 0.0-1.0 (readability and understanding)
- coherence_score: 0.0-1.0 (logical consistency)
- key_points_covered: ["point1", "point2"]
- missing_elements: ["element1", "element2"]
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return AnswerAnalysis(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Structure analysis failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Structure Analysis - {e}")
            print(f"   → Using heuristic answer analysis")
            return self._fallback_answer_analysis(answer)
    
    async def _check_factual_accuracy(self, answer: str, state: ReactorState) -> AccuracyCheck:
        """Check factual accuracy of the answer against available evidence."""
        prompt = self._get_prompt("m11_accuracy_check",
            "Check the factual accuracy of this answer against the provided evidence."
        )
        
        evidence_text = self._prepare_evidence_text(state.evidences)
        
        full_prompt = f"""{prompt}

<answer>
{answer}
</answer>

<evidence>
{evidence_text}
</evidence>

Return JSON with:
- accuracy_score: 0.0-1.0
- verified_facts: ["fact1", "fact2"]
- questionable_claims: ["claim1", "claim2"]
- contradictions: ["contradiction1"]
- evidence_support_ratio: 0.0-1.0
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return AccuracyCheck(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Accuracy check failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Accuracy Check - {e}")
            print(f"   → Using heuristic accuracy check")
            return self._fallback_accuracy_check(answer, state.evidences)
    
    async def _validate_answer_citations(self, answer: str, state: ReactorState) -> CitationValidation:
        """Validate the quality and accuracy of citations in the answer."""
        # Count citations in answer
        citation_count = self._count_citations(answer)
        
        prompt = self._get_prompt("m11_citation_validation",
            "Validate the citations in this answer for accuracy and completeness."
        )
        
        evidence_text = self._prepare_evidence_text(state.evidences)
        
        full_prompt = f"""{prompt}

<answer>
{answer}
</answer>

<available_evidence>
{evidence_text}
</available_evidence>

Return JSON with:
- total_citations: {citation_count}
- valid_citations: number of valid citations
- citation_accuracy: 0.0-1.0
- missing_citations: ["claim needing citation"]
- citation_quality: "excellent" | "good" | "fair" | "poor"
- source_diversity: 0.0-1.0
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return CitationValidation(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Citation validation failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Citation Validation - {e}")
            print(f"   → Using heuristic citation validation")
            return self._fallback_citation_validation(answer, state.evidences)
    
    async def _assess_answer_completeness(self, answer: str, state: ReactorState) -> CompletenessAssessment:
        """Assess how completely the answer addresses the original query."""
        if not state.original_query:
            print(f"🔄 FALLBACK TRIGGERED: M11 Completeness Assessment - No original query")
            print(f"   → Using heuristic completeness assessment")
            return self._fallback_completeness_assessment(answer)
        
        prompt = self._get_prompt("m11_completeness_assessment",
            "Assess how completely this answer addresses the original query."
        )
        
        full_prompt = f"""{prompt}

<query>
{state.original_query.text}
</query>

<answer>
{answer}
</answer>

Return JSON with:
- completeness_score: 0.0-1.0
- query_coverage: 0.0-1.0
- depth_score: 0.0-1.0
- breadth_score: 0.0-1.0
- unanswered_aspects: ["aspect1", "aspect2"]
- additional_context_needed: ["context1", "context2"]
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return CompletenessAssessment(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Completeness assessment failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M11 Completeness Assessment - {e}")
            print(f"   → Using heuristic completeness assessment")
            return self._fallback_completeness_assessment(answer)
    
    def _calculate_overall_quality_score(self, state: ReactorState) -> float:
        """Calculate overall answer quality score from all assessments."""
        scores = []
        
        # Structure and clarity
        if hasattr(state, 'answer_analysis'):
            analysis = state.answer_analysis
            structure_avg = (analysis.structure_score + analysis.clarity_score + analysis.coherence_score) / 3
            scores.append(structure_avg)
        
        # Accuracy
        if hasattr(state, 'accuracy_check'):
            scores.append(state.accuracy_check.accuracy_score)
        
        # Citations
        if hasattr(state, 'citation_validation'):
            scores.append(state.citation_validation.citation_accuracy)
        
        # Completeness
        if hasattr(state, 'completeness_assessment'):
            scores.append(state.completeness_assessment.completeness_score)
        
        # Calculate weighted average
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5  # Default neutral score
    
    def _prepare_evidence_text(self, evidences: List[EvidenceItem]) -> str:
        """Prepare evidence text for LLM analysis."""
        if not evidences:
            return "No evidence available"
        
        evidence_snippets = []
        for i, evidence in enumerate(evidences[:5]):  # Limit to top 5 for context
            snippet = f"Evidence {i+1}: {evidence.content[:200]}..."
            evidence_snippets.append(snippet)
        
        return "\n\n".join(evidence_snippets)
    
    def _count_citations(self, answer: str) -> int:
        """Count citations in the answer text."""
        # Simple citation counting - look for common citation patterns
        citation_patterns = [
            "[", "]",  # [1], [Source 1]
            "(", ")",  # (Smith, 2023)
            "according to",
            "as stated in",
            "source:",
            "ref:"
        ]
        
        citation_count = 0
        answer_lower = answer.lower()
        
        # Count bracket citations
        citation_count += answer.count("[")
        
        # Count reference phrases
        for pattern in ["according to", "as stated in", "source:", "ref:"]:
            citation_count += answer_lower.count(pattern)
        
        return citation_count
    
    def _fallback_answer_analysis(self, answer: str) -> AnswerAnalysis:
        """Fallback answer analysis using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M11 Answer Analysis - Using heuristic analysis")
        length = len(answer)
        
        # Simple heuristic scoring
        structure_score = min(1.0, length / 500)  # Longer answers tend to be more structured
        clarity_score = 0.8 if length > 100 else 0.5  # Assume reasonable clarity for substantial answers
        coherence_score = 0.7  # Default assumption
        
        # Extract key points (simple sentence splitting)
        sentences = answer.split('.')
        key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
        
        missing_elements = []
        if length < 100:
            missing_elements.append("Insufficient detail")
        if not any(word in answer.lower() for word in ["because", "therefore", "thus", "since"]):
            missing_elements.append("Limited reasoning explanation")
        
        return AnswerAnalysis(
            answer_length=length,
            structure_score=structure_score,
            clarity_score=clarity_score,
            coherence_score=coherence_score,
            key_points_covered=key_points,
            missing_elements=missing_elements,
            confidence=0.6
        )
    
    def _fallback_accuracy_check(self, answer: str, evidences: List[EvidenceItem]) -> AccuracyCheck:
        """Fallback accuracy check using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M11 Accuracy Check - Using heuristic accuracy check with {len(evidences)} evidences")
        if not evidences:
            return AccuracyCheck(
                accuracy_score=0.5,
                verified_facts=[],
                questionable_claims=["Unable to verify without evidence"],
                contradictions=[],
                evidence_support_ratio=0.0,
                confidence=0.3
            )
        
        # Simple heuristic: assume moderate accuracy if evidence exists
        accuracy_score = 0.7
        
        # Extract potential facts (sentences with specific claims)
        sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 10]
        verified_facts = sentences[:2]  # Assume first few are most likely to be factual
        
        questionable_claims = []
        if len(sentences) > 5:
            questionable_claims = ["Complex claims require detailed verification"]
        
        evidence_support_ratio = min(1.0, len(evidences) / 5)  # More evidence = better support
        
        return AccuracyCheck(
            accuracy_score=accuracy_score,
            verified_facts=verified_facts,
            questionable_claims=questionable_claims,
            contradictions=[],
            evidence_support_ratio=evidence_support_ratio,
            confidence=0.6
        )
    
    def _fallback_citation_validation(self, answer: str, evidences: List[EvidenceItem]) -> CitationValidation:
        """Fallback citation validation using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M11 Citation Validation - Using heuristic validation with {len(evidences)} evidences")
        citation_count = self._count_citations(answer)
        
        # Simple validation
        valid_citations = min(citation_count, len(evidences))
        citation_accuracy = valid_citations / max(1, citation_count)
        
        missing_citations = []
        if citation_count == 0:
            missing_citations = ["Answer lacks citations"]
        elif citation_count < len(answer.split('.')) / 3:
            missing_citations = ["More citations needed for claims"]
        
        quality_map = {
            0: "poor",
            1: "fair", 
            2: "good",
            3: "excellent"
        }
        citation_quality = quality_map.get(min(3, citation_count), "poor")
        
        # Source diversity based on evidence sources
        unique_sources = set()
        for evidence in evidences:
            if evidence.provenance:
                unique_sources.add(evidence.provenance.source_id)
        
        source_diversity = min(1.0, len(unique_sources) / 3)
        
        return CitationValidation(
            total_citations=citation_count,
            valid_citations=valid_citations,
            citation_accuracy=citation_accuracy,
            missing_citations=missing_citations,
            citation_quality=citation_quality,
            source_diversity=source_diversity,
            confidence=0.7
        )
    
    def _fallback_completeness_assessment(self, answer: str) -> CompletenessAssessment:
        """Fallback completeness assessment using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M11 Completeness Assessment - Using heuristic assessment")
        length = len(answer)
        
        # Simple heuristic scoring
        completeness_score = min(1.0, length / 300)
        query_coverage = 0.7  # Assume reasonable coverage
        depth_score = min(1.0, length / 400)
        breadth_score = 0.6  # Default assumption
        
        unanswered_aspects = []
        if length < 150:
            unanswered_aspects.append("Answer may lack sufficient detail")
        
        additional_context_needed = []
        if length < 200:
            additional_context_needed.append("More context and examples needed")
        
        return CompletenessAssessment(
            completeness_score=completeness_score,
            query_coverage=query_coverage,
            depth_score=depth_score,
            breadth_score=breadth_score,
            unanswered_aspects=unanswered_aspects,
            additional_context_needed=additional_context_needed,
            confidence=0.6
        )


# Module instance
answer_check_langgraph = AnswerCheckLangGraph()


# LangGraph node function
async def answer_check_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M11 - Answer Check."""
    return await answer_check_langgraph.execute(state)