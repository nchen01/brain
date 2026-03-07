# Design Document

## Overview

The QueryReactor system implements a sophisticated question-answering pipeline using LangGraph for workflow orchestration and PydanticAI for data modeling. The system processes user queries through a graph-based workflow with specialized modules for query processing, multi-path retrieval, evidence aggregation, and answer generation. The architecture supports concurrent multi-user operations with full traceability and configurable behavior.

## Architecture

### Core Framework Stack

- **LangGraph**: Orchestrates the workflow as a directed graph with nodes representing processing modules and edges defining control flow
- **PydanticAI**: Provides type-safe data models and agent integration with automatic validation
- **Python 3.13**: Runtime environment with async capabilities for concurrent processing
- **OpenTelemetry**: Distributed tracing for end-to-end observability

### High-Level System Flow

```
User Query → [M0] QA with Human → [M1] Query Preprocessor → [M2] Query Router
                                                                    ↓
[P1] Simple Retrieval ← → [P2] Internet Retrieval ← → [P3] Multi-Hop Retrieval
         ↓                           ↓                           ↓
[M4] Quality Check → [M7] Evidence Aggregator ← [M4] Quality Check ← [M4] Quality Check
                                ↓
[M8] ReRanker → [M9] Smart Controller → [M10] Answer Creator → [M11] Answer Check → [M12] Interaction Answer
                        ↑                                              ↓
                   Loop Back                                    Loop Back
```

### Module Architecture

The system consists of 13 specialized modules organized into processing stages:

**Query Processing Stage:**
- M0: QA with Human (Interactive clarification)
- M1: Query Preprocessor (Normalization and decomposition)
- M2: Query Router (Path selection)

**Retrieval Stage (Parallel Paths):**
- P1: Simple Retrieval (M3 + M4) - Internal databases
- P2: Internet Retrieval (M5 + M4) - Web search and APIs  
- P3: Multi-Hop Retrieval (M6 + M4) - Complex reasoning

**Aggregation and Answer Stage:**
- M7: Evidence Aggregator (Merge and deduplicate)
- M8: ReRanker (Relevance scoring)
- M9: Smart Controller (Flow control decisions)
- M10: Answer Creator (Generate response)
- M11: Answer Check (Verification)
- M12: Interaction Answer (User delivery)

## Components and Interfaces

### Data Models (Pydantic-based)

**Core Identity Types:**
```python
UserQuery: Contains user_id, conversation_id, query_id, text, timestamp, trace info
WorkUnit: Represents query or sub-question with hierarchical linkage
EvidenceItem: Retrieved content with provenance and scoring metadata
RankedEvidence: Evidence after reranker processing with relevance scores
Answer: Final response with citations and confidence metrics
ReactorState: LangGraph shared state for workflow coordination
```

**Multi-Tenancy Support:**
- All data models include user_id and conversation_id for isolation
- UUID-based identifiers ensure uniqueness across concurrent sessions
- TraceInfo propagates OpenTelemetry context throughout pipeline###
 Configuration Management

**External Configuration Files:**
- `config.md`: Model assignments, thresholds, loop limits, data source endpoints
- `prompts.md`: Centralized system and agent prompts with version control
- `.env`: Sensitive credentials and API keys (excluded from version control)
- `.env.example`: Template for required environment variables

**Configuration Loading:**
- Runtime configuration loading without code changes
- Hierarchical configuration with environment-specific overrides
- Model selection per module (e.g., cfg.ac.compose_model = "gpt-4")

### State Management ([S0])

**Global State Components:**
- Conversation history (last N turns with configurable retention)
- WorkUnit tracking with UUID registry
- Loop counters with configurable limits to prevent infinite cycles
- Evidence collections indexed by WorkUnit ID
- Request tracing and instrumentation data

**Memory Management:**
- Short-term: In-memory state per request session
- Long-term: Persistent conversation history across sessions
- Context injection controlled by feature flags (cfg.memory.enable_in_m0/m1)

