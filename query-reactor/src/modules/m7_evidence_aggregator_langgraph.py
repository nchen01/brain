"""M7 - Evidence Aggregator (LangGraph + Pydantic Implementation)."""

from typing import List, Dict, Optional, Set
from uuid import uuid4
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import ReactorState, EvidenceItem, Provenance
from .base import LLMModule
import time


class EvidenceCollection(BaseModel):
    """Pydantic model for evidence collection analysis."""
    total_evidence: int = Field(description="Total evidence items collected")
    source_distribution: Dict[str, int] = Field(description="Evidence count per source")
    quality_distribution: Dict[str, int] = Field(description="Evidence count per quality tier")
    coverage_analysis: str = Field(description="Analysis of topic coverage")
    confidence: float = Field(ge=0.0, le=1.0, description="Collection confidence")


class DeduplicationResults(BaseModel):
    """Pydantic model for deduplication results."""
    original_count: int = Field(description="Original evidence count")
    duplicate_count: int = Field(description="Number of duplicates found")
    final_count: int = Field(description="Final evidence count after deduplication")
    duplicate_pairs: List[Dict[str, str]] = Field(description="Identified duplicate pairs")
    deduplication_method: str = Field(description="Method used for deduplication")
    confidence: float = Field(ge=0.0, le=1.0, description="Deduplication confidence")


class SourceMerging(BaseModel):
    """Pydantic model for cross-source evidence merging."""
    merged_groups: List[Dict] = Field(description="Groups of merged evidence")
    merge_strategies: List[str] = Field(description="Strategies used for merging")
    quality_improvements: Dict[str, float] = Field(description="Quality improvements per group")
    information_gain: float = Field(ge=0.0, le=1.0, description="Information gain from merging")
    confidence: float = Field(ge=0.0, le=1.0, description="Merging confidence")


class ConsistencyValidation(BaseModel):
    """Pydantic model for evidence consistency checking."""
    consistency_score: float = Field(ge=0.0, le=1.0, description="Overall consistency score")
    conflicting_evidence: List[Dict] = Field(description="Identified conflicts")
    consensus_items: List[str] = Field(description="Evidence items with strong consensus")
    uncertainty_areas: List[str] = Field(description="Areas with high uncertainty")
    validation_method: str = Field(description="Method used for validation")
    confidence: float = Field(ge=0.0, le=1.0, description="Validation confidence")


