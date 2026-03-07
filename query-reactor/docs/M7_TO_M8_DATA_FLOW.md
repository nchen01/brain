# M7 → M8 Data Flow: Evidence Aggregator to ReRanker

## 🔄 **Complete Data Flow from M7 to M8**

### **M7 Output → ReactorState Storage**

M7 Evidence Aggregator stores its results in multiple locations within `ReactorState`:

```python
# After M7 execution, ReactorState contains:
class ReactorState:
    # 🔑 PRIMARY DATA for M8
    evidences: List[EvidenceItem] = []  # ← M8's main input (filtered & deduplicated)
    
    # 🔑 M7 AGGREGATION METADATA (available to M8)
    evidence_collection: EvidenceCollection = None      # Collection analysis
    deduplication_results: DeduplicationResults = None  # Duplicate removal info
    source_merging: SourceMerging = None                # Cross-source merging info
    consistency_validation: ConsistencyValidation = None # Consistency check results
    original_evidence_count: int = None                 # Pre-aggregation count
    
    # 🔑 EXISTING FIELDS M8 can also use
    evidence_sets: Optional[List[Any]] = None           # From M7 (if used)
    workunits: List[WorkUnit] = []                      # Original work units
    original_query: UserQuery                           # Original user query
```

## 📊 **What M8 ReRanker Can Access**

### **1. Primary Evidence Data**
```python
# M8's main input - the filtered, deduplicated evidence from M7
state.evidences: List[EvidenceItem]

# Example after M7 processing:
state.evidences = [
    EvidenceItem(
        id=UUID("evidence-1"),
        workunit_id=UUID("wu-123"),
        content="Solar energy is clean and renewable...",
        title="Solar Energy Benefits",
        score_raw=0.9,  # Original retrieval score
        provenance=Provenance(
            source_type=SourceType.db,
            source_id="solar_db",
            retrieval_path="P1"
        )
    ),
    EvidenceItem(
        id=UUID("evidence-2"),
        workunit_id=UUID("wu-456"),
        content="Wind power generates electricity...",
        title="Wind Energy Advantages", 
        score_raw=0.88,
        provenance=Provenance(
            source_type=SourceType.web,
            source_id="wind_web",
            retrieval_path="P2"
        )
    )
    # Note: Duplicates removed by M7
]
```

### **2. M7 Aggregation Metadata**
```python
# Collection Analysis Results
state.evidence_collection: EvidenceCollection = {
    "total_evidence": 4,
    "source_distribution": {"solar_db": 1, "wind_web": 1, "api_solar": 1},
    "quality_distribution": {"high": 3, "medium": 1, "low": 0},
    "coverage_analysis": "Coverage: comprehensive (3 sources), Content: brief",
    "confidence": 0.9
}

# Deduplication Results
state.deduplication_results: DeduplicationResults = {
    "original_count": 4,
    "duplicate_count": 2,
    "final_count": 2,
    "duplicate_pairs": [
        {"original_id": "evidence-1", "duplicate_id": "evidence-4", "similarity": "exact_match"}
    ],
    "deduplication_method": "content_hash + semantic_similarity",
    "confidence": 0.85
}

# Source Merging Results
state.source_merging: SourceMerging = {
    "merged_groups": [
        {
            "group_id": "renewable_energy_group",
            "base_evidence_id": "evidence-1",
            "merged_evidence_ids": ["evidence-1", "evidence-2"],
            "combined_content": "Solar and wind energy...",
            "merged_score": 0.99,
            "source_count": 2
        }
    ],
    "merge_strategies": ["content_synthesis"],
    "quality_improvements": {"renewable_energy_group": 0.125},
    "information_gain": 0.167,
    "confidence": 0.8
}

# Consistency Validation Results
state.consistency_validation: ConsistencyValidation = {
    "consistency_score": 1.0,
    "conflicting_evidence": [],
    "consensus_items": ["evidence-1", "evidence-2"],
    "uncertainty_areas": [],
    "validation_method": "cross_reference_analysis",
    "confidence": 0.8
}
```

## 🎯 **How M8 Uses M7's Results**

### **M8 Execute Method - Input Processing**
```python
# In M8: src/modules/m8_reranker_langgraph.py line 85-95
async def execute(self, state: ReactorState) -> ReactorState:
    """Execute evidence reranking using LangGraph."""
    
    # 🔑 M8 accesses M7's filtered evidence
    if not state.evidences:  # ← M7's deduplicated evidence list
        self._log_execution_end(state, "No evidence to rerank")
        return state
    
    # M8 can also access M7's metadata for enhanced ranking
    collection_info = getattr(state, 'evidence_collection', None)
    dedup_info = getattr(state, 'deduplication_results', None)
    consistency_info = getattr(state, 'consistency_validation', None)
```

