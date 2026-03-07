# P2 → M5 → M4 Data Flow and Types

## 🔄 **Complete Data Flow Trace**

### **Step 1: Input to M5 (P2 Path)**
```python
# Data Type: ReactorState
path_state = ReactorState(
    original_query=UserQuery(...),
    workunits=[
        WorkUnit(
            id=UUID("wu-123"),
            text="Latest AI developments 2024",
            user_id=UUID(...),
            conversation_id=UUID(...),
            # ...
        ),
        WorkUnit(
            id=UUID("wu-456"), 
            text="AI comparison 2023 vs 2024",
            # ...
        )
    ],
    evidences=[],  # Empty initially
    # ...
)
```

### **Step 2: M5 Processing - Creates EvidenceItem Objects**
```python
# In M5: src/modules/m5_internet_retrieval_langgraph.py line 350-380
async def _create_evidence_items(self, search_results, workunit, user_id, conversation_id):
    """Convert search results to EvidenceItem objects."""
    evidence_items = []
    
    for i, result in enumerate(search_results):
        # 🔑 Data Type: EvidenceItem
        evidence = EvidenceItem(
            id=UUID("evidence-abc-123"),           # Auto-generated
            workunit_id=workunit.id,               # Links to WorkUnit
            user_id=user_id,                       # From original query
            conversation_id=conversation_id,       # From original query
            content="AI developments in 2024...",  # From Perplexity search
            title="Latest AI Breakthroughs",      # From search result
            section_title=None,                    # Optional
            language="en",                         # Detected/default
            char_len=1250,                         # Auto-calculated
            tokens=None,                           # Optional
            score_raw=0.8,                         # Relevance score (0.8, 0.7, 0.6...)
            embeddings=None,                       # Optional vector
            provenance=Provenance(
                source_type=SourceType.web,        # "web"
                source_id="https://example.com/ai-news",
                url="https://example.com/ai-news",
                retrieval_path="P2",               # Path identifier
                router_decision_id=workunit.id,    # Links to routing
                language="en"
            )
        )
        evidence_items.append(evidence)
    
    return evidence_items
```

### **Step 3: M5 Output - Updated ReactorState**
```python
# After M5 processing, ReactorState.evidences contains:
state.evidences = [
    EvidenceItem(
        id=UUID("evidence-1"),
        workunit_id=UUID("wu-123"),  # From WorkUnit 1
        content="Latest AI developments include GPT-5, Claude 3.5...",
        title="AI Breakthroughs 2024",
        score_raw=0.8,
        provenance=Provenance(
            source_type=SourceType.web,
            url="https://bernardmarr.com/ai-breakthroughs-2024/",
            retrieval_path="P2"
        )
    ),
    EvidenceItem(
        id=UUID("evidence-2"),
        workunit_id=UUID("wu-123"),  # Same WorkUnit, different source
        content="Google Research announced breakthrough in quantum AI...",
        title="Google AI Research 2024",
        score_raw=0.7,
        provenance=Provenance(
            source_type=SourceType.web,
            url="https://research.google/blog/2024-breakthroughs/",
            retrieval_path="P2"
        )
    ),
    EvidenceItem(
        id=UUID("evidence-3"),
        workunit_id=UUID("wu-456"),  # From WorkUnit 2
        content="Comparing 2023 vs 2024 AI developments shows...",
        title="AI Progress Comparison",
        score_raw=0.6,
        provenance=Provenance(
            source_type=SourceType.web,
            url="https://hai.stanford.edu/ai-index-2025/",
            retrieval_path="P2"
        )
    )
]
```

### **Step 4: M4 Input - Same ReactorState with Evidence**
```python
# M4 receives the ReactorState with populated evidences
# Data Type: ReactorState (same as M5 output)
quality_check_input = ReactorState(
    original_query=UserQuery(...),
    workunits=[...],  # Same WorkUnits
    evidences=[...],  # EvidenceItem objects from M5
    # ...
)
```

### **Step 5: M4 Processing - Quality Assessment**
```python
# In M4: src/modules/m4_retrieval_quality_check_langgraph.py
async def _assess_evidence_quality(self, evidence: EvidenceItem, original_query: str):
    """Assess quality of a single evidence item."""
    
    # 🔑 Data Type: QualityAssessment
    assessment = QualityAssessment(
        evidence_id=evidence.id,
        relevance_score=0.85,      # How relevant to query
        credibility_score=0.90,    # Source credibility
        recency_score=0.95,        # Information freshness
        completeness_score=0.80,   # Information completeness
        overall_score=0.875,       # Weighted average
        reasoning="High-quality source with recent, relevant information about AI developments",
        should_keep=True           # Keep if overall_score > threshold
    )
    
    return assessment
```

