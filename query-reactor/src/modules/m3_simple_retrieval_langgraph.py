"""M3 - Simple Retrieval (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, EvidenceItem, Provenance, WorkUnit
from ..models.state import PathStats
from ..models.types import SourceType
from .base import LLMModule
import time


class QueryAnalysis(BaseModel):
    """Pydantic model for query analysis results."""
    query_text: str = Field(description="Original query text")
    query_type: str = Field(description="Type of query (factual, technical, historical, etc.)")
    complexity_level: str = Field(description="Query complexity (simple, moderate, complex)")
    key_concepts: List[str] = Field(description="Key concepts extracted from query")
    retrieval_strategy: str = Field(description="Recommended retrieval strategy")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in analysis")


class SourceSelection(BaseModel):
    """Pydantic model for source selection results."""
    selected_sources: List[str] = Field(description="Selected knowledge base sources")
    source_priorities: Dict[str, float] = Field(description="Priority scores for each source")
    selection_reasoning: str = Field(description="Reasoning for source selection")
    expected_results: int = Field(description="Expected number of results")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in selection")


class RetrievalResults(BaseModel):
    """Pydantic model for retrieval results."""
    evidence_items: List[Dict[str, Any]] = Field(description="Retrieved evidence items")
    retrieval_stats: Dict[str, Any] = Field(description="Retrieval statistics")
    source_coverage: Dict[str, int] = Field(description="Results per source")
    total_results: int = Field(description="Total number of results")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall retrieval confidence")


class ValidationResults(BaseModel):
    """Pydantic model for validation results."""
    validated_items: List[str] = Field(description="IDs of validated evidence items")
    quality_scores: Dict[str, float] = Field(description="Quality scores per item")
    validation_issues: List[str] = Field(default_factory=list, description="Validation issues found")
    overall_quality: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in validation")


class SimpleRetrievalLangGraph(LLMModule):
    """M3 - Simple retrieval with LangGraph orchestration and Pydantic validation."""
    
    def __init__(self):
        super().__init__("M3_LG", "sr.model")
        self.path_id = "P1"  # Set path_id for retrieval module functionality
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for simple retrieval."""
        workflow = StateGraph(ReactorState)
        
        # Add processing nodes
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("select_sources", self._select_sources_node)
        workflow.add_node("retrieve_data", self._retrieve_data_node)
        workflow.add_node("validate_results", self._validate_results_node)
        
        # Define workflow edges
        workflow.add_edge("analyze_query", "select_sources")
        workflow.add_edge("select_sources", "retrieve_data")
        workflow.add_edge("retrieve_data", "validate_results")
        workflow.add_edge("validate_results", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_query")
        
        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute simple retrieval using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Executing enhanced simple retrieval")
        
        start_time = time.time()
        
        try:
            # Get routed WorkUnits for P1
            routed_workunits = self._get_routed_workunits(state, "P1")
            
            # If no routing information, process all WorkUnits (fallback)
            if not routed_workunits and state.workunits:
                routed_workunits = state.workunits
            
            if not routed_workunits:
                self._log_execution_end(state, "No WorkUnits routed to P1")
                return state
            
            # Store WorkUnits for processing
            state.current_workunits = routed_workunits
            
            # Execute the LangGraph workflow
            thread_config = {
                "configurable": {
                    "thread_id": str(uuid4())
                }
            }
            
            result_state = await self.graph.ainvoke(state, config=thread_config)
            
            # Ensure we have a proper ReactorState object
            if not isinstance(result_state, ReactorState):
                # If LangGraph returned a dict, convert back to ReactorState
                if isinstance(result_state, dict):
                    # Copy the original state and update with new data
                    result_state = state.model_copy()
                    # The workflow should have updated the state in-place
                else:
                    result_state = state
            
            # Record path statistics
            execution_time = (time.time() - start_time) * 1000
            evidence_count = len(getattr(result_state, 'retrieved_evidence', []))
            
            path_stats = PathStats(
                path_id=self.path_id,
                execution_time_ms=execution_time,
                evidence_count=evidence_count,
                success=True
            )
            result_state.add_path_stats(path_stats)
            
            self._log_execution_end(result_state, f"Retrieved {evidence_count} evidence items")
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            # Record failed path statistics
            execution_time = (time.time() - start_time) * 1000
            path_stats = PathStats(
                path_id=self.path_id,
                execution_time_ms=execution_time,
                evidence_count=0,
                success=False,
                error_message=str(e)
            )
            state.add_path_stats(path_stats)
            return state
    
    async def _analyze_query_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for analyzing queries with LLM."""
        current_workunits = getattr(state, 'current_workunits', [])
        query_analyses = []
        
        for workunit in current_workunits:
            analysis = await self._analyze_workunit_query(workunit)
            query_analyses.append(analysis)
        
        state.query_analyses = query_analyses
        return state
    
    async def _select_sources_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for selecting optimal knowledge sources."""
        query_analyses = getattr(state, 'query_analyses', [])
        source_selections = []
        
        for analysis in query_analyses:
            selection = await self._select_optimal_sources(analysis)
            source_selections.append(selection)
        
        state.source_selections = source_selections
        return state
    
    async def _retrieve_data_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for retrieving data from selected sources."""
        current_workunits = getattr(state, 'current_workunits', [])
        source_selections = getattr(state, 'source_selections', [])
        
        all_evidence = []
        retrieval_results = []
        
        for workunit, selection in zip(current_workunits, source_selections):
            results = await self._retrieve_from_sources(workunit, selection, state)
            retrieval_results.append(results)
            
            # Convert results to EvidenceItem objects and add to state
            for evidence_data in results.evidence_items:
                evidence_item = self._create_evidence_item_from_data(evidence_data, workunit, state)
                all_evidence.append(evidence_item)
                state.add_evidence(evidence_item)
        
        state.retrieval_results = retrieval_results
        state.retrieved_evidence = all_evidence
        return state
    
    async def _validate_results_node(self, state: ReactorState) -> ReactorState:
        """LangGraph node for validating retrieved results."""
        retrieved_evidence = getattr(state, 'retrieved_evidence', [])
        
        if not retrieved_evidence:
            return state
        
        validation_results = await self._validate_evidence_quality(retrieved_evidence)
        state.validation_results = validation_results
        
        return state
    
    async def _analyze_workunit_query(self, workunit: WorkUnit) -> QueryAnalysis:
        """Analyze WorkUnit query with LLM for optimal retrieval strategy."""
        prompt = self._get_prompt("m3_query_analysis",
            "Analyze this query to determine the optimal retrieval strategy for internal knowledge bases."
        )
        
        full_prompt = f"""{prompt}

<query>
{workunit.text}
</query>

Return a JSON object with:
- query_text: The original query text
- query_type: Type of query (factual, technical, historical, comparative, etc.)
- complexity_level: Complexity (simple, moderate, complex)
- key_concepts: List of key concepts to search for
- retrieval_strategy: Recommended strategy (broad_search, focused_search, multi_source, etc.)
- confidence: Confidence score (0.0-1.0)"""
        
        try:
            response = await self._call_llm(full_prompt)
            
            # Parse and validate response with Pydantic
            import json
            response_data = json.loads(response)
            return QueryAnalysis(**response_data)
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Query analysis failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M3 Query Analysis - {e}")
            print(f"   → Using heuristic query analysis")
            # Fallback analysis
            return self._fallback_query_analysis(workunit)
    
    async def _select_optimal_sources(self, analysis: QueryAnalysis) -> SourceSelection:
        """Select optimal knowledge sources based on query analysis."""
        prompt = self._get_prompt("m3_source_selection",
            "Select the best knowledge base sources for this query based on the analysis."
        )
        
        full_prompt = f"""{prompt}

<query_analysis>
Query: {analysis.query_text}
Type: {analysis.query_type}
Complexity: {analysis.complexity_level}
Key Concepts: {', '.join(analysis.key_concepts)}
Strategy: {analysis.retrieval_strategy}
</query_analysis>

<available_sources>
- general_kb: General knowledge base (broad topics, high coverage)
- technical_kb: Technical documentation (programming, systems, APIs)
- historical_kb: Historical records and archived information
- factual_kb: Factual data and statistics
- reference_kb: Reference materials and definitions
</available_sources>

Return a JSON object with:
- selected_sources: List of source IDs to query
- source_priorities: Priority scores for each selected source (0.0-1.0)
- selection_reasoning: Reasoning for source selection
- expected_results: Expected number of results (1-10)
- confidence: Confidence in selection (0.0-1.0)"""
        
        try:
            response = await self._call_llm(full_prompt)
            
            # Parse and validate response with Pydantic
            import json
            response_data = json.loads(response)
            return SourceSelection(**response_data)
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Source selection failed, using fallback: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M3 Source Selection - {e}")
            print(f"   → Using heuristic source selection")
            # Fallback source selection
            return self._fallback_source_selection(analysis)
    
    async def _retrieve_from_sources(self, workunit: WorkUnit, selection: SourceSelection, 
                                   state: ReactorState) -> RetrievalResults:
        """Retrieve data from selected sources."""
        # Get configuration
        max_results_per_source = self._get_config("sr.max_results_per_source", 3)
        
        evidence_items = []
        source_coverage = {}
        
        # Retrieve from each selected source
        for source_id in selection.selected_sources:
            priority = selection.source_priorities.get(source_id, 0.5)
            max_results = max(1, int(max_results_per_source * priority))
            
            source_results = await self._retrieve_from_single_source(
                workunit, source_id, max_results
            )
            
            evidence_items.extend(source_results)
            source_coverage[source_id] = len(source_results)
        
        # Calculate overall confidence based on results and expectations
        total_results = len(evidence_items)
        expected_results = selection.expected_results
        
        if expected_results > 0:
            coverage_ratio = min(1.0, total_results / expected_results)
            confidence = (coverage_ratio * 0.7) + (selection.confidence * 0.3)
        else:
            confidence = 0.5 if total_results > 0 else 0.1
        
        return RetrievalResults(
            evidence_items=evidence_items,
            retrieval_stats={
                "sources_queried": len(selection.selected_sources),
                "total_results": total_results,
                "avg_results_per_source": total_results / len(selection.selected_sources) if selection.selected_sources else 0
            },
            source_coverage=source_coverage,
            total_results=total_results,
            confidence=confidence
        )
    
    async def _retrieve_from_single_source(self, workunit: WorkUnit, source_id: str, 
                                         max_results: int) -> List[Dict[str, Any]]:
        """Retrieve data from a single knowledge source."""
        # V1.0: Generate realistic dummy data based on source type and query
        results = []
        
        source_templates = self._get_source_templates(source_id)
        query_context = self._extract_query_context(workunit.text)
        
        for i in range(max_results):
            template = source_templates[i % len(source_templates)]
            
            content = template["content_template"].format(
                query=workunit.text,
                topic=query_context["topic"],
                context=query_context["context"],
                detail_level=query_context["detail_level"]
            )
            
            # Add variation to content
            if i > 0:
                content += f" {template.get('variation_suffix', '')}"
            
            result_data = {
                "id": str(uuid4()),
                "source_id": source_id,
                "title": template["title_template"].format(
                    topic=query_context["topic"],
                    index=i + 1
                ),
                "content": content,
                "score": 0.9 - (i * 0.1),  # Decreasing scores
                "metadata": {
                    "source_type": template["source_type"],
                    "confidence": 0.8 - (i * 0.05),
                    "relevance": 0.9 - (i * 0.1)
                }
            }
            
            results.append(result_data)
        
        return results
    
    async def _validate_evidence_quality(self, evidence_items: List[EvidenceItem]) -> ValidationResults:
        """Validate the quality of retrieved evidence."""
        if not evidence_items:
            return ValidationResults(
                validated_items=[],
                quality_scores={},
                validation_issues=["No evidence items to validate"],
                overall_quality=0.0,
                confidence=1.0
            )
        
        validated_items = []
        quality_scores = {}
        validation_issues = []
        
        for evidence in evidence_items:
            # Basic quality checks
            quality_score = 0.0
            
            # Content length check
            if len(evidence.content) >= 50:
                quality_score += 0.3
            elif len(evidence.content) >= 20:
                quality_score += 0.2
            else:
                validation_issues.append(f"Evidence {evidence.id}: Content too short")
            
            # Score check
            if evidence.score_raw >= 0.7:
                quality_score += 0.3
            elif evidence.score_raw >= 0.5:
                quality_score += 0.2
            else:
                validation_issues.append(f"Evidence {evidence.id}: Low relevance score")
            
            # Provenance check
            if evidence.provenance and evidence.provenance.source_id:
                quality_score += 0.2
            else:
                validation_issues.append(f"Evidence {evidence.id}: Missing provenance")
            
            # Title check
            if hasattr(evidence, 'title') and evidence.title:
                quality_score += 0.2
            
            quality_scores[str(evidence.id)] = quality_score
            
            if quality_score >= 0.5:  # Minimum quality threshold
                validated_items.append(str(evidence.id))
        
        # Calculate overall quality
        if quality_scores:
            overall_quality = sum(quality_scores.values()) / len(quality_scores)
        else:
            overall_quality = 0.0
        
        return ValidationResults(
            validated_items=validated_items,
            quality_scores=quality_scores,
            validation_issues=validation_issues,
            overall_quality=overall_quality,
            confidence=0.9 if len(validation_issues) == 0 else 0.7
        )
    
    def _fallback_query_analysis(self, workunit: WorkUnit) -> QueryAnalysis:
        """Fallback query analysis using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M3 Query Analysis - Using heuristic analysis for WorkUnit {workunit.id}")
        query_text = workunit.text.lower()
        
        # Determine query type
        if any(word in query_text for word in ["what is", "define", "explain"]):
            query_type = "factual"
        elif any(word in query_text for word in ["how to", "tutorial", "guide"]):
            query_type = "technical"
        elif any(word in query_text for word in ["history", "when", "timeline"]):
            query_type = "historical"
        elif any(word in query_text for word in ["compare", "vs", "difference"]):
            query_type = "comparative"
        else:
            query_type = "general"
        
        # Determine complexity
        word_count = len(workunit.text.split())
        if word_count > 15:
            complexity_level = "complex"
        elif word_count > 8:
            complexity_level = "moderate"
        else:
            complexity_level = "simple"
        
        # Extract key concepts (simple word extraction)
        key_concepts = [word for word in workunit.text.split() 
                       if len(word) > 3 and word.lower() not in 
                       ["what", "how", "when", "where", "why", "the", "and", "or"]][:5]
        
        return QueryAnalysis(
            query_text=workunit.text,
            query_type=query_type,
            complexity_level=complexity_level,
            key_concepts=key_concepts,
            retrieval_strategy="broad_search" if complexity_level == "complex" else "focused_search",
            confidence=0.7
        )
    
    def _fallback_source_selection(self, analysis: QueryAnalysis) -> SourceSelection:
        """Fallback source selection using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M3 Source Selection - Using heuristic source selection")
        selected_sources = ["general_kb"]  # Always include general KB
        source_priorities = {"general_kb": 0.8}
        
        # Add sources based on query type
        if analysis.query_type == "technical":
            selected_sources.append("technical_kb")
            source_priorities["technical_kb"] = 0.9
        elif analysis.query_type == "historical":
            selected_sources.append("historical_kb")
            source_priorities["historical_kb"] = 0.8
        elif analysis.query_type == "factual":
            selected_sources.append("factual_kb")
            source_priorities["factual_kb"] = 0.7
        
        return SourceSelection(
            selected_sources=selected_sources,
            source_priorities=source_priorities,
            selection_reasoning=f"Heuristic selection based on {analysis.query_type} query type",
            expected_results=3 if analysis.complexity_level == "simple" else 5,
            confidence=0.6
        )
    
    def _get_source_templates(self, source_id: str) -> List[Dict[str, str]]:
        """Get content templates for different sources."""
        templates = {
            "general_kb": [
                {
                    "title_template": "General Knowledge: {topic} - Entry {index}",
                    "content_template": "According to our general knowledge base, {query} relates to {topic}. {context} This information provides {detail_level} coverage of the topic.",
                    "source_type": "general",
                    "variation_suffix": "Additional context is available in related entries."
                },
                {
                    "title_template": "Knowledge Base: {topic} Overview {index}",
                    "content_template": "Our knowledge repository indicates that {query} involves {topic}. {context} The information is maintained with regular updates.",
                    "source_type": "general",
                    "variation_suffix": "Cross-references provide broader perspective."
                }
            ],
            "technical_kb": [
                {
                    "title_template": "Technical Documentation: {topic} - Section {index}",
                    "content_template": "Technical documentation shows that {query} involves {topic}. {context} Implementation details and {detail_level} specifications are documented.",
                    "source_type": "technical",
                    "variation_suffix": "See related API documentation for implementation details."
                }
            ],
            "historical_kb": [
                {
                    "title_template": "Historical Records: {topic} - Record {index}",
                    "content_template": "Historical records indicate that {query} has been relevant in the context of {topic}. {context} Archives contain {detail_level} information.",
                    "source_type": "historical",
                    "variation_suffix": "Timeline data provides chronological context."
                }
            ],
            "factual_kb": [
                {
                    "title_template": "Factual Data: {topic} - Fact {index}",
                    "content_template": "Factual data shows that {query} relates to {topic}. {context} Verified information provides {detail_level} accuracy.",
                    "source_type": "factual",
                    "variation_suffix": "Statistical data supports these findings."
                }
            ],
            "reference_kb": [
                {
                    "title_template": "Reference Material: {topic} - Reference {index}",
                    "content_template": "Reference materials define {query} in the context of {topic}. {context} Authoritative sources provide {detail_level} definitions.",
                    "source_type": "reference",
                    "variation_suffix": "See glossary for related terms."
                }
            ]
        }
        
        return templates.get(source_id, templates["general_kb"])
    
    def _extract_query_context(self, query_text: str) -> Dict[str, str]:
        """Extract context information from query for content generation."""
        query_lower = query_text.lower()
        
        # Extract topic
        if "python" in query_lower:
            topic = "Python programming"
            context = "a versatile programming language"
            detail_level = "comprehensive technical"
        elif "javascript" in query_lower:
            topic = "JavaScript development"
            context = "web development and programming"
            detail_level = "detailed technical"
        elif "machine learning" in query_lower or "ai" in query_lower:
            topic = "artificial intelligence and machine learning"
            context = "advanced computational techniques"
            detail_level = "in-depth technical"
        elif "climate" in query_lower:
            topic = "climate science"
            context = "environmental and atmospheric studies"
            detail_level = "scientific"
        else:
            topic = "general knowledge topics"
            context = "various domains of information"
            detail_level = "general"
        
        return {
            "topic": topic,
            "context": context,
            "detail_level": detail_level
        }
    
    def _create_evidence_item_from_data(self, evidence_data: Dict[str, Any], 
                                      workunit: WorkUnit, state: ReactorState) -> EvidenceItem:
        """Create EvidenceItem from retrieved data."""
        # Create provenance
        provenance = Provenance(
            source_type=SourceType.db,
            source_id=evidence_data["source_id"],
            doc_id=evidence_data["id"],
            chunk_id=f"chunk_{evidence_data['id'][:8]}",
            retrieval_path=self.path_id,
            router_decision_id=self._get_router_decision_id(state, workunit.id)
        )
        
        # Create evidence item
        evidence = EvidenceItem(
            workunit_id=workunit.id,
            user_id=workunit.user_id,
            conversation_id=workunit.conversation_id,
            content=evidence_data["content"],
            title=evidence_data.get("title"),
            score_raw=evidence_data["score"],
            provenance=provenance
        )
        
        return evidence
    
    def _get_routed_workunits(self, state: ReactorState, path_id: str) -> List[WorkUnit]:
        """Get WorkUnits routed to this path."""
        routed_workunits = []
        
        # 如果狀態中有 current_path_id，表示這是路徑協調器分配的狀態
        if hasattr(state, 'current_path_id') and state.current_path_id == path_id:
            # 直接使用狀態中的 WorkUnits（已經過濾）
            return state.workunits
        
        # 否則，從路由計劃中查找
        if hasattr(state, 'route_plans') and state.route_plans is not None:
            for route_plan in state.route_plans:
                if path_id in route_plan.selected_paths:
                    workunit = state.get_workunit(route_plan.workunit_id)
                    if workunit:
                        routed_workunits.append(workunit)
        
        return routed_workunits
    
    def _get_router_decision_id(self, state: ReactorState, workunit_id) -> str:
        """Get router decision ID for a WorkUnit."""
        if hasattr(state, 'route_plans') and state.route_plans is not None:
            for route_plan in state.route_plans:
                if route_plan.workunit_id == workunit_id:
                    return route_plan.router_decision_id
        
        return str(uuid4())  # Fallback


# Module instance
simple_retrieval_langgraph = SimpleRetrievalLangGraph()


# LangGraph node function for integration
async def simple_retrieval_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M3 - Simple Retrieval (LangGraph implementation)."""
    return await simple_retrieval_langgraph.execute(state)