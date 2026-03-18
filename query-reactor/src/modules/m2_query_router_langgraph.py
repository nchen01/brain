"""M2 - Query Router (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Set, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from ..models import ReactorState, WorkUnit, RoutePlan
from ..models.state import RouterStats
from .base import LLMModule
from ..config.model_manager import model_manager
import time


class ModernBaseModel(BaseModel):
    """Modern Pydantic v2 compatible base model with utility methods."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModernBaseModel':
        """Create model from dictionary."""
        return cls.model_validate(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModernBaseModel':
        """Create model from JSON string."""
        return cls.model_validate_json(json_str)


class PathAnalysis(ModernBaseModel):
    """Pydantic model for individual path analysis."""
    path_id: str = Field(description="Path identifier (P1, P2, P3)")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance score for this path")
    reasoning: str = Field(description="Reasoning for path selection")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in path selection")


class RoutingDecision(ModernBaseModel):
    """Pydantic model for routing decision output."""
    workunit_id: str = Field(description="WorkUnit ID being routed")
    selected_paths: List[str] = Field(description="Selected retrieval paths")
    path_analyses: List[PathAnalysis] = Field(description="Analysis for each considered path")
    overall_reasoning: str = Field(description="Overall routing reasoning")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in routing decision")


class StructuredLLMFactory:
    """Factory for creating LLMs with structured output for M2 routing."""
    
    @staticmethod
    def create_routing_llm() -> ChatOpenAI:
        """Create LLM for query routing with structured output."""
        model_name = model_manager.get_model_for_task('query_routing', 'qr.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'query_routing')
        
        raw_llm = ChatOpenAI(
            model=api_params.get("model", model_name),
            temperature=api_params.get("temperature", 0.3)
        )
        return raw_llm.with_structured_output(RoutingDecision, method="function_calling")


class QueryRouterLangGraph(LLMModule):
    """M2 - Query routing with LangGraph orchestration and Pydantic validation."""
    
    def __init__(self):
        super().__init__("M2_LG", "qr.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for query routing."""
        workflow = StateGraph(ReactorState)
        
        # Add processing nodes
        workflow.add_node("analyze_workunits", self._analyze_workunits_node)
        workflow.add_node("route_workunits", self._route_workunits_node)
        workflow.add_node("optimize_routing", self._optimize_routing_node)
        workflow.add_node("finalize_routes", self._finalize_routes_node)
        
        # Define workflow edges
        workflow.add_edge("analyze_workunits", "route_workunits")
        workflow.add_edge("route_workunits", "optimize_routing")
        workflow.add_edge("optimize_routing", "finalize_routes")
        workflow.add_edge("finalize_routes", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_workunits")
        
        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute query routing using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, f"Routing {len(state.workunits)} work units")
        
        start_time = time.time()
        
        try:
            # Initialize router statistics
            router_stats = RouterStats()
            state.router_stats = router_stats
            state.routing_start_time = start_time
            
            # Execute the LangGraph workflow
            thread_config = {
                "configurable": {
                    "thread_id": str(uuid4())
                }
            }
            
            result_state = await self.graph.ainvoke(state, config=thread_config)
            
            # Finalize statistics
            if hasattr(result_state, 'router_stats') and result_state.router_stats:
                result_state.router_stats.routing_time_ms = (time.time() - start_time) * 1000
            
            unique_paths = self._get_unique_paths(result_state.route_plans)
            self._log_execution_end(result_state, f"Routed to paths: {unique_paths}")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M2 Execute - {e}")
            print(f"   → Routing all WorkUnits to simple retrieval")
            # Fallback: route all WorkUnits to simple retrieval
            fallback_plans = []
            for workunit in state.workunits:
                fallback_plan = RoutePlan(
                    workunit_id=workunit.id,
                    selected_paths=["P1"],
                    router_decision_id=uuid4(),
                    reasoning="Fallback routing due to error"
                )
                fallback_plans.append(fallback_plan)
            
            state.route_plans = fallback_plans
            return state
    
    async def _analyze_workunits_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for analyzing WorkUnits before routing."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in analyze node")
            return state
        
        # Store workunit analysis for routing decisions
        workunit_analyses = {}
        
        for workunit in state.workunits:
            analysis = await self._analyze_workunit_characteristics(workunit)
            workunit_analyses[str(workunit.id)] = analysis
        
        state.workunit_analyses = workunit_analyses
        return state
    
    async def _route_workunits_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for routing WorkUnits with LLM-based decisions."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in route node")
            return state
        
        max_parallel_paths = self._get_config("router.max_parallel_paths", 3)
        routing_decisions = []
        
        for workunit in state.workunits:
            decision = await self._make_routing_decision(workunit, max_parallel_paths, state)
            routing_decisions.append(decision)
        
        state.routing_decisions = routing_decisions
        return state
    
    async def _optimize_routing_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for optimizing routing decisions."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in optimize node")
            return state
        
        # Analyze routing decisions for optimization opportunities
        routing_decisions = getattr(state, 'routing_decisions', [])
        
        # Check for redundant paths across WorkUnits
        path_usage = {}
        for decision in routing_decisions:
            for path in decision.selected_paths:
                path_usage[path] = path_usage.get(path, 0) + 1
        
        # Optimize based on resource constraints
        optimized_decisions = await self._optimize_path_allocation(routing_decisions, path_usage, state)
        state.routing_decisions = optimized_decisions
        
        return state
    
    async def _finalize_routes_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for finalizing route plans."""
        # Ensure we have a proper ReactorState object
        if isinstance(state, dict):
            self.logger.warning(f"[{self.module_code}] Received dict instead of ReactorState in finalize node")
            return state
        
        routing_decisions = getattr(state, 'routing_decisions', [])
        route_plans = []
        
        # Convert routing decisions to route plans
        for decision in routing_decisions:
            # Find the corresponding WorkUnit ID
            workunit_id = decision.workunit_id
            if isinstance(workunit_id, str):
                # Try to find the actual WorkUnit with this ID
                try:
                    from uuid import UUID
                    workunit_id = UUID(workunit_id) if len(workunit_id) == 36 else uuid4()
                except:
                    workunit_id = uuid4()
            
            route_plan = RoutePlan(
                workunit_id=workunit_id,
                selected_paths=decision.selected_paths,
                router_decision_id=uuid4(),
                reasoning=decision.overall_reasoning
            )
            route_plans.append(route_plan)
        
        state.route_plans = route_plans
        
        # Update router statistics
        if hasattr(state, 'router_stats') and state.router_stats:
            router_stats = state.router_stats
            router_stats.total_workunits = len(routing_decisions)
            
            for decision in routing_decisions:
                for path in decision.selected_paths:
                    router_stats.path_selections[path] = router_stats.path_selections.get(path, 0) + 1
                
                if len(decision.selected_paths) > 1:
                    router_stats.parallel_routes += 1
        
        return state
    
    async def _analyze_workunit_characteristics(self, workunit: WorkUnit) -> Dict[str, any]:
        """Analyze WorkUnit characteristics for routing decisions."""
        query_text = workunit.text.lower()
        
        characteristics = {
            'complexity': self._assess_query_complexity(query_text),
            'temporal_sensitivity': self._assess_temporal_sensitivity(query_text),
            'domain_specificity': self._assess_domain_specificity(query_text),
            'reasoning_requirements': self._assess_reasoning_requirements(query_text),
            'information_freshness': self._assess_information_freshness(query_text)
        }
        
        return characteristics
    
    async def _make_routing_decision(self, workunit: WorkUnit, max_paths: int, state: ReactorState) -> RoutingDecision:
        """Make intelligent routing decision using LLM with structured output."""
        try:
            # Create structured LLM (like M1)
            routing_llm = StructuredLLMFactory.create_routing_llm()
            
            # Get workunit analysis (safely)
            workunit_analysis = getattr(state, 'workunit_analyses', {}).get(str(workunit.id), {})
            
            # Get prompt from configuration
            prompt = self._get_prompt("m2_routing",
                "Analyze this query and determine the best retrieval paths. "
                "Consider query complexity, information freshness needs, and reasoning requirements."
            )
            
            full_prompt = f"""{prompt}