### **Step 6: M4 Output - Filtered ReactorState**
```python
# After M4 quality check, some evidence may be filtered out
# Data Type: ReactorState (with filtered evidences)
filtered_state = ReactorState(
    original_query=UserQuery(...),
    workunits=[...],  # Same WorkUnits
    evidences=[
        # Only high-quality evidence items remain
        EvidenceItem(
            id=UUID("evidence-1"),
            workunit_id=UUID("wu-123"),
            content="Latest AI developments include GPT-5...",
            score_raw=0.8,
            # Quality metadata may be added
            provenance=Provenance(
                source_type=SourceType.web,
                url="https://bernardmarr.com/ai-breakthroughs-2024/",
                retrieval_path="P2"
            )
        ),
        EvidenceItem(
            id=UUID("evidence-2"),
            workunit_id=UUID("wu-123"),
            content="Google Research announced breakthrough...",
            score_raw=0.7,
            provenance=Provenance(
                source_type=SourceType.web,
                url="https://research.google/blog/2024-breakthroughs/",
                retrieval_path="P2"
            )
        )
        # evidence-3 might be filtered out if quality score < threshold
    ],
    rqc_results={  # M4 may add quality check results
        "total_assessed": 3,
        "kept": 2,
        "filtered": 1,
        "average_quality": 0.82
    }
)
```

### **Step 7: Return to M2D5 Path Coordinator**
```python
# M2D5 receives the quality-checked state and extracts results by WorkUnit
# Data Type: PathExecutionResult
path_result = PathExecutionResult(
    path_id="P2",
    workunit_results={
        UUID("wu-123"): [
            # Evidence items for WorkUnit wu-123
            EvidenceItem(id=UUID("evidence-1"), workunit_id=UUID("wu-123"), ...),
            EvidenceItem(id=UUID("evidence-2"), workunit_id=UUID("wu-123"), ...)
        ],
        UUID("wu-456"): [
            # Evidence items for WorkUnit wu-456 (if any passed quality check)
            # May be empty if all evidence was filtered out
        ]
    },
    execution_stats=PathStats(
        path_id="P2",
        execution_time_ms=15000.0,
        evidence_count=2,  # After quality filtering
        success=True
    ),
    success=True
)
```

## 📊 **Data Type Summary**

### **Core Data Types Used:**

1. **`ReactorState`** - Main state container
   - Contains: `workunits: List[WorkUnit]`, `evidences: List[EvidenceItem]`
   - Flows through: M5 input → M5 output → M4 input → M4 output

2. **`EvidenceItem`** - Individual evidence pieces
   ```python
   class EvidenceItem(BaseModel):
       id: UUID                    # Unique evidence ID
       workunit_id: UUID          # Links to originating WorkUnit
       user_id: UUID              # User context
       conversation_id: UUID      # Conversation context
       content: str               # Main evidence text
       title: Optional[str]       # Evidence title
       score_raw: Optional[float] # Retrieval relevance score
       provenance: Provenance     # Source information
   ```

3. **`Provenance`** - Source tracking
   ```python
   class Provenance(BaseModel):
       source_type: SourceType    # "web", "document", etc.
       source_id: str            # URL or document ID
       url: Optional[str]        # Source URL
       retrieval_path: str       # "P2" for M5
       router_decision_id: UUID  # Links to routing decision
   ```

4. **`QualityAssessment`** - M4 quality evaluation
   ```python
   class QualityAssessment(BaseModel):
       evidence_id: UUID
       relevance_score: float     # 0.0 - 1.0
       credibility_score: float   # 0.0 - 1.0
       overall_score: float       # 0.0 - 1.0
       should_keep: bool         # Filter decision
   ```

5. **`PathExecutionResult`** - Final path results
   ```python
   class PathExecutionResult(BaseModel):
       path_id: str                                    # "P2"
       workunit_results: Dict[UUID, List[EvidenceItem]]  # Results by WorkUnit
       execution_stats: PathStats                      # Performance metrics
       success: bool                                   # Success flag
   ```

## 🎯 **Where Data Ends Up**

After P2 → M5 → M4 processing:

1. **In ReactorState.evidences**: Filtered, high-quality `EvidenceItem` objects
2. **In PathExecutionResult.workunit_results**: Evidence grouped by WorkUnit ID
3. **In main ReactorState**: All evidence from all paths gets aggregated
4. **Next destination**: M7 Evidence Aggregator for final processing

## 🔍 **Data Persistence Locations**

```python
# 1. During processing - in ReactorState
state.evidences: List[EvidenceItem]

# 2. Path results - in PathExecutionResult  
result.workunit_results: Dict[UUID, List[EvidenceItem]]

# 3. Final aggregation - back in main ReactorState
main_state.evidences: List[EvidenceItem]  # From all paths

# 4. Quality metadata - in ReactorState
state.rqc_results: Dict[str, Any]  # M4 quality check results
```

The retrieval data maintains its structure as `EvidenceItem` objects throughout the entire flow, with each piece of evidence maintaining its link to the originating `WorkUnit` via the `workunit_id` field.