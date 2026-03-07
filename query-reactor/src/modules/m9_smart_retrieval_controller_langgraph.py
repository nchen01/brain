"""M9 - Smart Retrieval Controller (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, EvidenceItem, WorkUnit
from .base import LLMModule


class EvidenceAssessment(BaseModel):
    """Pydantic model for current evidence quality assessment."""
    total_evidence: int = Field(description="Total evidence items available")
    quality_distribution: Dict[str, int] = Field(description="Distribution by quality tiers")
    coverage_score: float = Field(ge=0.0, le=1.0, description="Topic coverage completeness")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence in evidence")
    gaps_identified: List[str] = Field(description="Identified information gaps")
    assessment_confidence: float = Field(ge=0.0, le=1.0, description="Assessment confidence")


class ControlDecision(BaseModel):
    """Pydantic model for next action decision."""
    decision: str = Field(description="Control decision: continue, refine, terminate, or expand")
    decision_rationale: str = Field(description="Reasoning behind the decision")
    priority_level: str = Field(description="Priority level: low, medium, high, critical")
    expected_improvement: float = Field(ge=0.0, le=1.0, description="Expected improvement from action")
    resource_cost: str = Field(description="Estimated resource cost: low, medium, high")
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence")


class ActionPlan(BaseModel):
    """Pydantic model for detailed action plan."""
    action_type: str = Field(description="Type of action to take")
    target_modules: List[str] = Field(description="Modules to invoke or adjust")
    parameters: Dict[str, Any] = Field(description="Parameters for the action")
    success_criteria: List[str] = Field(description="Criteria for measuring success")
    fallback_plan: str = Field(description="Fallback if primary action fails")
    estimated_duration: str = Field(description="Estimated time to complete")
    confidence: float = Field(ge=0.0, le=1.0, description="Plan confidence")


class ControlExecution(BaseModel):
    """Pydantic model for control action results."""
    action_executed: str = Field(description="Action that was executed")
    execution_status: str = Field(description="Status: success, partial, failed")
    results_achieved: List[str] = Field(description="Results achieved by the action")
    performance_metrics: Dict[str, float] = Field(description="Performance metrics")
    issues_encountered: List[str] = Field(description="Issues encountered during execution")
    next_recommendation: str = Field(description="Recommendation for next step")
    confidence: float = Field(ge=0.0, le=1.0, description="Execution confidence")


class SmartRetrievalControllerLangGraph(LLMModule):
    """M9 - Smart retrieval controller with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M9_LG", "src.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self.max_turns = 1  # Maximum retrieval turns before giving up
        self.quality_threshold = 0.05  # Minimum quality threshold for "good enough"
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for smart retrieval control."""
        workflow = StateGraph(ReactorState)
        
        # Simplified workflow for 3-path routing
        workflow.add_node("assess_and_route", self._assess_and_route_node)
        
        workflow.add_edge("assess_and_route", END)
        
        workflow.set_entry_point("assess_and_route")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute smart retrieval control with 3-path routing logic."""
        self._update_state_module(state)
        self._log_execution_start(state, "Executing smart retrieval control")
        
        # Initialize retrieval turn counter
        if not hasattr(state, 'retrieval_turns'):
            state.retrieval_turns = 0
        
        try:
            # Assess current evidence quality
            assessment = await self._assess_current_evidence(state)
            state.evidence_assessment = assessment
            
            # Make routing decision based on 3-path logic
            routing_decision = self._make_routing_decision(assessment, state)
            state.routing_decision = routing_decision

            # Set smr_decision field expected by graph.py routing function
            next_module = routing_decision.get("next_module", "M12")
            if next_module == "M10":
                state.smr_decision = "answer_ready"
            elif next_module == "M1":
                state.smr_decision = "needs_better_decomposition"
            else:
                state.smr_decision = "insufficient_evidence"

            self._log_execution_end(state, f"Routing decision: {routing_decision['next_module']} - {routing_decision['reason']}")

            return state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M9 Execute - {e}")
            print(f"   → Returning original state")
            return state
    
    async def _assess_and_route_node(self, state: ReactorState) -> ReactorState:
        """Assess evidence and make routing decision."""
        try:
            # Assess current evidence quality
            assessment = await self._assess_current_evidence(state)
            state.evidence_assessment = assessment
            
            # Make routing decision based on 3-path logic
            routing_decision = self._make_routing_decision(assessment, state)
            state.routing_decision = routing_decision
            
            return state
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Assess and route failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M9 Assess and Route - {e}")
            print(f"   → Using fallback routing decision")
            
            # Fallback routing decision
            state.routing_decision = {
                "next_module": "M12",
                "reason": "Assessment failed, terminating with error message",
                "message_for_m12": "Unable to assess evidence quality due to system error"
            }
            return state
    
    def _make_routing_decision(self, assessment: EvidenceAssessment, state: ReactorState) -> Dict[str, Any]:
        """
        Make 3-path routing decision based on evidence quality and turn count.
        
        Path 1: Retrieval not good + max turn not reached → go to M1
        Path 2: Max turn reached → go to M12 with "no relevant data" message  
        Path 3: Retrieval is good enough → go to M10
        """
        
        current_turns = getattr(state, 'retrieval_turns', 0)
        evidence_quality = assessment.confidence_score
        coverage_score = assessment.coverage_score
        
        # Calculate overall quality score (weighted average)
        overall_quality = (evidence_quality * 0.6) + (coverage_score * 0.4)
        
        # Analyze WorkUnit performance for feedback
        workunit_feedback = self._analyze_workunit_performance(state, assessment)
        
        self.logger.info(f"[{self.module_code}] Quality assessment: evidence={evidence_quality:.3f}, coverage={coverage_score:.3f}, overall={overall_quality:.3f}")
        self.logger.info(f"[{self.module_code}] Turn status: current={current_turns}, max={self.max_turns}")
        
        # Path 2: Max turns reached - go to M12 regardless of quality
        if current_turns >= self.max_turns:
            print(f"🔄 M9 ROUTING: Max turns ({self.max_turns}) reached")
            print(f"   → Routing to M12 with limitation message")
            
            if overall_quality < self.quality_threshold:
                message = f"Unable to find sufficient relevant data after {self.max_turns} retrieval attempts. The available information may be limited or incomplete."
            else:
                message = f"Retrieval completed after {self.max_turns} attempts. Proceeding with available information."
            
            return {
                "next_module": "M12",
                "reason": f"Maximum retrieval turns ({self.max_turns}) reached",
                "message_for_m12": message,
                "quality_score": overall_quality,
                "turns_used": current_turns,
                "workunit_feedback": workunit_feedback,
                "retrieval_limitations": {
                    "max_turns_reached": True,
                    "final_quality": overall_quality,
                    "evidence_gaps": assessment.gaps_identified,
                    "quality_distribution": assessment.quality_distribution
                }
            }
        
        # Path 3: Good quality - go to M10
        if overall_quality >= self.quality_threshold:
            print(f"🔄 M9 ROUTING: Good quality ({overall_quality:.3f} >= {self.quality_threshold})")
            print(f"   → Routing to M10 for answer generation")
            
            return {
                "next_module": "M10",
                "reason": f"Evidence quality sufficient ({overall_quality:.3f})",
                "quality_score": overall_quality,
                "turns_used": current_turns,
                "evidence_count": assessment.total_evidence,
                "workunit_feedback": workunit_feedback
            }
        
        # Path 1: Poor quality but turns remaining - go to M1
        print(f"🔄 M9 ROUTING: Poor quality ({overall_quality:.3f} < {self.quality_threshold}) with turns remaining")
        print(f"   → Routing to M1 for query refinement")
        
        return {
            "next_module": "M1",
            "reason": f"Evidence quality insufficient ({overall_quality:.3f}), refining query",
            "quality_score": overall_quality,
            "turns_used": current_turns,
            "improvement_needed": self.quality_threshold - overall_quality,
            "workunit_feedback": workunit_feedback,
            "refinement_guidance": {
                "current_approach_issues": workunit_feedback["issues_identified"],
                "suggested_improvements": workunit_feedback["improvement_suggestions"],
                "evidence_gaps": assessment.gaps_identified,
                "quality_problems": self._identify_quality_problems(assessment),
                "alternative_strategies": self._suggest_alternative_strategies(workunit_feedback)
            }
        }

    def _analyze_workunit_performance(self, state: ReactorState, assessment: EvidenceAssessment) -> Dict[str, Any]:
        """Analyze WorkUnit performance to provide feedback for M1 and M12."""
        
        workunits = state.workunits or []
        evidences = state.evidences or []
        
        if not workunits:
            return {
                "total_workunits": 0,
                "issues_identified": ["No WorkUnits available for analysis"],
                "improvement_suggestions": ["Generate more specific sub-questions"],
                "workunit_effectiveness": {}
            }
        
        # Analyze each WorkUnit's effectiveness
        workunit_analysis = {}
        total_evidence_per_wu = {}
        avg_quality_per_wu = {}
        
        for wu in workunits:
            wu_evidences = [e for e in evidences if e.workunit_id == wu.id]
            total_evidence_per_wu[str(wu.id)] = len(wu_evidences)
            
            if wu_evidences:
                avg_quality = sum(e.score_raw for e in wu_evidences) / len(wu_evidences)
                avg_quality_per_wu[str(wu.id)] = avg_quality
                
                # Analyze WorkUnit effectiveness
                if avg_quality < 0.5:
                    effectiveness = "poor"
                    issues = ["Low quality evidence retrieved", "Sub-question may be too broad or unclear"]
                elif avg_quality < 0.7:
                    effectiveness = "moderate" 
                    issues = ["Mixed quality evidence", "Sub-question could be more specific"]
                else:
                    effectiveness = "good"
                    issues = []
                
                if len(wu_evidences) < 2:
                    issues.append("Insufficient evidence retrieved")
                    
            else:
                avg_quality_per_wu[str(wu.id)] = 0.0
                effectiveness = "failed"
                issues = ["No evidence retrieved", "Sub-question may be unanswerable or too specific"]
            
            workunit_analysis[str(wu.id)] = {
                "text": wu.text,
                "evidence_count": len(wu_evidences),
                "avg_quality": avg_quality_per_wu[str(wu.id)],
                "effectiveness": effectiveness,
                "issues": issues
            }
        
        # Identify overall issues
        overall_issues = []
        improvement_suggestions = []
        
        # Check for common problems
        low_quality_wus = [wu_id for wu_id, analysis in workunit_analysis.items() 
                          if analysis["avg_quality"] < 0.5]
        no_evidence_wus = [wu_id for wu_id, analysis in workunit_analysis.items() 
                          if analysis["evidence_count"] == 0]
        
        if len(low_quality_wus) > len(workunits) * 0.5:
            overall_issues.append("Majority of sub-questions producing low-quality evidence")
            improvement_suggestions.append("Reformulate sub-questions to be more specific and answerable")
        
        if len(no_evidence_wus) > 0:
            overall_issues.append(f"{len(no_evidence_wus)} sub-questions retrieved no evidence")
            improvement_suggestions.append("Replace unanswerable sub-questions with alternative approaches")
        
        if assessment.coverage_score < 0.5:
            overall_issues.append("Poor topic coverage across all sub-questions")
            improvement_suggestions.append("Generate sub-questions that cover different aspects of the main query")
        
        # Check for redundancy
        if len(workunits) > 1:
            similar_wus = self._detect_similar_workunits(workunits)
            if similar_wus:
                overall_issues.append("Some sub-questions are too similar")
                improvement_suggestions.append("Diversify sub-questions to cover different angles")
        
        return {
            "total_workunits": len(workunits),
            "workunit_analysis": workunit_analysis,
            "issues_identified": overall_issues,
            "improvement_suggestions": improvement_suggestions,
            "performance_metrics": {
                "avg_evidence_per_workunit": sum(total_evidence_per_wu.values()) / len(workunits) if workunits else 0,
                "avg_quality_across_workunits": sum(avg_quality_per_wu.values()) / len(workunits) if workunits else 0,
                "successful_workunits": len([wu for wu in workunit_analysis.values() if wu["effectiveness"] in ["good", "moderate"]]),
                "failed_workunits": len([wu for wu in workunit_analysis.values() if wu["effectiveness"] == "failed"])
            }
        }
    
    def _detect_similar_workunits(self, workunits: List[WorkUnit]) -> List[Dict[str, Any]]:
        """Detect similar WorkUnits that might be redundant."""
        similar_pairs = []
        
        for i, wu1 in enumerate(workunits):
            for j, wu2 in enumerate(workunits[i+1:], i+1):
                # Simple similarity check based on common words
                words1 = set(wu1.text.lower().split())
                words2 = set(wu2.text.lower().split())
                
                # Remove common stop words
                stop_words = {"what", "how", "why", "when", "where", "is", "are", "the", "a", "an", "and", "or", "but"}
                words1 = words1 - stop_words
                words2 = words2 - stop_words
                
                if words1 and words2:
                    similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                    if similarity > 0.6:  # 60% similarity threshold
                        similar_pairs.append({
                            "workunit1": {"id": str(wu1.id), "text": wu1.text},
                            "workunit2": {"id": str(wu2.id), "text": wu2.text},
                            "similarity": similarity
                        })
        
        return similar_pairs
    
    def _identify_quality_problems(self, assessment: EvidenceAssessment) -> List[str]:
        """Identify specific quality problems with current evidence."""
        problems = []
        
        if assessment.total_evidence == 0:
            problems.append("No evidence retrieved")
        elif assessment.total_evidence < 3:
            problems.append("Insufficient evidence volume")
        
        if assessment.confidence_score < 0.3:
            problems.append("Very low evidence quality scores")
        elif assessment.confidence_score < 0.5:
            problems.append("Below-average evidence quality")
        
        if assessment.coverage_score < 0.3:
            problems.append("Poor topic coverage")
        elif assessment.coverage_score < 0.5:
            problems.append("Incomplete topic coverage")
        
        # Analyze quality distribution
        quality_dist = assessment.quality_distribution
        total_items = sum(quality_dist.values())
        
        if total_items > 0:
            high_quality_ratio = quality_dist.get("high", 0) / total_items
            low_quality_ratio = quality_dist.get("low", 0) / total_items
            
            if high_quality_ratio < 0.2:
                problems.append("Very few high-quality evidence items")
            if low_quality_ratio > 0.5:
                problems.append("Too many low-quality evidence items")
        
        return problems
    
    def _suggest_alternative_strategies(self, workunit_feedback: Dict[str, Any]) -> List[str]:
        """Suggest alternative strategies based on WorkUnit performance."""
        strategies = []
        
        failed_count = workunit_feedback["performance_metrics"]["failed_workunits"]
        total_count = workunit_feedback["total_workunits"]
        
        if failed_count > total_count * 0.5:
            strategies.append("Try broader, more general sub-questions")
            strategies.append("Focus on fundamental concepts rather than specific details")
        
        if workunit_feedback["performance_metrics"]["avg_evidence_per_workunit"] < 2:
            strategies.append("Reformulate sub-questions to be more searchable")
            strategies.append("Use more common terminology and phrases")
        
        if workunit_feedback["performance_metrics"]["avg_quality_across_workunits"] < 0.5:
            strategies.append("Break down complex questions into simpler components")
            strategies.append("Focus on factual rather than opinion-based questions")
        
        # Check for specific issues
        issues = workunit_feedback["issues_identified"]
        if "too similar" in " ".join(issues).lower():
            strategies.append("Generate more diverse sub-questions covering different aspects")
        
        if "unanswerable" in " ".join(issues).lower():
            strategies.append("Validate sub-questions against available knowledge sources")
        
        return strategies

    async def _assess_current_evidence(self, state: ReactorState) -> EvidenceAssessment:
        """Assess the current state of evidence collection."""
        evidences = state.evidences or []
        
        if not evidences:
            return EvidenceAssessment(
                total_evidence=0,
                quality_distribution={"high": 0, "medium": 0, "low": 0},
                coverage_score=0.0,
                confidence_score=0.0,
                gaps_identified=["No evidence available"],
                assessment_confidence=1.0
            )
        
        # Analyze quality distribution
        quality_dist = {"high": 0, "medium": 0, "low": 0}
        total_confidence = 0.0
        
        for evidence in evidences:
            if evidence.score_raw >= 0.8:
                quality_dist["high"] += 1
            elif evidence.score_raw >= 0.5:
                quality_dist["medium"] += 1
            else:
                quality_dist["low"] += 1
            total_confidence += evidence.score_raw
        
        avg_confidence = total_confidence / len(evidences)
        
        # Assess coverage using LLM
        coverage_score = await self._assess_topic_coverage(evidences, state)
        
        # Identify gaps
        gaps = await self._identify_information_gaps(evidences, state)
        
        return EvidenceAssessment(
            total_evidence=len(evidences),
            quality_distribution=quality_dist,
            coverage_score=coverage_score,
            confidence_score=avg_confidence,
            gaps_identified=gaps,
            assessment_confidence=0.85
        )
    
    async def _make_control_decision(self, assessment: Optional[EvidenceAssessment], 
                                   state: ReactorState) -> ControlDecision:
        """Make intelligent control decision based on evidence assessment."""
        if not assessment:
            return self._fallback_control_decision()
        
        prompt = self._get_prompt("m9_control_decision",
            "Analyze the evidence assessment and decide on the next action."
        )
        
        query_text = state.original_query.text if state.original_query else "Unknown query"
        
        full_prompt = f"""{prompt}

<query>{query_text}</query>
<evidence_assessment>
Total evidence: {assessment.total_evidence}
Quality distribution: {assessment.quality_distribution}
Coverage score: {assessment.coverage_score}
Confidence score: {assessment.confidence_score}
Gaps: {assessment.gaps_identified}
</evidence_assessment>

Return JSON with:
- decision: "continue" | "refine" | "terminate" | "expand"
- decision_rationale: "detailed reasoning"
- priority_level: "low" | "medium" | "high" | "critical"
- expected_improvement: 0.0-1.0
- resource_cost: "low" | "medium" | "high"
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return ControlDecision(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Control decision failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M9 Control Decision - {e}")
            print(f"   → Using default control decision")
            return self._fallback_control_decision()
    
    async def _create_action_plan(self, decision: ControlDecision, state: ReactorState) -> ActionPlan:
        """Create detailed action plan based on control decision."""
        prompt = self._get_prompt("m9_action_planning",
            "Create a detailed action plan based on the control decision."
        )
        
        full_prompt = f"""{prompt}