<query>
{workunit.text}
</query>

<query_characteristics>
Complexity: {workunit_analysis.get('complexity', 'medium')}
Temporal Sensitivity: {workunit_analysis.get('temporal_sensitivity', 'low')}
Domain Specificity: {workunit_analysis.get('domain_specificity', 'general')}
Reasoning Requirements: {workunit_analysis.get('reasoning_requirements', 'basic')}
Information Freshness: {workunit_analysis.get('information_freshness', 'not_critical')}
</query_characteristics>

<workunit_id>
{workunit.id}
</workunit_id>"""
            
            # Log the input prompt for review
            self.logger.info(f"[{self.module_code}] ROUTING INPUT:\n{full_prompt}")
            
            # Call structured LLM - returns validated Pydantic object directly
            result: RoutingDecision = await routing_llm.ainvoke(full_prompt)
            
            # Log the output for review
            self.logger.info(f"[{self.module_code}] ROUTING OUTPUT: {result.to_dict()}")
            
            # Ensure we don't exceed max_paths
            if len(result.selected_paths) > max_paths:
                # Sort by relevance and take top paths
                path_scores = {pa.path_id: pa.relevance_score for pa in result.path_analyses}
                sorted_paths = sorted(result.selected_paths, 
                                    key=lambda p: path_scores.get(p, 0.0), reverse=True)
                result.selected_paths = sorted_paths[:max_paths]
            
            return result
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Structured LLM routing failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M2 Routing Decision - {e}")
            print(f"   → Using heuristic routing for WorkUnit {workunit.id}")
            # Fallback to heuristic routing
            return await self._fallback_routing_decision(workunit, max_paths)
    
    async def _fallback_routing_decision(self, workunit: WorkUnit, max_paths: int) -> RoutingDecision:
        """Fallback routing decision using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M2 Routing Decision - Using heuristic routing for WorkUnit {workunit.id}")
        query_text = workunit.text.lower()
        selected_paths = set()
        path_analyses = []
        
        # P1 (Simple Retrieval) analysis
        p1_score = 0.8 if any(indicator in query_text for indicator in 
                             ["what is", "who is", "definition", "explain"]) else 0.4
        path_analyses.append(PathAnalysis.from_dict({
            "path_id": "P1",
            "relevance_score": p1_score,
            "reasoning": "Internal knowledge base suitable for factual queries",
            "confidence": 0.8
        }))
        if p1_score > 0.5:
            selected_paths.add("P1")
        
        # P2 (Internet Retrieval) analysis
        p2_score = 0.9 if any(indicator in query_text for indicator in 
                             ["latest", "current", "recent", "2024", "2025"]) else 0.3
        path_analyses.append(PathAnalysis.from_dict({
            "path_id": "P2",
            "relevance_score": p2_score,
            "reasoning": "Internet search needed for current information",
            "confidence": 0.7
        }))
        if p2_score > 0.5:
            selected_paths.add("P2")
        
        # P3 (Multi-hop) analysis
        p3_score = 0.8 if any(indicator in query_text for indicator in 
                             ["why", "how does", "compare", "analyze"]) else 0.2
        path_analyses.append(PathAnalysis.from_dict({
            "path_id": "P3",
            "relevance_score": p3_score,
            "reasoning": "Multi-hop reasoning needed for complex analysis",
            "confidence": 0.6
        }))
        if p3_score > 0.5:
            selected_paths.add("P3")
        
        # Ensure at least one path
        if not selected_paths:
            selected_paths.add("P1")
        
        # Limit to max_paths
        selected_list = list(selected_paths)[:max_paths]
        
        return RoutingDecision.from_dict({
            "workunit_id": str(workunit.id),
            "selected_paths": selected_list,
            "path_analyses": [pa.to_dict() for pa in path_analyses],
            "overall_reasoning": f"Heuristic routing based on query patterns in: {workunit.text[:50]}...",
            "confidence": 0.7
        })
    
    async def _optimize_path_allocation(self, routing_decisions: List[RoutingDecision], 
                                      path_usage: Dict[str, int], state: ReactorState) -> List[RoutingDecision]:
        """Optimize path allocation based on resource constraints."""
        # For now, return decisions as-is
        # In future versions, could implement load balancing, cost optimization, etc.
        return routing_decisions
    
    def _assess_query_complexity(self, query_text: str) -> str:
        """Assess query complexity level."""
        word_count = len(query_text.split())
        
        if word_count > 15:
            return "high"
        elif word_count > 8:
            return "medium"
        else:
            return "low"
    
    def _assess_temporal_sensitivity(self, query_text: str) -> str:
        """Assess temporal sensitivity of the query."""
        temporal_indicators = ["latest", "current", "recent", "today", "now", "2024", "2025"]
        
        if any(indicator in query_text for indicator in temporal_indicators):
            return "high"
        elif any(indicator in query_text for indicator in ["this year", "this month"]):
            return "medium"
        else:
            return "low"
    
    def _assess_domain_specificity(self, query_text: str) -> str:
        """Assess domain specificity of the query."""
        technical_terms = ["api", "algorithm", "database", "programming", "software"]
        
        if any(term in query_text for term in technical_terms):
            return "technical"
        elif any(term in query_text for term in ["business", "market", "finance"]):
            return "business"
        else:
            return "general"
    
    def _assess_reasoning_requirements(self, query_text: str) -> str:
        """Assess reasoning requirements of the query."""
        query_text = query_text.lower()  # Ensure lowercase for consistent matching
        complex_reasoning = ["why", "how does", "what causes", "analyze", "compare"]
        
        if any(indicator in query_text for indicator in complex_reasoning):
            return "complex"
        elif any(indicator in query_text for indicator in ["explain", "describe"]):
            return "moderate"
        else:
            return "basic"
    
    def _assess_information_freshness(self, query_text: str) -> str:
        """Assess information freshness requirements."""
        freshness_indicators = ["latest", "current", "recent", "breaking", "news"]
        
        if any(indicator in query_text for indicator in freshness_indicators):
            return "critical"
        elif any(indicator in query_text for indicator in ["this year", "2024", "2025"]):
            return "important"
        else:
            return "not_critical"
    
    def _get_unique_paths(self, route_plans: List[RoutePlan]) -> Set[str]:
        """Get unique paths from all route plans."""
        unique_paths = set()
        for plan in route_plans:
            unique_paths.update(plan.selected_paths)
        return unique_paths


# Module instance
query_router_langgraph = QueryRouterLangGraph()


# LangGraph node function for integration
async def query_router_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M2 - Query Router (LangGraph implementation)."""
    return await query_router_langgraph.execute(state)