### Retrieval Path Design

**Path P1 - Simple Retrieval:**
- M3 (SimpleRetrieval): Queries internal databases/knowledge bases
- Supports multiple concurrent data sources with configurable limits
- Returns EvidenceItems with native relevance scores and provenance

**Path P2 - Internet Retrieval:**
- M5 (InternetRetrieval): Web search APIs and external data sources
- Domain filtering and content age restrictions for quality control
- Handles rate limiting and API failure gracefully

**Path P3 - Multi-Hop Retrieval:**
- M6 (MultiHopOrchestrator): Iterative reasoning with intermediate queries
- Configurable hop limits and branching factors
- Uses other retrieval modules internally for each hop

**Common Quality Control:**
- M4 (RetrievalQualityCheck): Validates relevance, filters low-quality results
- Configurable thresholds for content quality and query overlap
- Returns structured success/failure signals with diagnostic information

## Data Models

### Core Data Contracts

**UserQuery Model:**
```python
class UserQuery(BaseModel):
    user_id: UUID                    # Multi-tenant isolation
    conversation_id: UUID            # Session grouping
    id: UUID                        # Unique query identifier
    request_id: Optional[str]       # Idempotency key
    text: str                       # Query content
    locale: Optional[str]           # Language/region
    timestamp: EpochMs              # UNIX epoch milliseconds
    trace: Optional[TraceInfo]      # OpenTelemetry context
    context: Optional[ContextBundle] # History and metadata
```

**EvidenceItem Model:**
```python
class EvidenceItem(BaseModel):
    id: UUID                        # Unique evidence identifier
    workunit_id: UUID              # Links to originating query
    user_id: UUID                  # Tenant isolation
    conversation_id: UUID          # Session context
    content: str                   # Evidence text/data
    title: Optional[str]           # Document title
    score_raw: Optional[Score]     # Original retrieval score
    provenance: Provenance         # Source metadata
```

**Provenance Tracking:**
```python
class Provenance(BaseModel):
    source_type: SourceType        # db/web/api classification
    source_id: str                 # Source identifier
    url: Optional[str]             # Web URL if applicable
    retrieved_at: EpochMs          # Retrieval timestamp
    retrieval_path: str            # Path identifier (P1/P2/P3)
    router_decision_id: UUID       # Links to routing decision
    authority_score: Optional[Confidence] # Source reliability
```

### State Management Model

**ReactorState (LangGraph):**
```python
class ReactorState(BaseModel):
    original_query: UserQuery                           # Initial request
    workunits: List[WorkUnit]                          # Query decomposition  
    evidences: List[EvidenceItem]                      # Raw evidence
    ranked_evidence: Dict[UUID, List[RankedEvidence]]  # Post-ranking
    partial_answers: Optional[List[Answer]]            # Intermediate results
    final_answer: Optional[Answer]                     # Verified response
    cfg: Optional[Dict[str, object]]                   # Runtime config snapshot
    
    # State management components from [S0]
    history: List[HistoryTurn]                         # Conversation history
    loop_counters: Dict[str, int]                      # Loop prevention tracking
    router_stats: Optional[Dict[str, object]]          # Path statistics
    request_index: Optional[str]                       # Tracing identifier
```

**Loop Counter Management:**
- `smartretrieval_to_qp`: M9 → M1 query refinement loops
- `answercheck_to_ac`: M11 → M10 answer regeneration loops  
- `answercheck_to_qp`: M11 → M1 query reformulation loops
- Reset to 0 when entering M1 for first time in session
- Configurable limits via cfg.loop.max.* prevent infinite cycles

## Error Handling

### Loop Prevention and Control

**Loop Counter Management:**
- `smartretrieval_to_qp`: M9 → M1 refinement loops
- `answercheck_to_ac`: M11 → M10 regeneration loops  
- `answercheck_to_qp`: M11 → M1 reformulation loops
- Configurable maximum attempts per loop type
- Graceful termination when limits exceeded