class EvidenceAggregatorLangGraph(LLMModule):
    """M7 - Evidence aggregator with LangGraph orchestration."""
    
    def __init__(self):
        super().__init__("M7_LG", "ea.model")
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow for evidence aggregation."""
        workflow = StateGraph(ReactorState)
        
        workflow.add_node("collect_evidence", self._collect_evidence_node)
        workflow.add_node("deduplicate", self._deduplicate_node)
        workflow.add_node("merge_sources", self._merge_sources_node)
        workflow.add_node("validate_consistency", self._validate_consistency_node)
        
        workflow.add_edge("collect_evidence", "deduplicate")
        workflow.add_edge("deduplicate", "merge_sources")
        workflow.add_edge("merge_sources", "validate_consistency")
        workflow.add_edge("validate_consistency", END)
        
        workflow.set_entry_point("collect_evidence")
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute evidence aggregation using LangGraph."""
        self._update_state_module(state)
        self._log_execution_start(state, "Aggregating evidence")
        
        if not state.evidences:
            self._log_execution_end(state, "No evidence to aggregate")
            return state
        
        try:
            # Call pipeline nodes directly (avoids LangGraph sub-graph dict serialization issues)
            result_state = await self._collect_evidence_node(state)
            result_state = await self._deduplicate_node(result_state)
            result_state = await self._merge_sources_node(result_state)
            result_state = await self._validate_consistency_node(result_state)

            final_count = len(result_state.evidences)
            original_count = getattr(result_state, 'original_evidence_count', final_count)
            self._log_execution_end(result_state, f"Aggregated evidence: {original_count} → {final_count}")
            
            return result_state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M7 Execute - {e}")
            print(f"   → Returning original state")
            return state
    
    async def _collect_evidence_node(self, state: ReactorState) -> ReactorState:
        """Collect and analyze all available evidence."""
        collection = await self._analyze_evidence_collection(state.evidences)
        state.evidence_collection = collection
        state.original_evidence_count = len(state.evidences)
        return state
    
    async def _deduplicate_node(self, state: ReactorState) -> ReactorState:
        """Remove duplicate evidence items."""
        dedup_results = await self._deduplicate_evidence(state.evidences)
        
        # Apply deduplication
        unique_evidence = self._apply_deduplication(state.evidences, dedup_results)
        state.evidences = unique_evidence
        state.deduplication_results = dedup_results
        
        return state
    
    async def _merge_sources_node(self, state: ReactorState) -> ReactorState:
        """Merge evidence from different sources."""
        merging_results = await self._merge_cross_source_evidence(state.evidences)
        
        # Apply merging
        merged_evidence = self._apply_source_merging(state.evidences, merging_results)
        state.evidences = merged_evidence
        state.source_merging = merging_results
        
        return state
    
    async def _validate_consistency_node(self, state: ReactorState) -> ReactorState:
        """Validate consistency across all evidence."""
        validation = await self._validate_evidence_consistency(state.evidences)
        state.consistency_validation = validation
        
        # Filter out highly conflicting evidence if configured
        if self._get_config("ea.filter_conflicts", False):
            filtered_evidence = self._filter_conflicting_evidence(state.evidences, validation)
            state.evidences = filtered_evidence
        
        return state
    
    async def _analyze_evidence_collection(self, evidences: List[EvidenceItem]) -> EvidenceCollection:
        """Analyze the collected evidence for completeness and distribution."""
        if not evidences:
            return EvidenceCollection(
                total_evidence=0,
                source_distribution={},
                quality_distribution={},
                coverage_analysis="No evidence available",
                confidence=1.0
            )
        
        # Analyze source distribution
        source_dist = {}
        for evidence in evidences:
            source = evidence.provenance.source_id if evidence.provenance else "unknown"
            source_dist[source] = source_dist.get(source, 0) + 1
        
        # Analyze quality distribution
        quality_dist = {"high": 0, "medium": 0, "low": 0}
        for evidence in evidences:
            if evidence.score_raw >= 0.8:
                quality_dist["high"] += 1
            elif evidence.score_raw >= 0.5:
                quality_dist["medium"] += 1
            else:
                quality_dist["low"] += 1
        
        # Generate coverage analysis
        coverage_analysis = await self._analyze_topic_coverage(evidences)
        
        return EvidenceCollection(
            total_evidence=len(evidences),
            source_distribution=source_dist,
            quality_distribution=quality_dist,
            coverage_analysis=coverage_analysis,
            confidence=0.9
        )
    
    async def _deduplicate_evidence(self, evidences: List[EvidenceItem]) -> DeduplicationResults:
        """Identify and mark duplicate evidence items."""
        duplicate_pairs = []
        seen_content = {}
        
        # Simple content-based deduplication
        for i, evidence in enumerate(evidences):
            content_hash = self._generate_content_hash(evidence.content)
            
            if content_hash in seen_content:
                duplicate_pairs.append({
                    "original_id": str(seen_content[content_hash].id),
                    "duplicate_id": str(evidence.id),
                    "similarity": "exact_match"
                })
            else:
                seen_content[content_hash] = evidence
        
        # Advanced semantic deduplication for near-duplicates
        semantic_duplicates = await self._find_semantic_duplicates(evidences)
        duplicate_pairs.extend(semantic_duplicates)
        
        return DeduplicationResults(
            original_count=len(evidences),
            duplicate_count=len(duplicate_pairs),
            final_count=len(evidences) - len(duplicate_pairs),
            duplicate_pairs=duplicate_pairs,
            deduplication_method="content_hash + semantic_similarity",
            confidence=0.85
        )
    
    async def _merge_cross_source_evidence(self, evidences: List[EvidenceItem]) -> SourceMerging:
        """Merge complementary evidence from different sources."""
        merged_groups = []
        merge_strategies = []
        quality_improvements = {}
        
        # Group evidence by topic/content similarity
        content_groups = self._group_by_content_similarity(evidences)
        
        for group_id, group_evidences in content_groups.items():
            if len(group_evidences) > 1:
                # Merge evidence from different sources
                merged_info = await self._merge_evidence_group(group_evidences)
                merged_groups.append(merged_info)
                merge_strategies.append("content_synthesis")
                
                # Calculate quality improvement
                original_avg = sum(e.score_raw for e in group_evidences) / len(group_evidences)
                improved_score = min(1.0, original_avg * 1.2)  # 20% improvement
                quality_improvements[group_id] = improved_score - original_avg
        
        information_gain = len(merged_groups) / max(1, len(evidences)) * 0.5
        
        return SourceMerging(
            merged_groups=merged_groups,
            merge_strategies=merge_strategies,
            quality_improvements=quality_improvements,
            information_gain=information_gain,
            confidence=0.8
        )
    
    async def _validate_evidence_consistency(self, evidences: List[EvidenceItem]) -> ConsistencyValidation:
        """Validate consistency across all evidence items."""
        if len(evidences) < 2:
            return ConsistencyValidation(
                consistency_score=1.0,
                conflicting_evidence=[],
                consensus_items=[str(e.id) for e in evidences],
                uncertainty_areas=[],
                validation_method="single_source",
                confidence=1.0
            )
        
        # Identify potential conflicts
        conflicts = await self._identify_conflicts(evidences)
        
        # Find consensus items
        consensus_items = self._find_consensus_items(evidences)
        
        # Identify uncertainty areas
        uncertainty_areas = await self._identify_uncertainty_areas(evidences)
        
        # Calculate overall consistency score
        conflict_penalty = len(conflicts) / len(evidences) * 0.5
        consistency_score = max(0.0, 1.0 - conflict_penalty)
        
        return ConsistencyValidation(
            consistency_score=consistency_score,
            conflicting_evidence=conflicts,
            consensus_items=consensus_items,
            uncertainty_areas=uncertainty_areas,
            validation_method="cross_reference_analysis",
            confidence=0.8
        )
    
    async def _analyze_topic_coverage(self, evidences: List[EvidenceItem]) -> str:
        """Analyze how well the evidence covers the topic."""
        if not evidences:
            return "No evidence available for coverage analysis"
        
        # Simple coverage analysis based on content diversity
        unique_sources = set()
        total_content_length = 0
        
        for evidence in evidences:
            if evidence.provenance:
                unique_sources.add(evidence.provenance.source_id)
            total_content_length += len(evidence.content)
        
        avg_content_length = total_content_length / len(evidences)
        
        coverage_quality = "comprehensive" if len(unique_sources) >= 3 else "limited"
        content_depth = "detailed" if avg_content_length > 200 else "brief"
        
        return f"Coverage: {coverage_quality} ({len(unique_sources)} sources), Content: {content_depth}"
    
    async def _find_semantic_duplicates(self, evidences: List[EvidenceItem]) -> List[Dict[str, str]]:
        """Find semantically similar evidence items."""
        duplicates = []
        
        # Simple semantic similarity based on content overlap
        for i, evidence1 in enumerate(evidences):
            for j, evidence2 in enumerate(evidences[i+1:], i+1):
                similarity = self._calculate_content_similarity(evidence1.content, evidence2.content)
                
                if similarity > 0.8:  # High similarity threshold
                    duplicates.append({
                        "original_id": str(evidence1.id),
                        "duplicate_id": str(evidence2.id),
                        "similarity": f"semantic_{similarity:.2f}"
                    })
        
        return duplicates
    
    def _group_by_content_similarity(self, evidences: List[EvidenceItem]) -> Dict[str, List[EvidenceItem]]:
        """Group evidence by content similarity."""
        groups = {}
        
        for evidence in evidences:
            # Simple grouping by first few words
            content_key = " ".join(evidence.content.split()[:5]).lower()
            
            if content_key not in groups:
                groups[content_key] = []
            groups[content_key].append(evidence)
        
        return groups
    
    async def _merge_evidence_group(self, group_evidences: List[EvidenceItem]) -> Dict:
        """Merge a group of related evidence items."""
        # Combine content from all evidence in group
        combined_content = "\n".join([e.content for e in group_evidences])
        
        # Use the highest scoring evidence as base
        best_evidence = max(group_evidences, key=lambda e: e.score_raw)
        
        return {
            "group_id": str(uuid4()),
            "base_evidence_id": str(best_evidence.id),
            "merged_evidence_ids": [str(e.id) for e in group_evidences],
            "combined_content": combined_content[:500] + "...",  # Truncate for storage
            "merged_score": min(1.0, best_evidence.score_raw * 1.1),
            "source_count": len(set(e.provenance.source_id for e in group_evidences if e.provenance))
        }
    
    async def _identify_conflicts(self, evidences: List[EvidenceItem]) -> List[Dict]:
        """Identify conflicting information in evidence."""
        conflicts = []
        
        # Simple conflict detection based on contradictory keywords
        conflict_indicators = [
            ("yes", "no"), ("true", "false"), ("increase", "decrease"),
            ("positive", "negative"), ("support", "oppose")
        ]
        
        for i, evidence1 in enumerate(evidences):
            for j, evidence2 in enumerate(evidences[i+1:], i+1):
                for pos_word, neg_word in conflict_indicators:
                    if (pos_word in evidence1.content.lower() and 
                        neg_word in evidence2.content.lower()):
                        conflicts.append({
                            "evidence1_id": str(evidence1.id),
                            "evidence2_id": str(evidence2.id),
                            "conflict_type": f"{pos_word}_vs_{neg_word}",
                            "confidence": 0.7
                        })
        
        return conflicts
    
    def _find_consensus_items(self, evidences: List[EvidenceItem]) -> List[str]:
        """Find evidence items that have consensus support."""
        consensus_items = []
        
        # Simple consensus: evidence with high scores and no conflicts
        for evidence in evidences:
            if evidence.score_raw >= 0.8:
                consensus_items.append(str(evidence.id))
        
        return consensus_items
    
    async def _identify_uncertainty_areas(self, evidences: List[EvidenceItem]) -> List[str]:
        """Identify areas with high uncertainty or conflicting information."""
        uncertainty_areas = []
        
        # Identify topics with low-scoring evidence
        low_score_topics = set()
        for evidence in evidences:
            if evidence.score_raw < 0.5:
                # Extract key topics from content
                words = evidence.content.split()[:10]
                topic = " ".join(words)
                low_score_topics.add(topic)
        
        uncertainty_areas = list(low_score_topics)[:5]  # Limit to top 5
        
        return uncertainty_areas
    
    def _apply_deduplication(self, evidences: List[EvidenceItem], 
                           dedup_results: DeduplicationResults) -> List[EvidenceItem]:
        """Apply deduplication results to evidence list."""
        duplicate_ids = set()
        
        for pair in dedup_results.duplicate_pairs:
            duplicate_ids.add(pair["duplicate_id"])
        
        # Keep only non-duplicate evidence
        unique_evidence = [e for e in evidences if str(e.id) not in duplicate_ids]
        
        return unique_evidence
    
    def _apply_source_merging(self, evidences: List[EvidenceItem], 
                            merging_results: SourceMerging) -> List[EvidenceItem]:
        """Apply source merging results to evidence list."""
        # For now, just return original evidence
        # In a full implementation, this would create new merged evidence items
        return evidences
    
    def _filter_conflicting_evidence(self, evidences: List[EvidenceItem], 
                                   validation: ConsistencyValidation) -> List[EvidenceItem]:
        """Filter out highly conflicting evidence."""
        if validation.consistency_score >= 0.7:
            return evidences  # No filtering needed
        
        # Remove evidence involved in conflicts
        conflicting_ids = set()
        for conflict in validation.conflicting_evidence:
            conflicting_ids.add(conflict["evidence1_id"])
            conflicting_ids.add(conflict["evidence2_id"])
        
        # Keep evidence not involved in conflicts or with high scores
        filtered_evidence = [
            e for e in evidences 
            if str(e.id) not in conflicting_ids or e.score_raw >= 0.8
        ]
        
        return filtered_evidence
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        # Simple hash based on normalized content
        normalized = " ".join(content.lower().split())
        return str(hash(normalized))
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


# Module instance
evidence_aggregator_langgraph = EvidenceAggregatorLangGraph()


# LangGraph node function
async def evidence_aggregator_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M7 - Evidence Aggregator."""
    return await evidence_aggregator_langgraph.execute(state)