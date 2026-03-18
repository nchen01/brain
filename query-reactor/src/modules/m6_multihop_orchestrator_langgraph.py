"""M6 - Multi-hop Orchestrator (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, WorkUnit, EvidenceItem
from .base import LLMModule


class ComplexityAnalysis(BaseModel):
    """Pydantic model for query complexity analysis."""
    query_text: str = Field(description="Original query")
    complexity_score: float = Field(ge=0.0, le=1.0, description="Complexity score")
    reasoning_type: str = Field(description="Type of reasoning required")
    hop_count_estimate: int = Field(description="Estimated number of reasoning hops")
    key_concepts: List[str] = Field(description="Key concepts requiring multi-hop reasoning")
    confidence: float = Field(ge=0.0, le=1.0, description="Analysis confidence")


class HopPlan(BaseModel):
    """Pydantic model for multi-hop reasoning plan."""
    hop_sequence: List[str] = Field(description="Sequence of reasoning steps")
    intermediate_queries: List[str] = Field(description="Intermediate queries to resolve")
    dependency_map: Dict[str, List[str]] = Field(description="Dependencies between hops")
    expected_evidence_types: List[str] = Field(description="Expected evidence types per hop")
    confidence: float = Field(ge=0.0, le=1.0, description="Planning confidence")


class HopExecution(BaseModel):
    """Pydantic model for hop execution results."""
    hop_id: str = Field(description="Hop identifier")
    query_executed: str = Field(description="Query executed for this hop")
    evidence_found: int = Field(description="Evidence items found")
    reasoning_result: str = Field(description="Reasoning result from this hop")
    next_hop_needed: bool = Field(description="Whether another hop is needed")
    confidence: float = Field(ge=0.0, le=1.0, description="Execution confidence")


class ReasoningSynthesis(BaseModel):
    """Pydantic model for reasoning synthesis results."""
    total_hops: int = Field(description="Total reasoning hops executed")
    synthesis_result: str = Field(description="Synthesized reasoning result")
    evidence_chain: List[str] = Field(description="Chain of evidence used")
    reasoning_quality: float = Field(ge=0.0, le=1.0, description="Quality of reasoning")
    completeness: float = Field(ge=0.0, le=1.0, description="Completeness of answer")
    confidence: float = Field(ge=0.0, le=1.0, description="Synthesis confidence")


class MultihopOrchestratorLangGraph(LLMModule):
    """M6 - Multi-hop orchestrator with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M6_LG", "mho.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for multi-hop orchestration."""
        workflow = StateGraph(ReactorState)
        
        workflow.add_node("analyze_complexity", self._analyze_complexity_node)
        workflow.add_node("plan_hops", self._plan_hops_node)
        workflow.add_node("execute_hop", self._execute_hop_node)
        workflow.add_node("synthesize_results", self._synthesize_results_node)
        workflow.add_node("validate_reasoning", self._validate_reasoning_node)
        
        workflow.add_edge("analyze_complexity", "plan_hops")
        workflow.add_edge("plan_hops", "execute_hop")
        workflow.add_edge("execute_hop", "synthesize_results")
        workflow.add_edge("synthesize_results", "validate_reasoning")
        workflow.add_edge("validate_reasoning", END)
        
        workflow.set_entry_point("analyze_complexity")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute multi-hop orchestration using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Executing multi-hop orchestration")
        
        if not state.workunits:
            self._log_execution_end(state, "No WorkUnits to process")
            return state
        
        try:
            thread_config = {"configurable": {"thread_id": str(uuid4())}}
            result_state = await self.graph.ainvoke(state, config=thread_config)
            
            if not isinstance(result_state, ReactorState):
                result_state = state
            
            hop_count = getattr(result_state, 'total_hops_executed', 0)
            self._log_execution_end(result_state, f"Multi-hop orchestration: {hop_count} hops executed")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            return state
    
    async def _analyze_complexity_node(self, state: ReactorState) -> ReactorState:
        """Analyze query complexity to determine if multi-hop reasoning is needed."""
        complexity_analyses = []
        
        for workunit in state.workunits:
            analysis = await self._analyze_query_complexity(workunit)
            complexity_analyses.append(analysis)
        
        state.complexity_analyses = complexity_analyses
        return state
    
    async def _plan_hops_node(self, state: ReactorState) -> ReactorState:
        """Plan multi-hop reasoning strategy."""
        complexity_analyses = getattr(state, 'complexity_analyses', [])
        hop_plans = []
        
        for analysis in complexity_analyses:
            if analysis.complexity_score >= 0.6:  # Requires multi-hop
                plan = await self._create_hop_plan(analysis)
                hop_plans.append(plan)
        
        state.hop_plans = hop_plans
        return state
    
    async def _execute_hop_node(self, state: ReactorState) -> ReactorState:
        """Execute individual reasoning hops."""
        hop_plans = getattr(state, 'hop_plans', [])
        hop_executions = []
        total_hops = 0
        
        for plan in hop_plans:
            executions = await self._execute_reasoning_hops(plan, state)
            hop_executions.extend(executions)
            total_hops += len(executions)
        
        state.hop_executions = hop_executions
        state.total_hops_executed = total_hops
        return state
    
    async def _synthesize_results_node(self, state: ReactorState) -> ReactorState:
        """Synthesize results from all reasoning hops."""
        hop_executions = getattr(state, 'hop_executions', [])
        
        if hop_executions:
            synthesis = await self._synthesize_reasoning_results(hop_executions, state)
            state.reasoning_synthesis = synthesis
        
        return state
    
    async def _validate_reasoning_node(self, state: ReactorState) -> ReactorState:
        """Validate the quality of multi-hop reasoning."""
        synthesis = getattr(state, 'reasoning_synthesis', None)
        
        if synthesis:
            validation_score = await self._validate_reasoning_quality(synthesis, state)
            state.reasoning_validation_score = validation_score
        
        return state
    
    async def _analyze_query_complexity(self, workunit: WorkUnit) -> ComplexityAnalysis:
        """Analyze complexity of a query to determine reasoning requirements."""
        prompt = self._get_prompt("m6_complexity_analysis",
            "Analyze this query to determine if multi-hop reasoning is required."
        )
        
        full_prompt = f"""{prompt}