**Failure Modes and Recovery:**
- Insufficient evidence: Graceful termination with explanatory message
- Retrieval timeouts: Continue with available evidence from other paths
- Verification failures: Attempt regeneration up to configured limits
- API failures: Fallback to alternative retrieval paths when possible

### Quality Assurance

**Evidence Validation:**
- Relevance thresholds for filtering low-quality results
- Content coherence checks to eliminate fragmented snippets
- Duplicate detection and elimination across retrieval paths
- Source reliability scoring for web-based evidence

**Answer Verification:**
- Citation accuracy validation against source evidence
- Hallucination detection through fact-checking against evidence
- Completeness verification ensuring all claims are supported
- Confidence scoring based on evidence quality and coverage## T
esting Strategy

### Unit Testing Approach

**Module-Level Testing:**
- Each module (M0-M12) tested in isolation with mocked dependencies
- Pydantic model validation testing for all data contracts
- Configuration loading and parameter validation tests
- Loop counter and state management verification

**Test Data Strategy:**
- Fixed prompt templates and mock LLM responses for consistent testing
- Predefined evidence sets for aggregation and ranking tests
- Sample queries covering various complexity levels and edge cases
- Mock external API responses for internet retrieval testing

### Integration Testing

**Workflow Testing:**
- End-to-end pipeline tests with stubbed retrieval results
- Multi-path retrieval coordination and timing tests
- Loop behavior validation under various evidence scenarios
- State consistency verification across module transitions

**Concurrency Testing:**
- Multi-user session isolation verification
- Parallel retrieval path execution testing
- Thread-safety validation for shared state components
- Performance testing under concurrent load

### Version 1.0 Implementation Strategy

**Dummy Module Implementation (Per Technical Specification):**
- **Retrieval Paths (P1, P2, P3)**: Implemented as placeholder modules that return pre-defined, hard-coded EvidenceItem objects or negative signals (RQC status like `NO_EVIDENCE_FOUND`)
- **ReRanker (M8)**: Simple non-ML heuristic (basic keyword match or pass-through ordering) with placeholder rr_score assignment
- **Common Output Interface**: All paths must produce either EvidenceItem objects or structured negative signals for consistent downstream processing
- **Primary Purpose**: Provide stable interface for developing and testing aggregator and connected modules

**Version 1.1 Full Implementation:**
- Replace dummy retrieval logic with actual data source connections and queries
- Implement configurable learning-to-rank model for ReRanker (cfg.rr.model_name)
- Add meaningful relevance scoring and top-K selection (cfg.rr.top_k)
- Production-ready performance optimizations and error handling

### Deployment Considerations

**Service Architecture:**
- FastAPI-based REST service for query processing endpoints
- Async request handling for improved concurrent user support
- Health check endpoints for monitoring and load balancing
- Graceful shutdown handling for in-flight request completion

**Monitoring and Observability:**
- Structured logging with request correlation IDs
- OpenTelemetry integration for distributed tracing
- Performance metrics collection (response times, success rates)
- Error rate monitoring and alerting capabilities

**Security Measures:**
- Input validation and sanitization for user queries
- Rate limiting to prevent abuse and resource exhaustion
- Secure credential management with environment variable isolation
- Content filtering for potentially harmful or inappropriate queries

### Scalability Design

**Horizontal Scaling:**
- Stateless service design enabling multiple instance deployment
- Load balancer compatibility with session affinity if needed
- Database connection pooling for efficient resource utilization
- Caching strategies for frequently accessed configuration and prompts

**Performance Optimization:**
- Parallel retrieval execution to minimize total response time
- Configurable timeouts to prevent slow queries from blocking resources
- Evidence caching for repeated similar queries (future enhancement)
- Efficient data serialization and memory management

