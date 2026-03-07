"""M10 - Answer Creator (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, Answer, Citation, RankedEvidence, WorkUnit
from .base import LLMModule


class EvidenceAnalysis(BaseModel):
    """Pydantic model for evidence analysis."""
    evidence_id: str = Field(description="Evidence item ID")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to query")
    quality_score: float = Field(ge=0.0, le=1.0, description="Evidence quality")
    key_points: List[str] = Field(description="Key information points")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in analysis")


class WorkunitAnswerPlan(BaseModel):
    """Pydantic model for workunit answer planning."""
    workunit_id: str = Field(description="WorkUnit ID")
    has_sufficient_evidence: bool = Field(description="Whether sufficient evidence exists")
    selected_evidence: List[str] = Field(description="Selected evidence IDs")
    answer_strategy: str = Field(description="Strategy for answering (synthesis, extraction, etc.)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in answer plan")


class AnswerContent(BaseModel):
    """Pydantic model for generated answer content."""
    text: str = Field(description="Generated answer text")
    citations: List[Dict[str, Any]] = Field(description="Citation information")
    limitations: List[str] = Field(default_factory=list, description="Answer limitations")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in answer")
    reasoning: str = Field(description="Reasoning behind answer generation")


class AnswerCreatorLangGraph(LLMModule):
    """M10 - Answer creation with LangGraph orchestration and Pydantic validation."""
    
    def __init__(self):
        super().__init__("M10_LG", "ac.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for answer creation."""
        workflow = StateGraph(ReactorState)
        
        # Add processing nodes
        workflow.add_node("analyze_evidence", self._analyze_evidence_node)
        workflow.add_node("plan_answers", self._plan_answers_node)
        workflow.add_node("generate_content", self._generate_content_node)
        workflow.add_node("synthesize_answer", self._synthesize_answer_node)
        workflow.add_node("validate_answer", self._validate_answer_node)
        
        # Define workflow edges
        workflow.add_edge("analyze_evidence", "plan_answers")
        workflow.add_edge("plan_answers", "generate_content")
        workflow.add_edge("generate_content", "synthesize_answer")
        workflow.add_edge("synthesize_answer", "validate_answer")
        workflow.add_edge("validate_answer", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_evidence")
        
        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute answer creation using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Creating answer from evidence")
        
        try:
            # Check SMR decision
            smr_decision = getattr(state, 'smr_decision', 'answer_ready')
            
            if smr_decision == 'insufficient_evidence':
                # Create insufficient evidence response directly
                answer = await self._create_insufficient_evidence_answer(state)
                state.final_answer = answer
                self._log_execution_end(state, "Created insufficient evidence response")
                return state
            
            # Execute the LangGraph workflow
            thread_config = {
                "configurable": {
                    "thread_id": str(uuid4())
                }
            }
            
            # Call pipeline nodes directly (avoids LangGraph sub-graph dict serialization issues)
            result_state = await self._analyze_evidence_node(state)
            result_state = await self._plan_answers_node(result_state)
            result_state = await self._generate_content_node(result_state)
            result_state = await self._synthesize_answer_node(result_state)
            result_state = await self._validate_answer_node(result_state)

            citation_count = len(result_state.final_answer.citations) if result_state.final_answer else 0
            self._log_execution_end(result_state, f"Created answer with {citation_count} citations")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M10 Execute - {e}")
            print(f"   → Creating error response for user")
            # Fallback: create error response
            fallback_answer = Answer(
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                query_id=state.original_query.id,
                text="I apologize, but I encountered an error while generating the answer. Please try again.",
                citations=[],
                limitations=["Error occurred during answer generation"],
                confidence=0.0
            )
            state.final_answer = fallback_answer
            return state
    
    async def _analyze_evidence_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for analyzing available evidence."""
        evidence_analyses = []
        
        # Analyze evidence for each workunit
        for workunit in state.workunits:
            workunit_evidence = self._get_evidence_for_workunit(state, workunit)
            
            for evidence in workunit_evidence:
                analysis = await self._analyze_evidence_item(evidence, workunit)
                evidence_analyses.append(analysis)
        
        state.evidence_analyses = evidence_analyses
        return state
    
    async def _plan_answers_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for planning answer generation strategy."""
        answer_plans = []
        
        for workunit in state.workunits:
            plan = await self._create_workunit_answer_plan(workunit, state)
            answer_plans.append(plan)
        
        state.answer_plans = answer_plans
        return state
    
    async def _generate_content_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for generating answer content."""
        workunit_answers = []
        
        answer_plans = getattr(state, 'answer_plans', [])
        
        for plan in answer_plans:
            if plan.has_sufficient_evidence:
                content = await self._generate_workunit_content(plan, state)
                workunit_answers.append(content)
            else:
                # Create insufficient evidence content for this workunit
                insufficient_content = AnswerContent(
                    text=f"I couldn't find sufficient information to answer the part about '{self._get_workunit_text(plan.workunit_id, state)}'.",
                    citations=[],
                    limitations=[f"No reliable evidence found for workunit {plan.workunit_id}"],
                    confidence=0.0,
                    reasoning="Insufficient evidence available"
                )
                workunit_answers.append(insufficient_content)
        
        state.workunit_answers = workunit_answers
        return state
    
    async def _synthesize_answer_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for synthesizing final answer."""
        workunit_answers = getattr(state, 'workunit_answers', [])
        
        if not workunit_answers:
            # No content generated
            answer = await self._create_insufficient_evidence_answer(state)
        elif len(workunit_answers) == 1:
            # Single workunit answer
            answer = await self._create_single_answer(workunit_answers[0], state)
        else:
            # Multiple workunit answers - synthesize
            answer = await self._synthesize_multi_workunit_answer(workunit_answers, state)
        
        state.final_answer = answer
        return state
    
    async def _validate_answer_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for validating the generated answer."""
        if not state.final_answer:
            return state
        
        # Validate answer quality and completeness
        validation_result = await self._validate_answer_quality(state.final_answer, state)
        
        # Store validation metadata
        if not hasattr(state, 'answer_metadata'):
            state.answer_metadata = {}
        state.answer_metadata['validation'] = validation_result
        
        return state
    
    async def _analyze_evidence_item(self, evidence: Any, workunit: WorkUnit) -> EvidenceAnalysis:
        """Analyze individual evidence item with LLM."""
        prompt = self._get_prompt("m10_evidence_analysis",
            "Analyze this evidence item for relevance and quality in answering the given query."
        )
        
        evidence_content = getattr(evidence, 'content', str(evidence))
        
        full_prompt = f"""{prompt}

<query>
{workunit.text}
</query>

<evidence>
{evidence_content}
</evidence>

Return a JSON object with:
- evidence_id: "{evidence.id}"
- relevance_score: Relevance to query (0.0-1.0)
- quality_score: Evidence quality (0.0-1.0)
- key_points: List of key information points
- confidence: Confidence in analysis (0.0-1.0)"""
        
        try:
            response = await self._call_llm(full_prompt)
            
            # Parse and validate response with Pydantic
            import json
            response_data = json.loads(response)
            return EvidenceAnalysis(**response_data)
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Evidence analysis failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M10 Evidence Analysis - {e}")
            print(f"   → Using heuristic analysis")
            # Fallback analysis
            return EvidenceAnalysis(
                evidence_id=str(evidence.id),
                relevance_score=0.7,
                quality_score=0.6,
                key_points=[evidence_content[:100] + "..."],
                confidence=0.5
            )
    
    async def _create_workunit_answer_plan(self, workunit: WorkUnit, state: ReactorState) -> WorkunitAnswerPlan:
        """Create answer plan for a specific workunit."""
        workunit_evidence = self._get_evidence_for_workunit(state, workunit)
        evidence_analyses = getattr(state, 'evidence_analyses', [])
        
        # Filter analyses for this workunit's evidence
        relevant_analyses = [
            analysis for analysis in evidence_analyses
            if any(str(evidence.id) == analysis.evidence_id for evidence in workunit_evidence)
        ]
        
        # Determine if we have sufficient evidence
        high_quality_evidence = [
            analysis for analysis in relevant_analyses
            if analysis.relevance_score >= 0.6 and analysis.quality_score >= 0.5
        ]
        
        has_sufficient = len(high_quality_evidence) > 0
        selected_evidence = [analysis.evidence_id for analysis in high_quality_evidence[:3]]  # Top 3
        
        # Determine answer strategy
        if len(high_quality_evidence) == 1:
            strategy = "extraction"
        elif len(high_quality_evidence) > 1:
            strategy = "synthesis"
        else:
            strategy = "insufficient"
        
        confidence = sum(analysis.confidence for analysis in high_quality_evidence) / len(high_quality_evidence) if high_quality_evidence else 0.0
        
        return WorkunitAnswerPlan(
            workunit_id=str(workunit.id),
            has_sufficient_evidence=has_sufficient,
            selected_evidence=selected_evidence,
            answer_strategy=strategy,
            confidence=confidence
        )
    
    async def _generate_workunit_content(self, plan: WorkunitAnswerPlan, state: ReactorState) -> AnswerContent:
        """Generate content for a workunit using LLM."""
        workunit = self._get_workunit_by_id(plan.workunit_id, state)
        selected_evidence = self._get_evidence_by_ids(plan.selected_evidence, state)
        
        prompt = self._get_prompt("m10_content_generation",
            "Generate a comprehensive answer using the provided evidence. "
            "Use only information from the evidence and cite sources appropriately."
        )
        
        # Format evidence for prompt
        evidence_context = self._format_evidence_for_prompt(selected_evidence)
        
        # Format conversation history
        conversation_context = self._format_conversation_history(state)
        
        full_prompt = f"""{prompt}

<original_query>
{state.original_query.text}
</original_query>

<conversation_history>
{conversation_context}
</conversation_history>

<current_sub_question>
{workunit.text}
</current_sub_question>

<evidence>
{evidence_context}
</evidence>

<strategy>
{plan.answer_strategy}
</strategy>

Return a JSON object with:
- text: Generated answer text
- citations: List of citation objects with evidence_id, span_start, span_end
- limitations: List of any limitations or caveats
- confidence: Confidence in answer (0.0-1.0)
- reasoning: Reasoning behind answer generation"""
        
        try:
            response = await self._call_llm(full_prompt)
            
            # Parse and validate response with Pydantic
            import json
            response_data = json.loads(response)
            return AnswerContent(**response_data)
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Content generation failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M10 Content Generation - {e}")
            print(f"   → Using simple extraction fallback")
            # Fallback content generation
            return await self._fallback_content_generation(workunit, selected_evidence)
    
    async def _synthesize_multi_workunit_answer(self, workunit_answers: List[AnswerContent], state: ReactorState) -> Answer:
        """Synthesize multiple workunit answers into final answer."""
        prompt = self._get_prompt("m10_answer_synthesis",
            "Synthesize multiple answer components into a coherent, comprehensive response."
        )
        
        # Format workunit answers for synthesis
        answer_components = []
        workunits = state.workunits or []
        for i, content in enumerate(workunit_answers):
            workunit_text = workunits[i].text if i < len(workunits) else f"Sub-question {i+1}"
            answer_components.append(f"Sub-question: {workunit_text}\nAnswer: {content.text}")
        
        components_text = "\n\n".join(answer_components)
        
        # Format conversation history
        conversation_context = self._format_conversation_history(state)
        
        full_prompt = f"""{prompt}

<original_query>
{state.original_query.text}
</original_query>

<conversation_history>
{conversation_context}
</conversation_history>

<answer_components>
{components_text}
</answer_components>

Return a JSON object with:
- text: Synthesized answer text
- confidence: Overall confidence (0.0-1.0)
- reasoning: Synthesis reasoning"""
        
        try:
            response = await self._call_llm(full_prompt)
            
            # Parse response
            import json
            response_data = json.loads(response)
            
            # Combine all citations
            all_citations = []
            for content in workunit_answers:
                for citation_data in content.citations:
                    citation = Citation(
                        evidence_id=citation_data.get('evidence_id'),
                        span_start=citation_data.get('span_start', 0),
                        span_end=citation_data.get('span_end', len(response_data['text']))
                    )
                    all_citations.append(citation)
            
            # Combine all limitations
            all_limitations = []
            for content in workunit_answers:
                all_limitations.extend(content.limitations)
            
            return Answer(
                user_id=state.original_query.user_id,
                conversation_id=state.original_query.conversation_id,
                query_id=state.original_query.id,
                text=response_data['text'],
                citations=all_citations,
                limitations=all_limitations if all_limitations else None,
                confidence=response_data.get('confidence', 0.7)
            )
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Answer synthesis failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M10 Answer Synthesis - {e}")
            print(f"   → Using simple concatenation fallback")
            # Fallback synthesis
            return await self._fallback_answer_synthesis(workunit_answers, state)
    
    async def _create_single_answer(self, content: AnswerContent, state: ReactorState) -> Answer:
        """Create answer from single workunit content."""
        # Convert citation data to Citation objects
        citations = []
        for citation_data in content.citations:
            citation = Citation(
                evidence_id=citation_data.get('evidence_id'),
                span_start=citation_data.get('span_start', 0),
                span_end=citation_data.get('span_end', len(content.text))
            )
            citations.append(citation)
        
        return Answer(
            user_id=state.original_query.user_id,
            conversation_id=state.original_query.conversation_id,
            query_id=state.original_query.id,
            text=content.text,
            citations=citations,
            limitations=content.limitations if content.limitations else None,
            confidence=content.confidence
        )
    
    async def _create_insufficient_evidence_answer(self, state: ReactorState) -> Answer:
        """Create answer for insufficient evidence scenario."""
        smr_reasoning = getattr(state, 'smr_reasoning', 'Insufficient evidence found')
        
        answer_text = (
            "I'm sorry, but I couldn't find enough reliable information to answer your question. "
            "The available sources did not provide sufficient evidence to give you a confident response."
        )
        
        total_evidence = len(state.evidences)
        if total_evidence > 0:
            answer_text += f" While I found {total_evidence} potential sources, "
            answer_text += "they didn't meet the quality and relevance standards needed for a reliable answer."
        
        return Answer(
            user_id=state.original_query.user_id,
            conversation_id=state.original_query.conversation_id,
            query_id=state.original_query.id,
            text=answer_text,
            citations=[],
            limitations=[
                "Insufficient evidence available",
                smr_reasoning
            ],
            confidence=0.0
        )
    
    async def _validate_answer_quality(self, answer: Answer, state: ReactorState) -> Dict[str, Any]:
        """Validate answer quality and completeness."""
        validation = {
            'has_content': len(answer.text.strip()) > 0,
            'has_citations': len(answer.citations) > 0,
            'confidence_reasonable': 0.0 <= answer.confidence <= 1.0,
            'addresses_query': True,  # Would need LLM analysis for proper validation
            'overall_quality': 'good' if answer.confidence > 0.7 else 'moderate' if answer.confidence > 0.4 else 'low'
        }
        
        return validation
    
    def _get_evidence_for_workunit(self, state: ReactorState, workunit: WorkUnit) -> List[Any]:
        """Get evidence items for a specific workunit."""
        # Try ranked evidence first
        ranked_evidence = state.get_ranked_evidence(workunit.id)
        if ranked_evidence:
            return [e for e in ranked_evidence if e.is_primary]
        
        # Fall back to raw evidence
        return [e for e in state.evidences if e.workunit_id == workunit.id]
    
    def _get_workunit_by_id(self, workunit_id: str, state: ReactorState) -> Optional[WorkUnit]:
        """Get workunit by ID."""
        for workunit in state.workunits:
            if str(workunit.id) == workunit_id:
                return workunit
        return None
    
    def _get_workunit_text(self, workunit_id: str, state: ReactorState) -> str:
        """Get workunit text by ID."""
        workunit = self._get_workunit_by_id(workunit_id, state)
        return workunit.text if workunit else "unknown query"
    
    def _get_evidence_by_ids(self, evidence_ids: List[str], state: ReactorState) -> List[Any]:
        """Get evidence items by IDs."""
        evidence_items = []
        for evidence in state.evidences:
            if str(evidence.id) in evidence_ids:
                evidence_items.append(evidence)
        return evidence_items
    
    def _format_evidence_for_prompt(self, evidence_items: List[Any]) -> str:
        """Format evidence items for LLM prompt."""
        formatted_evidence = []
        for i, evidence in enumerate(evidence_items):
            content = getattr(evidence, 'content', str(evidence))
            title = getattr(evidence, 'title', f'Evidence {i+1}')
            source = getattr(evidence, 'provenance', {})
            source_info = getattr(source, 'source_id', 'Unknown source') if source else 'Unknown source'
            
            formatted_evidence.append(f"Evidence {i+1} (ID: {evidence.id}):\nTitle: {title}\nSource: {source_info}\nContent: {content}")
        
        return "\n\n".join(formatted_evidence)
    
    def _format_conversation_history(self, state: ReactorState) -> str:
        """Format conversation history for LLM prompt."""
        if not hasattr(state, 'conversation_history') or not state.conversation_history:
            return "No previous conversation history."
        
        history_items = []
        for turn in state.conversation_history:
            if hasattr(turn, 'user_message') and hasattr(turn, 'assistant_message'):
                history_items.append(f"User: {turn.user_message}")
                if turn.assistant_message:
                    history_items.append(f"Assistant: {turn.assistant_message}")
            elif hasattr(turn, 'text'):
                # Handle different conversation history formats
                role = getattr(turn, 'role', 'Unknown')
                history_items.append(f"{role}: {turn.text}")
        
        if not history_items:
            return "No previous conversation history."
        
        return "\n".join(history_items[-10:])  # Last 10 turns to avoid token limits
    
    async def _fallback_content_generation(self, workunit: WorkUnit, evidence_items: List[Any]) -> AnswerContent:
        """Fallback content generation using simple extraction."""
        print(f"🔄 EXECUTING FALLBACK: M10 Content Generation - Using simple extraction for WorkUnit {workunit.id}")
        if not evidence_items:
            return AnswerContent(
                text="No evidence available to answer this question.",
                citations=[],
                limitations=["No evidence found"],
                confidence=0.0,
                reasoning="No evidence available"
            )
        
        # Use first evidence item
        evidence = evidence_items[0]
        content = getattr(evidence, 'content', str(evidence))
        
        # Simple extraction
        answer_text = content[:300] + "..." if len(content) > 300 else content
        
        citations = [{
            'evidence_id': str(evidence.id),
            'span_start': 0,
            'span_end': len(answer_text)
        }]
        
        return AnswerContent(
            text=answer_text,
            citations=citations,
            limitations=["Simplified extraction from single source"],
            confidence=0.6,
            reasoning="Fallback extraction from available evidence"
        )
    
    async def _fallback_answer_synthesis(self, workunit_answers: List[AnswerContent], state: ReactorState) -> Answer:
        """Fallback answer synthesis using simple concatenation."""
        print(f"🔄 EXECUTING FALLBACK: M10 Answer Synthesis - Using simple concatenation for {len(workunit_answers)} answers")
        # Simple concatenation of answer texts
        answer_texts = [content.text for content in workunit_answers if content.text]
        combined_text = " ".join(answer_texts)
        
        # Combine all citations
        all_citations = []
        for content in workunit_answers:
            for citation_data in content.citations:
                citation = Citation(
                    evidence_id=citation_data.get('evidence_id'),
                    span_start=citation_data.get('span_start', 0),
                    span_end=citation_data.get('span_end', len(combined_text))
                )
                all_citations.append(citation)
        
        # Combine limitations
        all_limitations = []
        for content in workunit_answers:
            all_limitations.extend(content.limitations)
        
        # Calculate average confidence
        confidences = [content.confidence for content in workunit_answers]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return Answer(
            user_id=state.original_query.user_id,
            conversation_id=state.original_query.conversation_id,
            query_id=state.original_query.id,
            text=combined_text,
            citations=all_citations,
            limitations=all_limitations if all_limitations else None,
            confidence=avg_confidence
        )


# Module instance
answer_creator_langgraph = AnswerCreatorLangGraph()


# LangGraph node function for integration
async def answer_creator_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M10 - Answer Creator (LangGraph implementation)."""
    return await answer_creator_langgraph.execute(state)