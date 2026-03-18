"""M8 - ReRanker (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from ..models import ReactorState, EvidenceItem, WorkUnit
from .base import LLMModule
from ..config.model_manager import model_manager
import math


class EvidenceScoring(BaseModel):
    """Pydantic model for multi-dimensional evidence scoring."""
    evidence_id: str = Field(description="Evidence item ID")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Query relevance score")
    quality_score: float = Field(ge=0.0, le=1.0, description="Content quality score")
    credibility_score: float = Field(ge=0.0, le=1.0, description="Source credibility score")
    recency_score: float = Field(ge=0.0, le=1.0, description="Information recency score")
    completeness_score: float = Field(ge=0.0, le=1.0, description="Information completeness score")
    composite_score: float = Field(ge=0.0, le=1.0, description="Final composite score")
    confidence: float = Field(ge=0.0, le=1.0, description="Scoring confidence")


class RankingCalculation(BaseModel):
    """Pydantic model for ranking algorithm results."""
    algorithm_used: str = Field(description="Ranking algorithm applied")
    total_items: int = Field(description="Total items ranked")
    ranking_factors: List[str] = Field(description="Factors considered in ranking")
    score_distribution: Dict[str, int] = Field(description="Distribution of scores")
    ranking_quality: float = Field(ge=0.0, le=1.0, description="Quality of ranking")
    confidence: float = Field(ge=0.0, le=1.0, description="Ranking confidence")


class RankingValidation(BaseModel):
    """Pydantic model for ranking quality assessment."""
    validation_method: str = Field(description="Method used for validation")
    ranking_consistency: float = Field(ge=0.0, le=1.0, description="Consistency of ranking")
    top_items_quality: float = Field(ge=0.0, le=1.0, description="Quality of top-ranked items")
    diversity_score: float = Field(ge=0.0, le=1.0, description="Diversity in top results")
    validation_issues: List[str] = Field(description="Identified ranking issues")
    confidence: float = Field(ge=0.0, le=1.0, description="Validation confidence")


class AdaptiveStrategy(BaseModel):
    """Pydantic model for adaptive ranking strategy."""
    strategy_name: str = Field(description="Name of adaptive strategy")
    query_characteristics: Dict[str, float] = Field(description="Query analysis results")
    weight_adjustments: Dict[str, float] = Field(description="Factor weight adjustments")
    strategy_rationale: str = Field(description="Reasoning for strategy selection")
    expected_improvement: float = Field(ge=0.0, le=1.0, description="Expected ranking improvement")
    confidence: float = Field(ge=0.0, le=1.0, description="Strategy confidence")


class ModernBaseModel(BaseModel):
    """Base model with Pydantic v2 compatibility methods."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Modern replacement for deprecated dict() method."""
        return self.model_dump()
    
    @classmethod
    def from_json(cls, json_str: str):
        """Modern replacement for deprecated parse_raw() method."""
        return cls.model_validate_json(json_str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Modern replacement for deprecated parse_obj() method."""
        return cls.model_validate(data)


class StructuredLLMFactory:
    """Factory for creating structured output LLMs for M8."""
    
    @staticmethod
    def create_strategy_llm() -> ChatOpenAI:
        """Create LLM for strategy selection with structured output."""
        model_name = model_manager.get_model_for_task('ranking_strategy', 'rr.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'ranking_strategy')
        
        raw_llm = ChatOpenAI(
            model=api_params.get("model", model_name),
            temperature=api_params.get("temperature", 0.3)
        )
        return raw_llm.with_structured_output(AdaptiveStrategy, method="function_calling")
    
    @staticmethod
    def create_scoring_llm() -> ChatOpenAI:
        """Create LLM for evidence scoring with structured output."""
        model_name = model_manager.get_model_for_task('evidence_scoring', 'rr.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'evidence_scoring')
        
        raw_llm = ChatOpenAI(
            model=api_params.get("model", model_name),
            temperature=api_params.get("temperature", 0.2)
        )
        return raw_llm.with_structured_output(EvidenceScoring, method="function_calling")
    
    @staticmethod
    def create_validation_llm() -> ChatOpenAI:
        """Create LLM for ranking validation with structured output."""
        model_name = model_manager.get_model_for_task('ranking_validation', 'rr.model')
        api_params = model_manager.optimize_params_for_task(model_name, 'ranking_validation')
        
        raw_llm = ChatOpenAI(
            model=api_params.get("model", model_name),
            temperature=api_params.get("temperature", 0.1)
        )
        return raw_llm.with_structured_output(RankingValidation, method="function_calling")


class ReRankerLangGraph(LLMModule):
    """M8 - ReRanker with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M8_LG", "rr.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for evidence reranking."""
        workflow = StateGraph(ReactorState)
        
        workflow.add_node("analyze_evidence", self._analyze_evidence_node)
        workflow.add_node("calculate_scores", self._calculate_scores_node)
        workflow.add_node("apply_ranking", self._apply_ranking_node)
        workflow.add_node("validate_ranking", self._validate_ranking_node)
        
        workflow.add_edge("analyze_evidence", "calculate_scores")
        workflow.add_edge("calculate_scores", "apply_ranking")
        workflow.add_edge("apply_ranking", "validate_ranking")
        workflow.add_edge("validate_ranking", END)
        
        workflow.set_entry_point("analyze_evidence")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute evidence reranking using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Reranking evidence")
        
        if not state.evidences:
            self._log_execution_end(state, "No evidence to rerank")
            return state
        
        try:
            thread_config = {"configurable": {"thread_id": str(uuid4())}}
            result_state = await self.graph.ainvoke(state, config=thread_config)
            
            if not isinstance(result_state, ReactorState):
                result_state = state
            
            # Sort evidence by final scores
            if hasattr(result_state, 'evidence_scores'):
                score_map = {score.evidence_id: score.composite_score 
                           for score in result_state.evidence_scores}
                result_state.evidences.sort(
                    key=lambda e: score_map.get(str(e.id), e.score_raw), 
                    reverse=True
                )
            
            top_score = result_state.evidences[0].score_raw if result_state.evidences else 0.0
            self._log_execution_end(result_state, f"Reranked {len(result_state.evidences)} items, top score: {top_score:.3f}")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            return state
    
    async def _analyze_evidence_node(self, state: ReactorState) -> ReactorState:
        """Analyze evidence characteristics for ranking strategy."""
        strategy = await self._determine_adaptive_strategy(state)
        state.adaptive_strategy = strategy
        return state
    
    async def _calculate_scores_node(self, state: ReactorState) -> ReactorState:
        """Calculate multi-dimensional scores for all evidence."""
        evidence_scores = []
        strategy = getattr(state, 'adaptive_strategy', None)
        
        for evidence in state.evidences:
            scoring = await self._calculate_evidence_scores(evidence, state, strategy)
            evidence_scores.append(scoring)
        
        state.evidence_scores = evidence_scores
        return state
    
    async def _apply_ranking_node(self, state: ReactorState) -> ReactorState:
        """Apply ranking algorithm based on calculated scores."""
        evidence_scores = getattr(state, 'evidence_scores', [])
        
        if evidence_scores:
            ranking_calc = await self._apply_ranking_algorithm(evidence_scores, state)
            state.ranking_calculation = ranking_calc
        
        return state
    
    async def _validate_ranking_node(self, state: ReactorState) -> ReactorState:
        """Validate the quality of the ranking."""
        ranking_validation = await self._validate_ranking_quality(state)
        state.ranking_validation = ranking_validation
        return state
    
    async def _determine_adaptive_strategy(self, state: ReactorState) -> AdaptiveStrategy:
        """Determine the best ranking strategy based on query and evidence characteristics."""
        if not state.original_query:
            return self._fallback_adaptive_strategy()
        
        try:
            # Create structured LLM (like M1)
            strategy_llm = StructuredLLMFactory.create_strategy_llm()
            
            # Get prompt from prompts.md
            prompt = self._get_prompt("m8_strategy_selection",
                "Analyze the query and evidence to determine the optimal ranking strategy."
            )
            
            evidence_summary = self._summarize_evidence_characteristics(state.evidences)
            
            full_prompt = f"""{prompt}

<query>{state.original_query.text}</query>
<evidence_summary>
Total items: {len(state.evidences)}
{evidence_summary}
</evidence_summary>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            result: AdaptiveStrategy = await strategy_llm.ainvoke(full_prompt)
            
            self.logger.info(f"[{self.module_code}] Strategy selected: {result.strategy_name}")
            return result
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Strategy selection failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M8 Strategy Selection - {e}")
            print(f"   → Using fallback adaptive strategy")
            return self._fallback_adaptive_strategy()
    
    async def _calculate_evidence_scores(self, evidence: EvidenceItem, 
                                       state: ReactorState, 
                                       strategy: Optional[AdaptiveStrategy]) -> EvidenceScoring:
        """Calculate comprehensive scores for an evidence item using structured LLM output."""
        try:
            # Use structured LLM to get all scores at once
            scoring_llm = StructuredLLMFactory.create_scoring_llm()
            
            # Get prompt from prompts.md
            prompt = self._get_prompt("m8_evidence_scoring",
                "Score the evidence comprehensively for ranking purposes."
            )
            
            # Find the WorkUnit this evidence belongs to
            workunit = next((wu for wu in state.workunits if wu.id == evidence.workunit_id), None)
            workunit_text = workunit.text if workunit else state.original_query.text
            
            full_prompt = f"""{prompt}

<workunit_question>{workunit_text}</workunit_question>
<evidence_title>{evidence.title or 'No title'}</evidence_title>
<evidence_content>{evidence.content}</evidence_content>
<evidence_source>{evidence.provenance.source_id if evidence.provenance else 'Unknown'}</evidence_source>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            result: EvidenceScoring = await scoring_llm.ainvoke(full_prompt)
            
            # Ensure evidence_id is set correctly
            result.evidence_id = str(evidence.id)
            
            return result
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Evidence scoring failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M8 Evidence Scoring - {e}")
            print(f"   → Using heuristic scoring for evidence {evidence.id}")
            # Fallback to heuristic scoring
            return self._fallback_evidence_scoring(evidence, state, strategy)
            relevance_score * weights["relevance"] +
            quality_score * weights["quality"] +
            credibility_score * weights["credibility"] +
            recency_score * weights["recency"] +
            completeness_score * weights["completeness"]
        )
        
        # Update evidence score
        evidence.score_raw = composite_score
        
        return EvidenceScoring(
            evidence_id=str(evidence.id),
            relevance_score=relevance_score,
            quality_score=quality_score,
            credibility_score=credibility_score,
            recency_score=recency_score,
            completeness_score=completeness_score,
            composite_score=composite_score,
            confidence=0.85
        )
    
    async def _apply_ranking_algorithm(self, evidence_scores: List[EvidenceScoring], 
                                     state: ReactorState) -> RankingCalculation:
        """Apply the selected ranking algorithm."""
        algorithm = "multi_factor_weighted"
        
        # Sort by composite score
        sorted_scores = sorted(evidence_scores, key=lambda x: x.composite_score, reverse=True)
        
        # Calculate score distribution
        score_ranges = {"high": 0, "medium": 0, "low": 0}
        for score in sorted_scores:
            if score.composite_score >= 0.8:
                score_ranges["high"] += 1
            elif score.composite_score >= 0.5:
                score_ranges["medium"] += 1
            else:
                score_ranges["low"] += 1
        
        # Calculate ranking quality
        top_10_scores = [s.composite_score for s in sorted_scores[:10]]
        ranking_quality = sum(top_10_scores) / len(top_10_scores) if top_10_scores else 0.0
        
        return RankingCalculation(
            algorithm_used=algorithm,
            total_items=len(evidence_scores),
            ranking_factors=["relevance", "quality", "credibility", "recency", "completeness"],
            score_distribution=score_ranges,
            ranking_quality=ranking_quality,
            confidence=0.9
        )
    
    async def _validate_ranking_quality(self, state: ReactorState) -> RankingValidation:
        """Validate the quality and consistency of the ranking using structured LLM output."""
        evidence_scores = getattr(state, 'evidence_scores', [])
        
        if not evidence_scores:
            return RankingValidation(
                validation_method="no_evidence",
                ranking_consistency=1.0,
                top_items_quality=0.0,
                diversity_score=0.0,
                validation_issues=["No evidence to validate"],
                confidence=1.0
            )
        
        try:
            # Use structured LLM for validation
            validation_llm = StructuredLLMFactory.create_validation_llm()
            
            # Get prompt from prompts.md
            prompt = self._get_prompt("m8_ranking_validation",
                "Validate the quality and appropriateness of evidence ranking results."
            )
            
            # Prepare ranking summary for LLM
            ranking_summary = self._create_ranking_summary(state.evidences, evidence_scores)
            
            full_prompt = f"""{prompt}

<original_query>{state.original_query.text}</original_query>
<ranking_summary>
{ranking_summary}
</ranking_summary>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            result: RankingValidation = await validation_llm.ainvoke(full_prompt)
            
            return result
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Ranking validation failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M8 Ranking Validation - {e}")
            print(f"   → Using heuristic validation for {len(evidence_scores)} items")
            # Fallback to heuristic validation
            return self._fallback_ranking_validation(state, evidence_scores)
    
    def _create_ranking_summary(self, evidences: List[EvidenceItem], 
                              evidence_scores: List[EvidenceScoring]) -> str:
        """Create a summary of the ranking for LLM validation."""
        summary_lines = []
        
        for i, evidence in enumerate(evidences[:5], 1):  # Top 5 items
            score_info = next((s for s in evidence_scores if s.evidence_id == str(evidence.id)), None)
            composite_score = score_info.composite_score if score_info else evidence.score_raw
            
            summary_lines.append(f"{i}. [{composite_score:.3f}] {evidence.title}")
            summary_lines.append(f"   Content: {evidence.content[:100]}...")
            summary_lines.append(f"   Source: {evidence.provenance.source_type.value if evidence.provenance else 'Unknown'}")
        
        return "\n".join(summary_lines)
    
    def _fallback_ranking_validation(self, state: ReactorState, 
                                   evidence_scores: List[EvidenceScoring]) -> RankingValidation:
        """Fallback ranking validation using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M8 Ranking Validation - Using heuristic validation for {len(evidence_scores)} items")
        # Check ranking consistency
        scores = [s.composite_score for s in evidence_scores]
        consistency = self._calculate_ranking_consistency(scores)
        
        # Check top items quality
        top_scores = scores[:min(5, len(scores))]
        top_quality = sum(top_scores) / len(top_scores) if top_scores else 0.0
        
        # Check diversity in top results
        diversity = self._calculate_result_diversity(state.evidences[:10])
        
        # Identify issues
        issues = []
        if consistency < 0.7:
            issues.append("Low ranking consistency")
        if top_quality < 0.6:
            issues.append("Low quality in top results")
        if diversity < 0.3:
            issues.append("Low diversity in top results")
        
        return RankingValidation(
            validation_method="heuristic_fallback",
            ranking_consistency=consistency,
            top_items_quality=top_quality,
            diversity_score=diversity,
            validation_issues=issues,
            confidence=0.6  # Lower confidence for fallback
        )
    
    async def _calculate_relevance_score(self, evidence: EvidenceItem, state: ReactorState) -> float:
        """Calculate relevance score using LLM analysis with structured output."""
        if not state.original_query:
            return evidence.score_raw  # Fallback to existing score
        
        try:
            # Create structured LLM for evidence scoring
            scoring_llm = StructuredLLMFactory.create_scoring_llm()
            
            # Get prompt from prompts.md
            prompt = self._get_prompt("m8_evidence_scoring",
                "Score the relevance of this evidence to the query."
            )
            
            # Find the WorkUnit this evidence belongs to
            workunit = next((wu for wu in state.workunits if wu.id == evidence.workunit_id), None)
            workunit_text = workunit.text if workunit else state.original_query.text
            
            full_prompt = f"""{prompt}

<workunit_question>{workunit_text}</workunit_question>
<evidence_title>{evidence.title or 'No title'}</evidence_title>
<evidence_content>{evidence.content}</evidence_content>
<evidence_source>{evidence.provenance.source_id if evidence.provenance else 'Unknown'}</evidence_source>"""
            
            # Call structured LLM - returns validated Pydantic object directly
            result: EvidenceScoring = await scoring_llm.ainvoke(full_prompt)
            
            return result.relevance_score
            
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Relevance scoring failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M8 Relevance Scoring - {e}")
            print(f"   → Using original score {evidence.score_raw} for evidence {evidence.id}")
            return evidence.score_raw
    
    def _calculate_quality_score(self, evidence: EvidenceItem) -> float:
        """Calculate content quality score using heuristics."""
        content = evidence.content
        
        # Length factor (optimal around 200-500 chars)
        length_score = min(1.0, len(content) / 300)
        
        # Structure factor (presence of sentences, punctuation)
        sentences = content.count('.') + content.count('!') + content.count('?')
        structure_score = min(1.0, sentences / 5)
        
        # Information density (ratio of meaningful words)
        words = content.split()
        meaningful_words = [w for w in words if len(w) > 3]
        density_score = len(meaningful_words) / max(1, len(words))
        
        return (length_score + structure_score + density_score) / 3
    
    def _calculate_credibility_score(self, evidence: EvidenceItem) -> float:
        """Calculate source credibility score."""
        if not evidence.provenance:
            return 0.5  # Neutral score for unknown sources
        
        source_id = evidence.provenance.source_id
        
        # Simple credibility mapping
        credibility_map = {
            "academic": 0.9,
            "government": 0.85,
            "news": 0.7,
            "wiki": 0.6,
            "web": 0.5,
            "social": 0.3
        }
        
        for source_type, score in credibility_map.items():
            if source_type in source_id.lower():
                return score
        
        return 0.5  # Default neutral score
    
    def _calculate_recency_score(self, evidence: EvidenceItem) -> float:
        """Calculate information recency score."""
        # For now, return a default score since we don't have timestamp info
        # In a full implementation, this would use actual timestamps
        return 0.8
    
    def _calculate_completeness_score(self, evidence: EvidenceItem) -> float:
        """Calculate information completeness score."""
        content = evidence.content
        
        # Check for completeness indicators
        completeness_indicators = [
            "conclusion", "summary", "result", "finding",
            "therefore", "thus", "in summary", "overall"
        ]
        
        indicator_count = sum(1 for indicator in completeness_indicators 
                            if indicator in content.lower())
        
        # Length-based completeness
        length_completeness = min(1.0, len(content) / 200)
        
        # Indicator-based completeness
        indicator_completeness = min(1.0, indicator_count / 3)
        
        return (length_completeness + indicator_completeness) / 2
    
    def _get_adaptive_weights(self, strategy: Optional[AdaptiveStrategy]) -> Dict[str, float]:
        """Get adaptive weights based on strategy."""
        if not strategy:
            # Default balanced weights
            return {
                "relevance": 0.3,
                "quality": 0.25,
                "credibility": 0.2,
                "recency": 0.15,
                "completeness": 0.1
            }
        
        # Apply strategy adjustments
        base_weights = {
            "relevance": 0.3,
            "quality": 0.25,
            "credibility": 0.2,
            "recency": 0.15,
            "completeness": 0.1
        }
        
        # Adjust weights based on strategy
        for factor, adjustment in strategy.weight_adjustments.items():
            if factor in base_weights:
                base_weights[factor] = adjustment
        
        # Normalize weights to sum to 1.0
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            for factor in base_weights:
                base_weights[factor] /= total_weight
        
        return base_weights
    
    def _summarize_evidence_characteristics(self, evidences: List[EvidenceItem]) -> str:
        """Summarize characteristics of evidence collection."""
        if not evidences:
            return "No evidence available"
        
        avg_score = sum(e.score_raw for e in evidences) / len(evidences)
        avg_length = sum(len(e.content) for e in evidences) / len(evidences)
        
        sources = set()
        for evidence in evidences:
            if evidence.provenance:
                sources.add(evidence.provenance.source_id)
        
        return f"Average score: {avg_score:.2f}, Average length: {avg_length:.0f}, Sources: {len(sources)}"
    
    def _calculate_ranking_consistency(self, scores: List[float]) -> float:
        """Calculate consistency of ranking scores."""
        if len(scores) < 2:
            return 1.0
        
        # Calculate variance in score differences
        differences = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
        
        if not differences:
            return 1.0
        
        avg_diff = sum(differences) / len(differences)
        variance = sum((d - avg_diff) ** 2 for d in differences) / len(differences)
        
        # Convert variance to consistency score (lower variance = higher consistency)
        consistency = 1.0 / (1.0 + variance)
        
        return consistency
    
    def _fallback_evidence_scoring(self, evidence: EvidenceItem, 
                                 state: ReactorState, 
                                 strategy: Optional[AdaptiveStrategy]) -> EvidenceScoring:
        """Fallback evidence scoring using heuristics."""
        print(f"🔄 EXECUTING FALLBACK: M8 Evidence Scoring - Using heuristic scoring for {evidence.id}")
        # Use heuristic calculations
        quality_score = self._calculate_quality_score(evidence)
        credibility_score = self._calculate_credibility_score(evidence)
        recency_score = self._calculate_recency_score(evidence)
        completeness_score = self._calculate_completeness_score(evidence)
        
        # Simple relevance based on original score
        relevance_score = evidence.score_raw
        
        # Apply adaptive weights
        weights = self._get_adaptive_weights(strategy)
        
        composite_score = (
            relevance_score * weights.get("relevance", 0.3) +
            quality_score * weights.get("quality", 0.25) +
            credibility_score * weights.get("credibility", 0.25) +
            completeness_score * weights.get("completeness", 0.2)
        )
        
        return EvidenceScoring(
            evidence_id=str(evidence.id),
            relevance_score=relevance_score,
            quality_score=quality_score,
            credibility_score=credibility_score,
            recency_score=recency_score,
            completeness_score=completeness_score,
            composite_score=composite_score,
            confidence=0.7  # Lower confidence for fallback
        )
    
    def _calculate_result_diversity(self, evidences: List[EvidenceItem]) -> float:
        """Calculate diversity in top results."""
        if not evidences:
            return 0.0
        
        # Simple diversity based on content uniqueness
        unique_content_starts = set()
        for evidence in evidences:
            content_start = evidence.content[:50].lower()
            unique_content_starts.add(content_start)
        
        diversity = len(unique_content_starts) / len(evidences)
        return diversity
    
    def _fallback_adaptive_strategy(self) -> AdaptiveStrategy:
        """Fallback adaptive strategy when LLM analysis fails."""
        print(f"🔄 EXECUTING FALLBACK: M8 Adaptive Strategy - Using balanced default strategy")
        return AdaptiveStrategy(
            strategy_name="balanced",
            query_characteristics={"complexity": 0.5, "specificity": 0.5},
            weight_adjustments={
                "relevance": 0.3,
                "quality": 0.25,
                "credibility": 0.2,
                "recency": 0.15,
                "completeness": 0.1
            },
            strategy_rationale="Default balanced strategy due to analysis failure",
            expected_improvement=0.1,
            confidence=0.6
        )


# Module instance
reranker_langgraph = ReRankerLangGraph()


# LangGraph node function
async def reranker_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M8 - ReRanker."""
    return await reranker_langgraph.execute(state)