### **M8 Analysis Node - Using M7 Metadata**
```python
# M8 can use M7's aggregation results for better ranking strategy
async def _analyze_evidence_node(self, state: ReactorState) -> ReactorState:
    """Analyze evidence characteristics for ranking strategy."""
    
    # Access M7's collection analysis
    if hasattr(state, 'evidence_collection'):
        collection = state.evidence_collection
        source_diversity = len(collection.source_distribution)
        quality_dist = collection.quality_distribution
        
        # Adjust ranking strategy based on M7's analysis
        if source_diversity >= 3:
            strategy = "multi_source_ranking"
        elif quality_dist.get("high", 0) > quality_dist.get("medium", 0):
            strategy = "quality_focused_ranking"
    
    # Access M7's consistency validation
    if hasattr(state, 'consistency_validation'):
        validation = state.consistency_validation
        if validation.consistency_score < 0.7:
            # Use conflict-aware ranking for inconsistent evidence
            strategy = "conflict_aware_ranking"
```

## 📋 **M8 Output - Enhanced with M7 Context**

### **M8 Stores Enhanced Rankings**
```python
# After M8 processing, ReactorState gets additional ranking data:
class ReactorState:
    # Updated by M8
    evidences: List[EvidenceItem] = []  # ← Now reranked based on M7's clean data
    evidence_scores: List[EvidenceScoring] = []  # ← M8's detailed scoring
    ranking_calculation: RankingCalculation = None  # ← M8's ranking algorithm info
    ranking_validation: RankingValidation = None   # ← M8's ranking quality check
    adaptive_strategy: AdaptiveStrategy = None     # ← M8's strategy (informed by M7)
    
    # Preserved from M7
    evidence_collection: EvidenceCollection = None
    deduplication_results: DeduplicationResults = None
    source_merging: SourceMerging = None
    consistency_validation: ConsistencyValidation = None
```

## 🔍 **Specific Object Names M8 Uses**

### **Primary Input Object**
```python
# Object Name: state.evidences
# Type: List[EvidenceItem]
# Source: M7's filtered and deduplicated evidence
# Usage: M8's main ranking input

for evidence in state.evidences:  # ← M8 iterates through M7's clean evidence
    # Calculate enhanced scores based on M7's quality improvements
    enhanced_score = evidence.score_raw * quality_multiplier
```

### **M7 Metadata Objects M8 Can Use**
```python
# 1. Collection Analysis
state.evidence_collection: EvidenceCollection
# Usage: Inform ranking strategy based on source diversity and quality distribution

# 2. Deduplication Results  
state.deduplication_results: DeduplicationResults
# Usage: Understand evidence reduction and quality improvements

# 3. Source Merging Results
state.source_merging: SourceMerging
# Usage: Leverage merged content and quality improvements

# 4. Consistency Validation
state.consistency_validation: ConsistencyValidation
# Usage: Apply conflict-aware ranking for inconsistent evidence
```

## 🚀 **Enhanced M8 Ranking with M7 Context**

### **Example: M8 Using M7's Quality Improvements**
```python
async def _calculate_scores_node(self, state: ReactorState) -> ReactorState:
    """Calculate enhanced scores using M7's aggregation results."""
    
    evidence_scores = []
    
    # Get M7's quality improvements
    quality_improvements = {}
    if hasattr(state, 'source_merging') and state.source_merging:
        quality_improvements = state.source_merging.quality_improvements
    
    for evidence in state.evidences:
        # Base score from retrieval
        base_score = evidence.score_raw
        
        # Apply M7's quality improvements
        quality_boost = quality_improvements.get(evidence.id, 0.0)
        enhanced_score = min(1.0, base_score + quality_boost)
        
        # Create enhanced scoring
        scoring = EvidenceScoring(
            evidence_id=str(evidence.id),
            relevance_score=enhanced_score,
            quality_score=enhanced_score * 1.1,  # M7 improved quality
            credibility_score=0.9,  # Based on M7's source analysis
            composite_score=enhanced_score,
            confidence=0.85
        )
        evidence_scores.append(scoring)
    
    state.evidence_scores = evidence_scores
    return state
```

## 📊 **Data Flow Summary**

```
M7 Evidence Aggregator
    ↓
    Processes: 4 evidence items
    Deduplicates: Removes 2 duplicates  
    Merges: Creates 1 merged group
    Validates: 100% consistency
    ↓
ReactorState Updated:
    ├─ evidences: List[EvidenceItem] (2 clean items)
    ├─ evidence_collection: EvidenceCollection
    ├─ deduplication_results: DeduplicationResults  
    ├─ source_merging: SourceMerging
    └─ consistency_validation: ConsistencyValidation
    ↓
M8 ReRanker
    ├─ Reads: state.evidences (primary input)
    ├─ Uses: M7 metadata for enhanced ranking
    ├─ Applies: Context-aware ranking algorithms
    └─ Outputs: Reranked evidence with detailed scores
```

## 🎯 **Key Takeaways**

1. **Primary Data**: M8 gets clean, deduplicated evidence via `state.evidences`
2. **Enhanced Context**: M8 can use M7's metadata for smarter ranking strategies  
3. **Quality Boost**: M7's quality improvements inform M8's scoring algorithms
4. **Consistency Aware**: M8 can apply conflict-aware ranking based on M7's validation
5. **Preserved Metadata**: All M7 analysis results remain available throughout the pipeline

The integration ensures M8 gets high-quality, pre-processed evidence while having access to rich metadata for enhanced ranking decisions!