<query>{workunit.text}</query>

Return JSON with:
- query_text: "{workunit.text}"
- complexity_score: 0.0-1.0 (0.6+ requires multi-hop)
- reasoning_type: "simple" | "multi-step" | "comparative" | "causal"
- hop_count_estimate: 1-5
- key_concepts: ["concept1", "concept2"]
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return ComplexityAnalysis(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Complexity analysis failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M6 Complexity Analysis - {e}")
            print(f"   → Using heuristic complexity analysis")
            return self._fallback_complexity_analysis(workunit)
    
    async def _create_hop_plan(self, analysis: ComplexityAnalysis) -> HopPlan:
        """Create a plan for multi-hop reasoning."""
        prompt = self._get_prompt("m6_hop_planning",
            "Create a multi-hop reasoning plan for this complex query."
        )
        
        full_prompt = f"""{prompt}

<complexity_analysis>
Query: {analysis.query_text}
Complexity: {analysis.complexity_score}
Type: {analysis.reasoning_type}
Concepts: {analysis.key_concepts}
</complexity_analysis>

Return JSON with:
- hop_sequence: ["step1", "step2", "step3"]
- intermediate_queries: ["query1", "query2"]
- dependency_map: {{"step1": [], "step2": ["step1"]}}
- expected_evidence_types: ["factual", "analytical"]
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return HopPlan(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Hop planning failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M6 Hop Planning - {e}")
            print(f"   → Using heuristic hop planning")
            return self._fallback_hop_plan(analysis)
    
    async def _execute_reasoning_hops(self, plan: HopPlan, state: ReactorState) -> List[HopExecution]:
        """Execute individual reasoning hops according to plan."""
        executions = []
        
        for i, (hop_step, query) in enumerate(zip(plan.hop_sequence, plan.intermediate_queries)):
            execution = await self._execute_single_hop(hop_step, query, i, state)
            executions.append(execution)
            
            # Check if we need to continue
            if not execution.next_hop_needed:
                break
        
        return executions
    
    async def _execute_single_hop(self, hop_step: str, query: str, 
                                 hop_index: int, state: ReactorState) -> HopExecution:
        """Execute a single reasoning hop."""
        hop_id = f"hop_{hop_index}_{str(uuid4())[:8]}"
        
        # Simulate hop execution by analyzing existing evidence
        relevant_evidence = self._find_relevant_evidence(query, state)
        
        prompt = self._get_prompt("m6_hop_execution",
            "Execute this reasoning step using available evidence."
        )
        
        evidence_text = "\n".join([e.content[:200] + "..." for e in relevant_evidence[:3]])
        
        full_prompt = f"""{prompt}

<hop_step>{hop_step}</hop_step>
<query>{query}</query>
<available_evidence>
{evidence_text}
</available_evidence>

Return JSON with:
- hop_id: "{hop_id}"
- query_executed: "{query}"
- evidence_found: {len(relevant_evidence)}
- reasoning_result: "detailed reasoning result"
- next_hop_needed: true/false
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return HopExecution(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Hop execution failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M6 Hop Execution - {e}")
            print(f"   → Using heuristic hop execution")
            return self._fallback_hop_execution(hop_id, query, len(relevant_evidence))
    
    async def _synthesize_reasoning_results(self, executions: List[HopExecution], 
                                          state: ReactorState) -> ReasoningSynthesis:
        """Synthesize results from all reasoning hops."""
        prompt = self._get_prompt("m6_synthesis",
            "Synthesize the results from multiple reasoning hops into a coherent conclusion."
        )
        
        hop_results = "\n".join([f"Hop {i+1}: {exec.reasoning_result}" 
                                for i, exec in enumerate(executions)])
        
        full_prompt = f"""{prompt}

<hop_results>
{hop_results}
</hop_results>

Return JSON with:
- total_hops: {len(executions)}
- synthesis_result: "comprehensive synthesized result"
- evidence_chain: ["evidence1", "evidence2"]
- reasoning_quality: 0.0-1.0
- completeness: 0.0-1.0
- confidence: 0.0-1.0"""
        
        try:
            response = await self._call_llm(full_prompt)
            import json
            response_data = json.loads(response)
            return ReasoningSynthesis(**response_data)
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Synthesis failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M6 Synthesis - {e}")
            print(f"   → Using heuristic synthesis")
            return self._fallback_synthesis(executions)
    
    async def _validate_reasoning_quality(self, synthesis: ReasoningSynthesis, 
                                        state: ReactorState) -> float:
        """Validate the quality of multi-hop reasoning."""
        # Simple validation based on synthesis metrics
        quality_factors = [
            synthesis.reasoning_quality,
            synthesis.completeness,
            synthesis.confidence
        ]
        
        return sum(quality_factors) / len(quality_factors)
    
    def _find_relevant_evidence(self, query: str, state: ReactorState) -> List[EvidenceItem]:
        """Find evidence relevant to a specific query."""
        if not state.evidences:
            return []
        
        # Simple relevance scoring based on content overlap
        query_words = set(query.lower().split())
        relevant_evidence = []
        
        for evidence in state.evidences:
            content_words = set(evidence.content.lower().split())
            overlap = len(query_words.intersection(content_words))
            
            if overlap > 0:
                relevant_evidence.append(evidence)
        
        # Sort by score and return top results
        return sorted(relevant_evidence, key=lambda e: e.score_raw, reverse=True)[:5]
    
    def _fallback_complexity_analysis(self, workunit: WorkUnit) -> ComplexityAnalysis:
        """Fallback complexity analysis using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M6 Complexity Analysis - Using heuristic analysis for WorkUnit {workunit.id}")
        query_text = workunit.text
        word_count = len(query_text.split())
        
        # Simple heuristics for complexity
        complexity_score = min(1.0, word_count / 20)  # Longer queries = more complex
        
        if any(word in query_text.lower() for word in ["compare", "analyze", "why", "how"]):
            complexity_score += 0.3
        
        complexity_score = min(1.0, complexity_score)
        
        reasoning_type = "multi-step" if complexity_score >= 0.6 else "simple"
        hop_count = int(complexity_score * 3) + 1
        
        # Extract key concepts (simple word extraction)
        key_concepts = [word for word in query_text.split() if len(word) > 4][:3]
        
        return ComplexityAnalysis(
            query_text=query_text,
            complexity_score=complexity_score,
            reasoning_type=reasoning_type,
            hop_count_estimate=hop_count,
            key_concepts=key_concepts,
            confidence=0.7
        )
    
    def _fallback_hop_plan(self, analysis: ComplexityAnalysis) -> HopPlan:
        """Fallback hop planning using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M6 Hop Planning - Using heuristic planning for {analysis.hop_count_estimate} hops")
        hop_count = analysis.hop_count_estimate
        
        hop_sequence = [f"Step {i+1}: Analyze {concept}" 
                       for i, concept in enumerate(analysis.key_concepts[:hop_count])]
        
        intermediate_queries = [f"What is {concept}?" for concept in analysis.key_concepts[:hop_count]]
        
        # Simple dependency map
        dependency_map = {}
        for i, step in enumerate(hop_sequence):
            dependency_map[step] = hop_sequence[:i]
        
        return HopPlan(
            hop_sequence=hop_sequence,
            intermediate_queries=intermediate_queries,
            dependency_map=dependency_map,
            expected_evidence_types=["factual", "analytical"],
            confidence=0.6
        )
    
    def _fallback_hop_execution(self, hop_id: str, query: str, evidence_count: int) -> HopExecution:
        """Fallback hop execution using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M6 Hop Execution - Using heuristic execution for hop {hop_id}")
        return HopExecution(
            hop_id=hop_id,
            query_executed=query,
            evidence_found=evidence_count,
            reasoning_result=f"Analyzed query '{query}' with {evidence_count} evidence items",
            next_hop_needed=evidence_count < 3,  # Continue if insufficient evidence
            confidence=0.6
        )
    
    def _fallback_synthesis(self, executions: List[HopExecution]) -> ReasoningSynthesis:
        """Fallback synthesis using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M6 Synthesis - Using heuristic synthesis for {len(executions)} hop executions")
        total_evidence = sum(exec.evidence_found for exec in executions)
        avg_confidence = sum(exec.confidence for exec in executions) / len(executions)
        
        synthesis_result = f"Synthesized results from {len(executions)} reasoning hops with {total_evidence} total evidence items"
        evidence_chain = [f"Evidence from {exec.hop_id}" for exec in executions]
        
        return ReasoningSynthesis(
            total_hops=len(executions),
            synthesis_result=synthesis_result,
            evidence_chain=evidence_chain,
            reasoning_quality=avg_confidence,
            completeness=min(1.0, total_evidence / 10),  # Assume 10 evidence items = complete
            confidence=avg_confidence
        )


# Module instance
multihop_orchestrator_langgraph = MultihopOrchestratorLangGraph()


# LangGraph node function
async def multihop_orchestrator_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M6 - Multi-hop Orchestrator."""
    return await multihop_orchestrator_langgraph.execute(state)