<decision>
Action: {decision.decision}
Rationale: {decision.decision_rationale}
Priority: {decision.priority_level}
</decision>

Return JSON with:
- action_type: "retrieve_more" | "refine_query" | "change_strategy" | "terminate"
- target_modules: ["M3", "M5"] (list of modules to invoke)
- parameters: {{"threshold": 0.8, "max_results": 10}}
- success_criteria: ["criteria1", "criteria2"]
- fallback_plan: "fallback description"
- estimated_duration: "short" | "medium" | "long"
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return ActionPlan(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Action planning failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M9 Action Planning - {e}")
            print(f"   → Using fallback action plan")
            return self._fallback_action_plan(decision)
    
    async def _execute_control_action(self, action_plan: ActionPlan, state: ReactorState) -> ControlExecution:
        """Execute the planned control action."""
        action_type = action_plan.action_type
        
        if action_type == "retrieve_more":
            result = await self._execute_retrieve_more(action_plan, state)
        elif action_type == "refine_query":
            result = await self._execute_refine_query(action_plan, state)
        elif action_type == "change_strategy":
            result = await self._execute_change_strategy(action_plan, state)
        elif action_type == "terminate":
            result = await self._execute_terminate(action_plan, state)
        else:
            result = self._fallback_execution_result(action_plan)
        
        return result
    
    async def _assess_topic_coverage(self, evidences: List[EvidenceItem], state: ReactorState) -> float:
        """Assess how well the evidence covers the topic."""
        if not evidences or not state.original_query:
            return 0.0
        
        prompt = self._get_prompt("m9_coverage_assessment",
            "Assess how well the evidence covers the query topic."
        )
        
        evidence_summary = "\n".join([e.content[:100] + "..." for e in evidences[:5]])
        
        full_prompt = f"""{prompt}

<query>{state.original_query.text}</query>
<evidence_summary>
{evidence_summary}
</evidence_summary>

Return only a number between 0.0 and 1.0 representing coverage completeness:"""
        
        try:
            response = await self._call_llm(full_prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Coverage assessment failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M9 Coverage Assessment - {e}")
            print(f"   → Using neutral coverage score (0.5)")
            return 0.5  # Default neutral score
    
    async def _identify_information_gaps(self, evidences: List[EvidenceItem], state: ReactorState) -> List[str]:
        """Identify gaps in information coverage."""
        if not evidences or not state.original_query:
            return ["Insufficient evidence for gap analysis"]
        
        prompt = self._get_prompt("m9_gap_identification",
            "Identify information gaps in the evidence relative to the query."
        )
        
        evidence_summary = "\n".join([e.content[:100] + "..." for e in evidences[:5]])
        
        full_prompt = f"""{prompt}

<query>{state.original_query.text}</query>
<evidence_summary>
{evidence_summary}
</evidence_summary>

Return JSON array of gap descriptions:
["gap1", "gap2", "gap3"]"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            gaps = json.loads(response)
            return gaps if isinstance(gaps, list) else ["Gap analysis failed"]
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Gap identification failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M9 Gap Identification - {e}")
            print(f"   → Using generic gap message")
            return ["Unable to identify specific gaps"]
    
    async def _execute_retrieve_more(self, action_plan: ActionPlan, state: ReactorState) -> ControlExecution:
        """Execute action to retrieve more evidence."""
        # Simulate retrieving more evidence
        original_count = len(state.evidences)
        
        # In a real implementation, this would trigger additional retrieval modules
        # For now, we'll simulate the action
        
        return ControlExecution(
            action_executed="retrieve_more",
            execution_status="success",
            results_achieved=[f"Initiated additional retrieval from {action_plan.target_modules}"],
            performance_metrics={"original_evidence": original_count},
            issues_encountered=[],
            next_recommendation="Monitor retrieval progress",
            confidence=0.8
        )
    
    async def _execute_refine_query(self, action_plan: ActionPlan, state: ReactorState) -> ControlExecution:
        """Execute action to refine the query."""
        # Simulate query refinement
        return ControlExecution(
            action_executed="refine_query",
            execution_status="success",
            results_achieved=["Query refinement parameters updated"],
            performance_metrics={"refinement_applied": 1},
            issues_encountered=[],
            next_recommendation="Re-run retrieval with refined query",
            confidence=0.75
        )
    
    async def _execute_change_strategy(self, action_plan: ActionPlan, state: ReactorState) -> ControlExecution:
        """Execute action to change retrieval strategy."""
        # Simulate strategy change
        return ControlExecution(
            action_executed="change_strategy",
            execution_status="success",
            results_achieved=["Retrieval strategy updated"],
            performance_metrics={"strategy_changed": 1},
            issues_encountered=[],
            next_recommendation="Execute new strategy",
            confidence=0.7
        )
    
    async def _execute_terminate(self, action_plan: ActionPlan, state: ReactorState) -> ControlExecution:
        """Execute termination action."""
        return ControlExecution(
            action_executed="terminate",
            execution_status="success",
            results_achieved=["Retrieval process terminated"],
            performance_metrics={"final_evidence_count": len(state.evidences)},
            issues_encountered=[],
            next_recommendation="Proceed to answer generation",
            confidence=0.9
        )
    
    def _fallback_control_decision(self) -> ControlDecision:
        """Fallback control decision when LLM analysis fails."""
        print(f"🔄 EXECUTING FALLBACK: M9 Control Decision - Using default continue decision")
        return ControlDecision(
            decision="continue",
            decision_rationale="Default decision due to analysis failure",
            priority_level="medium",
            expected_improvement=0.1,
            resource_cost="low",
            confidence=0.5
        )
    
    def _fallback_action_plan(self, decision: ControlDecision) -> ActionPlan:
        """Fallback action plan when planning fails."""
        print(f"🔄 EXECUTING FALLBACK: M9 Action Plan - Using default action plan for {decision.decision}")
        action_type_map = {
            "continue": "retrieve_more",
            "refine": "refine_query",
            "terminate": "terminate",
            "expand": "retrieve_more"
        }
        
        action_type = action_type_map.get(decision.decision, "retrieve_more")
        
        return ActionPlan(
            action_type=action_type,
            target_modules=["M3", "M5"],
            parameters={"threshold": 0.6},
            success_criteria=["Improved evidence quality"],
            fallback_plan="Terminate if no improvement",
            estimated_duration="medium",
            confidence=0.6
        )
    
    def _fallback_execution_result(self, action_plan: ActionPlan) -> ControlExecution:
        """Fallback execution result when execution fails."""
        return ControlExecution(
            action_executed=action_plan.action_type,
            execution_status="failed",
            results_achieved=[],
            performance_metrics={},
            issues_encountered=["Execution failed"],
            next_recommendation="Try alternative approach",
            confidence=0.3
        )


# Module instance
smart_retrieval_controller_langgraph = SmartRetrievalControllerLangGraph()


# LangGraph node function
async def smart_retrieval_controller_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M9 - Smart Retrieval Controller."""
    return await smart_retrieval_controller_langgraph.execute(state)