This design provides a robust foundation for implementing the QueryReactor system with clear separation of concerns, comprehensive error handling, and scalable architecture suitable for production deployment.
### Det
ailed Module Specifications (Per Technical Specification)

**Module Nomenclature and Codes:**
- [DB]: External Databases/Knowledge Bases
- [S0]: Global State (in-memory + optional persistent store)
- [M0]: QA with Human (interactive clarification)
- [M1]: Query Preprocessor (normalization, decomposition)
- [M2]: Query Router (path selection)
- [M3]: SimpleRetrieval (internal database lookup)
- [M4]: RetrievalQualityCheck (validation, used across paths)
- [M5]: InternetRetrieval (web search, external APIs)
- [M6]: MultiHopOrchestrator (iterative reasoning)
- [M7]: Evidence Aggregator (merge, deduplicate)
- [M8]: ReRanker (relevance scoring)
- [M9]: SmartRetrieval Controller (flow decisions)
- [M10]: AnswerCreator (response generation)
- [M11]: AnswerCheck (verification)
- [M12]: InteractionAnswer (user delivery)

**Key Module Behaviors:**

**M0 - QA with Human:**
- Interactive clarification until confidence ≥ cfg.qa.min_conf
- History injection controlled by cfg.memory.enable_in_m0
- Max cfg.qa.max_turns clarification questions
- Output: ClarifiedQuery + ContextBundle

**M1 - Query Preprocessor:**
- Normalization: clean formatting, resolve references
- Decomposition: split complex queries if cfg.qp.enable_decomposition enabled
- WorkUnit creation with UUID tracking in [S0].workunits
- Loop limit: cfg.qp.max_rounds for refinement attempts
- Reference resolution using history if cfg.memory.enable_in_m1 enabled

**M2 - Query Router:**
- Route WorkUnits to P1 (internal), P2 (web), P3 (multi-hop) based on characteristics
- Parallel routing up to cfg.router.max_parallel_paths
- Each decision logged with router_decision_id for provenance
- Timeout handling via cfg.router.timeout_ms

**M4 - RetrievalQualityCheck (Common):**
- Relevance filtering: cfg.rqc.min_score threshold
- Content quality validation and overlap checking
- Returns RQCResult: {status: 'ok', items: [...]} or {status: 'no_fit', reason: ...}
- Reasons: 'not_found', 'low_overlap', 'low_quality'

**M7 - Evidence Aggregator:**
- Deduplication based on cfg.ea.dedup_threshold similarity
- Merge strategy controlled by cfg.ea.merge_strategy
- Preserve full provenance from all paths
- Unified EvidenceSet output per WorkUnit

**M8 - ReRanker:**
- Model specified by cfg.rr.model_name
- Top-K selection via cfg.rr.top_k
- Assigns rr_score and rank to create RankedEvidence
- V1.0: Simple heuristics, V1.1: ML models

**M9 - SmartRetrieval Controller:**
- Decision outcomes: AnswerReady, NeedsBetterDecomposition, InsufficientEvidence
- Confidence threshold: cfg.smr.min_confidence
- Loop management with cfg.loop.max.smartretrieval_to_qp limit
- Graceful termination for insufficient evidence

**M10 - AnswerCreator:**
- LLM model: cfg.ac.compose_model
- Strict evidence-only policy (no hallucination)
- Partial answers controlled by cfg.ac.allow_partial_answer
- Citation mapping to evidence IDs with optional span indices

**M11 - AnswerCheck:**
- Fact verification against evidence sources
- Citation accuracy validation
- Loop limits: cfg.ack.max_loops for regeneration attempts
- Provenance trustworthiness checking

### RQC Result Interface

**Structured Quality Check Output:**
```python
type RQCResult = Union[
    {"status": "ok", "items": List[EvidenceItem]},
    {"status": "no_fit", "reason": Literal["not_found", "low_overlap", "low_quality"], "diagnostics": Optional[Any]}
]
```

This ensures consistent downstream processing regardless of retrieval path success or failure.