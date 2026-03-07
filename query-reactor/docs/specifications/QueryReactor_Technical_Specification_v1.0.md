# Query Reactor – Technical Specification v1.0

**Purpose:** To design a production-ready, modular smart query and question-answering (QA) system that routes user questions across multiple retrieval paths, aggregates evidence with provenance, and generates verifiable answers. This specification refines the initial draft (v0.01) and adds required details for implementation.

## Model Configuration

* **External Config File (config.md):** All model assignments and key configuration settings will reside in a separate config.md file (or similar). This avoids hard-coding model names or parameters in code and allows easy review/modification of which AI models are used for different agents or modules.

* **System Variables:** Any system constants or thresholds (e.g. confidence cutoffs, max loop counts) should be defined in config.md. The application will load these at runtime, so adjustments do not require code changes.

* **Data Source and Service Endpoint Management:** The configuration file will explicitly define all external data dependencies. This includes specifying which databases to use for data retrieval and defining the API endpoints for external services, such as internet search providers.

* **Example Config Entries:** For instance, config.md may specify the model name for the Answer Creator (e.g. AC.model = gpt-4), the minimum confidence for QA with Human (e.g. qa.min_conf = 0.8), or loop limits (e.g. loop.max.smartretrieval_to_qp = 1). All modules will reference these settings via a central config loader.

This approach ensures that model choices and tuning parameters are transparent and easily tunable by developers or operators without altering the code.

## Prompt Management

* **Centralized Prompt File (prompts.md):** All system and agent prompts will be stored in a dedicated prompts.md (or similar) file. Each agent/module’s behavior, such as system instructions or template prompts, is defined and labeled clearly in this file.

* **Editable Agent Instructions:** By externalizing prompts, developers and prompt designers can adjust the tone, role instructions, or few-shot examples for each agent (module) in one place. For example, the system prompt for the Query Router agent or the Answer Creator can be edited in prompts.md without digging into code.

* **Mapping in Config:** The config.md may reference which prompt from prompts.md to use for each module (by key or section). This separation of concerns makes it easier to iterate on prompt engineering and maintain consistency across the system.

Storing prompts externally also aids version control of prompt changes and allows non-engineers to contribute to refining agent behaviors.

## Secure Credential and Environment Management

* **Environment Variable File (.env):** All sensitive information, including API keys, database passwords, model access tokens, and other confidential credentials, must be stored in a .env file located in the project's root directory. This file is for local development and must be excluded from version control (e.g., listed in .gitignore) to prevent accidental exposure.

* **Codebase Policy:** It is strictly prohibited to hard-code any sensitive values directly within the application's source code. The application must load these credentials from environment variables at runtime.

* **Template for Configuration (.env.example):** A template file named .env.example will be included in the repository. This file will list all necessary environment variables with placeholder or empty values. Users will be instructed to copy this file to .env and populate it with their actual credentials to set up their environment.

## Architecture Overview

The Query Reactor system is composed of multiple specialized modules (agents and utility components) orchestrated in a graph-like workflow. We leverage the **LangGraph** framework for workflow orchestration and **PydanticAI** for data modeling and agent integration:

* **LangGraph Orchestration:** The modules are arranged as nodes in a directed graph workflow (not strictly linear). This allows parallel retrieval paths and looping flows (for clarification or decomposition) without data races. LangGraph models the agent workflow as an explicit state machine where each step is a node and edges define control flow. This gives fine-grained control over execution order, supports cycles (loops) and parallelism in the query processing pipeline.

* **PydanticAI for Data Models:** All data passed between modules (queries, work units, evidence, answers, etc.) are defined as Pydantic models (Python 3.13 environment). PydanticAI brings type safety and validation to AI agent development, treating agents’ inputs/outputs as strongly-typed Python objects. This ensures each module receives the expected fields (with automatic validation) and produces outputs that conform to the specified schema. It also simplifies dependency injection and structured output handling within agents.

* **Concurrent Multi-User Support:** The system is designed to operate as a fully concurrent, multi-tenant service capable of handling multiple users and conversations in parallel without state interference or data leakage. Each user interaction is isolated and traceable through a structured set of unique identifiers:

- User UUID: A globally unique identifier assigned to each user. Used to partition data, enforce access control, and support multi-tenant operation.

- Conversation UUID: Identifies a specific dialogue session for a given user. This allows continuity across multiple queries within the same conversation context.

- Query UUID: Represents a single top-level user request within a conversation. Every query spawns its own isolated workflow instance with independent state and execution trace.

- Sub-query UUIDs: Within a single query, the system may decompose the request into multiple sub-queries for parallel execution. These share the same user and conversation context but operate as independent, concurrent tasks under the same query identifier.

Each query instance runs as a self-contained workflow within the LangGraph orchestration framework, ensuring that concurrent executions do not interfere with each other. The framework maintains explicit state machines and thread-safe merging strategies, allowing parallel and cyclic data flows without race conditions. All data objects exchanged between modules—such as queries, evidence, and answers—are strongly typed and validated using PydanticAI, guaranteeing schema consistency and isolation between concurrent sessions.

A unique request ID (derived from the query UUID) is propagated throughout the entire execution pipeline for observability, traceability, and distributed logging. This enables the system to safely scale horizontally, support concurrent sessions across multiple users, and provide deterministic, replayable query execution in a multi-user API environment.

* **Environment:** Implement in Python 3.13. Use a managed virtual environment (e.g. using venv or similar, possibly managed by internal tools) to ensure dependency consistency. (No specific deployment instructions are included here, as internal developers are already familiar with the environment setup.)

## Nomenclature and Module Codes

For clarity in discussion and logging, each major component is assigned a short code. These codes will be used in diagrams, logs, and configuration keys:

* **[DB]:** External Databases / Knowledge Bases (external data sources the system can query, existing outside the QA system).

* **[S0]:** Global State (in-memory state + optional persistent store for the current session/request).

* **[M0]:** *QA with Human* – an interactive clarification module (if needed, to clarify user query).

* **[M1]:** *Query Preprocessor (QP)* – normalizes and possibly decomposes the query.

* **[M2]:** *Query Router (QR)* – routes the query or subqueries to appropriate retrieval paths.

* **[P1]:** *Simple Retrieval path* – a retrieval path targeting internal databases/indices.

* **[M3]:** *SimpleRetrieval (SR)* – executes simple knowledge base or database lookup.

* **[M4]:** *RetrievalQualityCheck (RQC)* – validates retrieval results (used in multiple paths).

* **[P2]:** *Internet Retrieval path* – a retrieval path using web search or external APIs.

* **[M5]:** *InternetRetrieval (IR)* – performs web searches and retrieves online content.

* **[M4]:** *RetrievalQualityCheck (RQC)* – validates web retrieval results (same module type as above).

* **[P3]:** *Multi-Hop Retrieval path* (a.k.a. complex reasoning path) – for stepwise, iterative query answering.

* **[M6]:** *MultiHopOrchestrator (MHO)* – orchestrates multi-step retrieval (chain of sub-queries).

* **[M4]:** *RetrievalQualityCheck (RQC)* – validates each hop’s results and the final combined results.

* **[M7]:** *Evidence Aggregator (EA)* – merges and deduplicates evidence from all paths.

* **[M8]:** *ReRanker (RR)* – re-ranks the collected evidence based on relevance.

* **[M9]:** *SmartRetrieval Controller (SMR)* – decides if the system is ready to answer or needs to loop/refine.

* **[M10]:** *AnswerCreator (AC)* – composes the final answer from evidence.

* **[M11]:** *AnswerCheck (ACK)* – verifies the answer against evidence (with possible corrective loops).

* **[M12]:** *InteractionAnswer (IA)* – delivers the answer (with citations) back to the user.

These codes in brackets (e.g., [M3], [P2]) will be used in logs and trace outputs to identify modules and paths.

## High-Level Workflow

The system operates in a sequence of stages, with conditional loops and parallel branches as needed. Below is the end-to-end flow of a user query through Query Reactor:

**User Query Ingestion → [M0] QA with Human:**  
   The user’s query is received as a **UserQuery** object. Module M0 checks the query for clarity. If the query is ambiguous or unclear, M0 engages in interactive clarification with the user (e.g., asking follow-up questions) until the system’s understanding confidence ≥ cfg.qa.min_conf. This ensures the query is well-specified.

- *History Injection:* If configured, M0 can prepend recent dialogue history (last N user-assistant turns) into the context to help interpret pronouns or context-dependent questions (controlled by cfg.memory.enable_in_m0).

- **Output:** A refined **ClarifiedQuery** (may be identical to original if no clarification needed), along with a **ContextBundle** containing any relevant context (e.g. conversation history or user metadata).

**[M1] Query Preprocessor (QP):**  
   M1 takes the ClarifiedQuery and prepares it for retrieval. Responsibilities include:

- **Normalization:** Clean up formatting, standardize casing/punctuation, and resolve references (e.g. if the user said "in the previous answer" or used pronouns, use the history context to clarify those references if cfg.memory.enable_in_m1 is true).

- **Decomposition:** Decide if the query should be split into multiple sub-questions. If the query is complex or multi-faceted and cfg.qp.enable_decomposition is enabled, M1 uses heuristics or an LLM to break it into smaller, answerable **SubQuestions**. (E.g., a complex query asking for a comparison may be split into two factual sub-queries and then a comparison step.)

- M1 then wraps the original query (or each sub-question) into a **WorkUnit** data structure. Each WorkUnit gets a new UUID and retains a reference to the original UserQuery ID. All WorkUnit IDs are registered in the global state [S0].workunits for tracking.

- The original query text is appended to the [S0].history log (persistent conversation record).

- **Output:** An array of **WorkUnits[]** (one for each sub-question, or just one containing the original query if no decomposition). These WorkUnits are passed to M2.

*Loop Note:* M1 can be invoked multiple times if the SmartRetrieval controller (M9) later decides the query needs to be reformulated or further decomposed. A config cfg.qp.max_rounds limits how many times we can loop back into query preprocessing to refine sub-questions.

**[M2] Query Router (QR):**  
   M2 examines each WorkUnit and decides which retrieval path(s) are most likely to yield answers:

- It can route a WorkUnit to one or more of the retrieval paths [P1], [P2], [P3] in parallel (fan-out) depending on query characteristics. For example:

   * Choose **[P1] (Simple Retrieval)** if the query likely can be answered from internal databases or knowledge base (e.g., query mentions a known domain or entity present in structured data).

   * Choose **[P2] (Internet/Web Retrieval)** if the query is about a very recent event or broad information not in internal data, or if [P1] yields nothing relevant.

   * Choose **[P3] (Multi-hop)** if the query requires reasoning through multiple steps or combining information (e.g., a complex question needing intermediate answers).

- The router’s decision may send a copy of the WorkUnit to multiple paths simultaneously for comprehensive coverage, up to cfg.router.max_parallel_paths paths (to balance load).

- Each routing decision is logged with a router_decision_id (UUID) to tie the WorkUnit to the chosen path(s) and for provenance tracking.

- **Output:** A **RoutePlan** describing where each WorkUnit went. The WorkUnits are forwarded into the respective path modules (M3/M5/M6 as appropriate).


**Retrieval Paths [P1]/[P2]/[P3]:** The WorkUnits are processed in parallel along the selected path(s):

- **Common Output Interface:** Each path, regardless of its implementation stage, must adhere to a common output interface. It will produce either a set of **EvidenceItem** objects (containing content and its source) or a structured **negative signal** (an RQC status indicating the reason for failure, e.g., `NO_EVIDENCE_FOUND`). This ensures that downstream components like the aggregator can process results consistently.

- **Version 1.0 (Dummy Implementation):** For the initial release, the Retrieval Paths will be implemented as **placeholder (dummy) modules**. They will **not** perform actual data retrieval. Instead, they will return pre-defined, hard-coded `EvidenceItem` objects or negative signals. The primary purpose is to provide a stable interface for developing and testing the aggregator and other connected modules.

- **Version 1.1 (Full Implementation):** The full, functional data retrieval logic for each path will be developed in a subsequent release. At that point, the dummy modules from v1.0 will be replaced with code that connects to and queries the actual data sources.

**[M7] Evidence Aggregator (EA):**  
   Module M7 collects results from all paths for each WorkUnit:

- It merges the EvidenceItems from different paths, ensuring a unified format/schema. Any duplicate evidence (e.g., the same document snippet retrieved from two sources) is deduplicated based on content similarity (threshold configurable via cfg.ea.dedup_threshold).

- The aggregator also preserves provenance details and source information for each evidence piece. If some paths returned a "no_fit" signal, the aggregator notes that those paths found nothing, but the workflow continues with whatever evidence is available from other paths.

- The merged evidence set is stored or updated in [S0] state for that WorkUnit (to be used by the reranker and answer generator).

- **Output:** A unified **EvidenceSet** per WorkUnit, containing all validated evidence items.

**[M8] ReRanker (RR):**  
    M8 re-ranks the aggregated evidence to prioritize the most relevant information for answering the **original user query**.

-   **Version 1.0 (Dummy Implementation):** For the initial release, the ReRanker will be a placeholder module. It will implement a simple, non-ML heuristic, such as a basic keyword match or even just passing the evidence through in its original order. It will assign a placeholder **rr_score** to each evidence item. The primary goal is to provide a correctly structured output (`state.ranked_evidence`) to unblock the development and testing of downstream modules like the Answer Creator.

-   **Version 1.1 (Full Implementation):** This version will replace the dummy logic with a configurable learning-to-rank model or an advanced heuristic (defined by `cfg.rr.model_name`). This model will compute a meaningful relevance score (**rr_score**) for each evidence item against the original user query. The top-K items, determined by `cfg.rr.top_k`, will be selected as the primary evidence, while lower-ranked items can be marked as secondary, focusing the answer generation process on the most pertinent facts.

**[M9] SmartRetrieval Controller (SMR):**  
    M9 analyzes the evidence and decides how to proceed. It considers the completeness and confidence of the retrieved evidence for answering the user’s query:

- If sufficient evidence is gathered and the system is confident, **AnswerReady** is signaled (confidence ≥ cfg.smr.min_confidence). The process moves forward to answer generation (M10).

- If the evidence seems insufficient or the query might need to be broken down further, **NeedsBetterDecomposition** is signaled. In this case, M9 will loop back to [M1] Query Preprocessor, possibly with instructions to refine the question or break it down differently. (For example, if one sub-question got no good evidence, the system might try to reformulate that sub-question.) The global state’s loop counter for this route is incremented (loop_counters.smartretrieval_to_qp), and if the loop count exceeds cfg.loop.max.smartretrieval_to_qp, the loop is aborted to avoid infinite cycles.

- If after retrieval (and possibly multiple attempts) there is still **InsufficientEvidence** to answer (e.g., all paths returned nothing useful, or evidence is too weak), M9 can decide to terminate gracefully. In such a case, the system would produce a fallback answer indicating that no answer could be found in the knowledge sources, rather than hallucinating an answer.

- **Output:** A directive of what to do next: either proceed to answer creation, or loop back to query preprocessing, or terminate with a “no answer found” outcome.

**[M10] AnswerCreator (AC):**  
    When ready to answer, M10 composes a draft answer using the collected evidence:

- It takes into account the **UserQuery** (original question), the context (e.g., conversation history for tone or follow-up context), the breakdown into WorkUnits (sub-questions), and all the top evidence for each WorkUnit.

- **Strict Use of Evidence:** The AC must **only use facts from the provided EvidenceItems** to construct the answer. It should not inject any external information or assumptions not backed by evidence. This ensures verifiability.

- **Answer Composition:** AC uses an LLM (language model) specified by cfg.ac.compose_model to generate a well-structured answer. It will weave together information from multiple evidence pieces if needed and cite them. The output is an **Answer** object that includes:

    * text: The answer text, formulated clearly for the user.

    * citations: A list of citations mapping portions of the answer to the evidence item IDs (with optional span indices if we pinpoint which part of evidence supports which part of the answer).

    * limitations (optional): Any disclaimers or notes about the answer’s scope or confidence (e.g., if part of the question couldn’t be answered fully).

- **Handling Missing Evidence:** If any WorkUnit ended up with no approved evidence (e.g., a sub-question could not be answered from the retrieved data), the AnswerCreator will **not fabricate an answer** for that portion. Depending on policy, two approaches:

    * If cfg.ac.allow_partial_answer is true, AC may still provide an answer for the parts it has evidence for, and explicitly note which aspect couldn’t be answered due to insufficient information.

    * If partial answers are not allowed or the question’s main point can’t be answered, AC produces an output indicating that it lacks sufficient evidence to answer completely (an **insufficient_evidence** outcome in the Answer draft, possibly with a message like "Sorry, I couldn’t find enough information to answer that question.").

- The draft answer is then passed on to verification. (If the answer is marked insufficient_evidence, the next module can decide to finalize that as the response or trigger a different fallback.)

**[M11] AnswerCheck (ACK):**  
    M11 validates the draft answer to ensure it is fully supported by the evidence:

- **Fact Verification:** It checks each claim or sentence in the answer against the EvidenceItems and their sources. Every factual statement in the answer should have at least one citation pointing to supporting evidence. If any part of the answer cannot be traced to provided evidence, or if the answer includes unsupported content, this is flagged.

- **Provenance Check:** For each citation, ensure the cited evidence indeed supports the claim in context and that the provenance (source) is trustworthy per system standards.

- If the answer fails verification (e.g., contains a claim with no evidence or a misinterpretation of evidence), the system will attempt to correct:

    * M11 can request a regeneration of the answer from M10 with stricter constraints or additional instructions (e.g., “ensure every sentence is backed by provided sources”). This triggers a loop back to AnswerCreator. The loop counter loop_counters.answercheck_to_ac is incremented. If it exceeds cfg.loop.max.answercheck_to_ac, the loop is stopped to avoid endless retries.

    * In more complex cases (e.g., evidence is insufficient or seems to answer a different question than asked), M11 might determine that the query needs reformulation. It can then route the process back to [M1] Query Preprocessor (incrementing loop_counters.answercheck_to_qp). For example, the system might try a different decomposition or search strategy on second attempt. This is a more expensive loop and also capped by cfg.loop.max.answercheck_to_qp.

- If all loops are exhausted or the answer cannot be fully supported, the system will either deliver the best possible partial answer with appropriate disclaimers or a polite statement of inability to answer.

- **Output:** A verified final Answer (if checks passed), or instructions to re-enter a module loop (with reasons).

**[M12] InteractionAnswer (IA):**  
    This is the final stage that interfaces with the user:

    * It takes the verified Answer from M11 and formats it for the user. This includes the answer text and the accompanying citations/provenance information. The answer might be delivered in a UI that shows footnotes or references for each citation.

    * M12 also logs the interaction outcome to telemetry: e.g., the final answer, which evidence was used, how long the process took, etc., to a log file or database. (All modules produce logs, but M12 ensures an end-of-query summary is logged.)

    * Optionally, if feedback is enabled (cfg.ia.enable_feedback), M12 could prompt the user for feedback on the answer or capture a rating, which could be stored for continuous improvement.

    * The conversation state can be updated here as well. For instance, a summary of the Q&A might be stored in long-term history if future queries from the user might refer back to this answer.

    * **Output:** The answer is presented to the user, completing the cycle. The system returns to idle waiting for the next user query (or next turn in conversation, if interactive).

Throughout this flow, the **Global State [S0]** is used to keep track of the conversation and processing state (detailed below). The design allows for modules M0–M12 to be thought of as a pipeline with possible loops. Using LangGraph, this pipeline is implemented as a graph where some nodes run in parallel ([P1]/[P2]/[P3]) and some edges create loops back to earlier nodes (for clarification or answer fixing), all while maintaining an orderly state.

## Data Contracts (Core Data Models)

This section defines the **Pydantic-based core data models** used throughout the Query Reactor system.
These models ensure **type safety**, **multi-user concurrency isolation**, and **end-to-end traceability** via `user_id`, `conversation_id`, and `TraceInfo`.

All timestamps are expressed in **UNIX epoch milliseconds**, and all models use `extra="forbid"` to prevent unvalidated fields.

---

### Core Principles

* **Multi-tenant isolation:** Every persisted record includes `user_id` and `conversation_id`.
* **Deterministic orchestration:** Each query, work unit, and evidence item is uniquely identified by a `UUID`.
* **Traceability:** OpenTelemetry-compatible tracing fields (`trace_id`, `span_id`) allow end-to-end observability.
* **Strong typing and validation:** Implemented with **Pydantic v2**, ensuring consistency between agents.
* **Extensible ranking:** Evidence objects carry ranking-friendly metadata for ReRanker (M8).

---

### Pydantic Model Definitions

```python
from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Annotated
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ---------- Common Types ----------

EpochMs = Annotated[int, Field(ge=0, description="UNIX epoch time in milliseconds")]
Score = Annotated[float, Field(description="Generic numerical score")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]

class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class SourceType(str, Enum):
    db = "db"
    web = "web"
    api = "api"

class TraceInfo(BaseModel):
    """Trace identifiers for observability (OpenTelemetry-compatible)."""
    model_config = ConfigDict(extra="forbid")
    trace_id: str
    span_id: Optional[str] = None


# ---------- Context & Query ----------

class HistoryTurn(BaseModel):
    """A single conversational turn used as context."""
    model_config = ConfigDict(extra="forbid")
    role: Role
    text: str
    timestamp: EpochMs
    locale: Optional[str] = None


class ContextBundle(BaseModel):
    """Optional user and conversation context."""
    model_config = ConfigDict(extra="forbid")
    history: Optional[List[HistoryTurn]] = None
    user_metadata: Optional[Dict[str, object]] = Field(
        default=None, description="User profile, preferences, or metadata"
    )


class UserQuery(BaseModel):
    """Top-level user request."""
    model_config = ConfigDict(extra="forbid")

    # Identity and tenancy
    user_id: UUID
    conversation_id: UUID
    id: UUID = Field(..., description="Unique query ID")
    request_id: Optional[str] = Field(
        default=None, description="Idempotency key (defaults to query ID if omitted)"
    )

    # Content
    text: str
    locale: Optional[str] = Field(None, description="e.g., 'en-US', 'zh-TW'")

    # Timing and tracing
    timestamp: EpochMs
    trace: Optional[TraceInfo] = None

    # Optional embedded context
    context: Optional[ContextBundle] = None


# ---------- Work Units (Query Decomposition) ----------

class WorkUnit(BaseModel):
    """A unit of work — the original query or a sub-question."""
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_query_id: UUID
    parent_workunit_id: Optional[UUID] = Field(None, description="Hierarchical linkage")
    text: str
    is_subquestion: bool
    locale: Optional[str] = None
    timestamp: EpochMs
    priority: Optional[int] = Field(
        None, description="Scheduler hint (lower = higher priority)"
    )
    features: Optional[Dict[str, object]] = None
    trace: Optional[TraceInfo] = None

    # Tenancy
    user_id: UUID
    conversation_id: UUID


# ---------- Evidence & Provenance ----------

class Provenance(BaseModel):
    """Metadata describing where an evidence item originated."""
    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source_id: str
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    retrieved_at: EpochMs
    retrieval_path: str = Field(..., description="Retrieval route identifier (e.g. 'P1')")
    router_decision_id: UUID

    # Ranking-related metadata
    authority_score: Optional[Confidence] = None
    published_at: Optional[EpochMs] = None
    language: Optional[str] = None


class EvidenceItem(BaseModel):
    """An evidence item (text snippet, record, or structured data)."""
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workunit_id: UUID
    user_id: UUID
    conversation_id: UUID
    content: str
    title: Optional[str] = None
    section_title: Optional[str] = None
    language: Optional[str] = None
    char_len: Optional[int] = Field(None, ge=0)
    tokens: Optional[int] = Field(None, ge=0)
    score_raw: Optional[Score] = Field(None, description="Retriever score before reranking")
    embeddings: Optional[List[float]] = Field(None, description="Optional embedding vector")
    provenance: Provenance

    @field_validator("char_len", mode="before")
    @classmethod
    def derive_length(cls, v, info):
        """Auto-derive character length from content if missing."""
        if v is None and (content := info.data.get("content")):
            return len(content)
        return v


class RankedEvidence(EvidenceItem):
    """Evidence after M8 ReRanker processing."""
    rr_score: Score = Field(..., description="ReRanker model score")
    rank: int = Field(..., ge=1, description="1-based rank within the WorkUnit")
    is_primary: bool = Field(..., description="True if within top-K for this WorkUnit")
    rationale: Optional[str] = Field(None, description="Explanation or justification text")


# ---------- Answers & Citations ----------

class Citation(BaseModel):
    """A link from an answer segment to a supporting evidence item."""
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID
    span: Optional[Tuple[int, int]] = Field(
        None, description="Character offset range [start, end) in answer text"
    )

    @field_validator("span")
    @classmethod
    def validate_span(cls, span):
        if span is None:
            return span
        start, end = span
        if start < 0 or end < 0 or end < start:
            raise ValueError("Citation span must satisfy 0 <= start <= end")
        return span


class Answer(BaseModel):
    """Final or partial answer returned to the user."""
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    conversation_id: UUID
    query_id: UUID
    workunit_id: Optional[UUID] = None
    text: str
    citations: List[Citation]
    limitations: Optional[List[str]] = None
    confidence: Optional[Confidence] = None
    locale: Optional[str] = None
    timestamp: EpochMs
    trace: Optional[TraceInfo] = None


# ---------- Reactor State (LangGraph Orchestration) ----------

class ReactorState(BaseModel):
    """Shared LangGraph state (append-only and deterministic)."""
    model_config = ConfigDict(extra="forbid")

    original_query: UserQuery
    workunits: List[WorkUnit] = Field(default_factory=list)
    evidences: List[EvidenceItem] = Field(default_factory=list)
    ranked_evidence: Dict[UUID, List[RankedEvidence]] = Field(default_factory=dict)
    partial_answers: Optional[List[Answer]] = None
    final_answer: Optional[Answer] = None
    cfg: Optional[Dict[str, object]] = Field(None, description="Runtime configuration snapshot")
```

---

### Model Guarantees and Invariants

| Category                      | Rule / Invariant                                                                                           |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Idempotency**               | `UserQuery.request_id` acts as an idempotency key (defaults to `id`).                                      |
| **Multi-tenancy**             | All persisted entities include `user_id` and `conversation_id` for access isolation.                       |
| **Traceability**              | `TraceInfo.trace_id` propagates through all submodules for end-to-end observability.                       |
| **Evidence Ranking**          | `RankedEvidence.is_primary == (rank <= cfg.rr.top_k)` at runtime.                                          |
| **Citation Integrity**        | Each `Citation.evidence_id` must reference a valid `EvidenceItem` or `RankedEvidence`.                     |
| **Deterministic State Merge** | Lists in `ReactorState` are append-only; merges must resolve by `(rr_score DESC, score_raw DESC, id ASC)`. |



**Retrieval Quality Check Result:** The RQC module (M4) returns a structured result indicating whether the retrieval output is acceptable or not. Its return type can be represented as:

type RQCResult =  
  | { status: 'ok'; items: EvidenceItem[] }   
  | { status: 'no_fit'; reason: 'not_found' | 'low_overlap' | 'low_quality'; diagnostics?: any };

* If status is 'ok', it will carry a list of EvidenceItem objects that passed the quality filters.

* If status is 'no_fit', the reason may clarify why the retrieval failed the check (e.g., nothing found, too little overlap with query, or generally low quality results). diagnostics can include additional info (e.g., scores or debug info) for logging or analysis.

These data contracts ensure each module communicates with a clear interface. They will be implemented as Pydantic models in code, allowing automatic validation and serialization. Developers should refer to these definitions when creating classes or schemas for the data.

## Memory and State Management ([S0])

Module [S0] represents the global state for the query processing session. It includes both transient in-memory data and any persistent storage as needed. Key aspects of state management:

* **Conversation History (Long-Term Memory):** The system can remember recent interaction history to provide context for follow-up questions. By default, the **last N turns** (question/answer pairs) can be included in the context. cfg.memory.last_n (default N = 5) controls how many recent turns to carry. The history turns are stored as an array of HistoryTurn in [S0].history.

* *History injection:* Controlled by config flags cfg.memory.enable_in_m0 and cfg.memory.enable_in_m1. These flags determine whether the history is supplied to M0 (clarification stage) and/or M1 (preprocessing). If enabled, the ContextBundle passed to those modules will include the last N turns from [S0].history.

* The history can be used to resolve references (e.g., pronouns or context-dependent queries) and to maintain conversational continuity.

* **Work Units Tracking:** As M1 generates WorkUnits for sub-questions, their IDs are stored in [S0].workunits (likely a list or dict of UUIDs to WorkUnit objects). This allows later modules to lookup all sub-questions of a query and ensure each has been handled. It also aids in re-aggregation of answers if needed.

* **Loop Counters and Control:** Because the system may loop back in the flow (for query refinement or answer re-checking), [S0] maintains counters to prevent infinite loops:

* On entering M1 (Query Preprocessor) for the first time in a session, all loop counters are **reset to 0**.

* There are separate counters for each type of loop:

  * loop_counters.smartretrieval_to_qp – counts how many times the SmartRetrieval (M9) has routed back to Query Preprocessor (M1) in this session.

  * loop_counters.answercheck_to_ac – counts how many times AnswerCheck (M11) requested AnswerCreator (M10) to regenerate the answer.

  * loop_counters.answercheck_to_qp – counts how many times AnswerCheck (M11) sent the flow back to Query Preprocessor (for query reformulation).

* Each counter has a maximum allowed value (from config cfg.loop.max.*). If a loop is about to exceed its limit, the system will stop looping:

  * For example, if smartretrieval_to_qp exceeds cfg.loop.max.smartretrieval_to_qp, the SmartRetrieval controller will not loop to M1 again. Instead, it might proceed to answer creation with whatever evidence is available or terminate if nothing found. In the state history or logs, the system should record that the loop cap was hit for transparency.

  * Similarly for answer verification loops: if the answer can’t be verified after the max retries, the system will break out (possibly delivering an answer with a note or a failure message rather than looping forever).

* The state may also snapshot the loop limits in a structure like [S0].loop_limits for reference at runtime (loaded from config at session start).

* **Stats and Traceability:** [S0] can hold instrumentation info such as:

* router_stats or path_stats to record which paths were taken, how long they took, how many results came from each, etc., for analytics or debugging.

* A request_index or ID to trace this request end-to-end (this could be the same as UserQuery.id or a separate incrementing ID for logging).

* **Persistence:** While most state is ephemeral per request, certain elements like the conversation history might be persisted across sessions (especially for chat applications with the same user). In an MVP, we might keep history in memory for the session. For a production system, [S0] could interface with a database or cache for long-term memory beyond the session lifecycle.

In summary, [S0] acts as a blackboard where modules can read/write common information (like history and work units) and check global conditions (like loop counts). It is crucial for coordinating the multi-step process and maintaining context, especially in iterative flows.

## Module Specifications

Below, each module [Mx] and path [Px] is described in terms of its input, responsibilities, key parameters (configurable behaviors), and outputs. The design is modular: each component has a single, well-defined purpose. Modules will be implemented either as agents (LLM-backed) or as procedural nodes using LangGraph’s flexible node definitions, and they communicate via the data models defined above.

### [M0] QA with Human (Clarification Interface)

**Role:** Interactive query clarification with the end-user (optional step at query start).

* **Input:** UserQuery (the raw user query) and an optional ContextBundle (which may include recent history if enabled).

* **Function:** If the user’s question is unclear or ambiguous, M0 engages the user in a quick Q&A to clarify the intent or specifics. For example, if the user asked "Tell me about Apple," M0 might ask "Do you mean Apple the company or the fruit?"  
  M0 uses an LLM to generate the clarification questions and interpret user responses. It continues this loop until the system’s understanding confidence is above a threshold.

* **Understanding Confidence:** A metric (0–1) representing how well the query is understood. This could be derived from the LLM’s own uncertainty or from heuristic rules (for instance, if multiple clarifications have converged on a specific interpretation, confidence is high). Config cfg.qa.min_conf defines the minimum confidence to proceed without further clarification.

* **Multi-turn Clarification:** M0 will ask at most cfg.qa.max_turns clarification questions. If the query remains unclear after that, it either proceeds with the best guess or politely refuses (depending on design).

* **Use of History:** If cfg.memory.enable_in_m0 is true, M0 will utilize recent conversation turns from ContextBundle.history to disambiguate the query (e.g., if the user’s query is follow-up like "What about its release date?", the context of what "it" refers to might be found in history).

* **Output:** A ClarifiedQuery object (which has similar structure to UserQuery but possibly refined text) and an updated ContextBundle. The ClarifiedQuery.text is what downstream modules (M1, etc.) will treat as the definitive question. The ContextBundle is passed along (potentially augmented with any new history turn representing the clarification dialogue that took place).

*Note:* M0 can be considered a human-in-the-loop step. In cases where Query Reactor is fully automated (no opportunity to ask the user follow-ups, e.g., in a single-turn QA setting), this module could be bypassed or operate in a self-clarification mode (the system attempts to reinterpret the query internally if ambiguous). But for interactive applications, M0 significantly improves query quality by ensuring the system addresses the correct user intent.

### [M1] Query Preprocessor (QP)

**Role:** Prepare and decompose the query for retrieval.

* **Input:** ClarifiedQuery (from M0, or directly the original query if M0 was skipped) and the ContextBundle (which may include history).

* **Responsibilities:**

* **Normalization:** Clean the query text (trim whitespace, unify encoding), standardize locale-specific content (e.g., convert full-width characters if needed for certain languages, ensure consistent date formats or units).

* **Reference Resolution:** If the query contains references like "the above" or pronouns like "he/she/it" and if conversation history is available (and cfg.memory.enable_in_m1 is true), replace or annotate those with the entities they refer to. For instance, "When was it released?" might be transformed into "When was *ProductX* released?" if history indicates the user was asking about *ProductX*.

* **Decomposition into Sub-Questions:** Check if the query is compound or complex. If cfg.qp.enable_decomposition is enabled and the query would be easier answered by breaking it down, generate sub-questions. This might involve using a reasoning LLM or rule-based approach (e.g., splitting on conjunctions asking different things). Each sub-question should be a stand-alone query that yields a part of the final answer.

  * e.g., Original query: "Compare the climate of Paris and Tokyo and how it has changed in the last decade."  
    Possible sub-questions: (1) "What is the climate of Paris and how has it changed in the last decade?" (2) "What is the climate of Tokyo and how has it changed in the last decade?" (M1 might generate these.)

* **WorkUnit Creation:** Wrap the original query (if not decomposed) or each sub-question into a WorkUnit. Mark is_subquestion = true for sub-questions, false for the original. Each WorkUnit gets a new UUID and parent_query_id = UserQuery.id for traceability.

* The original query text and any clarifications made are appended to global history [S0].history (so the conversation log is up-to-date).

* **Key Parameters:**

* cfg.qp.enable_decomposition: boolean to turn on/off automatic query splitting.

* cfg.qp.max_rounds: maximum times M1 can be re-entered in the loop (to refine questions). If the system loops back here beyond this count, it should stop further decomposition attempts.

* **Output:** A list of WorkUnit objects. Even if there is only one (no decomposition), it is wrapped in a list for uniform handling. These WorkUnits move next into the Query Routing stage.

* **Loop Behavior:** If M1 is invoked again (via a loop from M9 or M11), it should recognize if the query was already decomposed to avoid repetition. It might then attempt an alternative strategy (e.g., simplify the query wording or adjust a previous sub-question) based on instructions from the controller.

By performing these preprocessing steps, M1 ensures that downstream retrieval modules receive well-formed queries (or sub-queries) that can be effectively answered by the available resources.

### [M2] Query Router (QR)

**Role:** Route each query (or sub-query) to appropriate retrieval path(s).

* **Input:** One or more WorkUnit instances (from M1).

* **Responsibilities:**

* For each WorkUnit, determine the best retrieval strategy. The router uses a set of heuristics, rules, or possibly a classifier model to decide among:

  * **Simple internal search (P1)**: e.g., if the WorkUnit is about a known entity, fact, or something that likely exists in a structured DB or internal knowledge base.

  * **Internet search (P2)**: e.g., if the WorkUnit asks for very current information (news, live data) or something obscure not in internal data.

  * **Multi-hop reasoning (P3)**: e.g., if the WorkUnit is a question that likely requires answering intermediate questions or combining data from multiple sources.

* The router is not limited to a single path – it can send the same WorkUnit to multiple paths in parallel for thoroughness. For example, a generic question might be answered by internal data (P1) but just in case, also query the web (P2) for any newer info. However, a path will not be chosen if it’s clearly irrelevant (to save resources).

* The decision logic can factor in signals such as:

  * Presence of certain keywords (e.g., "latest", "today" might favor P2).

  * Availability of an index (if we have an internal index covering the topic, favor P1).

  * Complexity (if question has multiple entities/relations, consider P3).

  * Also, system load or time constraints (maybe limit to cfg.router.max_parallel_paths to avoid excessive branching).

* Each routing action results in a RoutePlan entry, logging something like: WorkUnit X → Path P1 (router_decision_id = ABC), WorkUnit X → Path P2 (router_decision_id = ABD).

* If a WorkUnit is routed to multiple paths, copies of that WorkUnit are sent to each path’s initial module (M3, M5, M6 respectively). They carry along the same content but different router_decision_id for provenance.

* A timeout (cfg.router.timeout_ms) may be set such that if a given retrieval path takes too long, the router (or subsequent aggregator) will ignore its result to keep the system responsive. (This can be implemented by having each retrieval path enforce its own timeout, or the aggregator ignoring late arrivals.)

* **Output:** No direct output object besides logs. The main result is that WorkUnits have been dispatched to various paths. The flow now continues in parallel in those paths (P1, P2, P3 as decided).

The Query Router acts like a traffic controller, ensuring each query fragment goes to the right experts. This modular routing means adding new paths (like a specialized API lookup) in the future would be easy by extending the router’s logic.

### [P1] Simple Retrieval Path (Internal Knowledge)

The **Simple Retrieval path** is designed to query internal databases or knowledge bases quickly. It consists of two primary components working in sequence:

#### *[M3] SimpleRetrieval (SR)*

* **Function:** Executes a search or lookup against internal data sources for the given WorkUnit’s query.

* **Operation:** This could involve:

* Querying one or multiple **internal databases** or indexes (for example, a vector database of documents, a SQL knowledge base, or an in-memory dictionary of facts).

* Each source queried can return a set of results (documents or data entries) with a native relevance score.

* M3 will collect the top results from each source (up to cfg.sr.top_n per source, for example) and convert them into a standardized **EvidenceItem** format. This involves extracting a relevant snippet or data field as content and attaching provenance info:

  * source_type would be "db" for internal sources.

  * source_id might be the name of the database or index.

  * If applicable, doc_id or chunk_id identifies where in the source the evidence came from.

  * A timestamp retrieved_at is recorded (especially important if data can change over time).

  * The router_decision_id from M2 is included to tie this evidence back to the routing decision.

* M3 should handle multiple sources if configured (cfg.sr.max_sources), possibly in parallel, and merge results into one list.

* **Scoring:** M3 may return a raw score_raw from the retrieval (e.g., a cosine similarity from a vector search or TF-IDF score). These are included in EvidenceItem for later use (the Reranker may use them).

* **Key Parameters:**

* cfg.sr.max_sources: how many internal sources to query (and maybe which ones, via config).

* cfg.sr.top_n: how many top results to retrieve from each source.

* **Output:** A collection of EvidenceItem objects (possibly empty if nothing found). These are passed to the next stage, RQC (M4).

#### *[M4] RetrievalQualityCheck (RQC) – for P1*

* **Function:** Filter and validate the raw evidence from M3 to ensure relevance and quality before it goes into the aggregator.

* **Checks performed:**

* **Relevance threshold:** If the retrieval module provided a score_raw or there is a way to estimate relevance, filter out items below cfg.rqc.min_score or otherwise deemed irrelevant. For example, if searching a vector DB, any result with similarity below a threshold might be dropped.

* **Content quality:** Check that the evidence content is coherent and not an out-of-context snippet. If the evidence is just a single stray sentence with no clear connection, it might be flagged as low quality.

* **Overlap with query:** Optionally, ensure the evidence has a certain overlap with the query terms or semantics (cfg.rqc.quality_threshold might define this). If a result is only tangentially related, it could be removed (status low_overlap).

* The RQC may also enforce policies like filtering out very long results (that might dilute focus) or ensuring diversity (dropping near-duplicates among results).

* **Output:** An RQCResult.

* If one or more items pass the checks, RQC outputs { status: 'ok', items: [...] } with the filtered list of EvidenceItems (possibly re-scored or annotated).

* If no item is suitable, RQC outputs { status: 'no_fit', reason: ... } where reason could be:

  * 'not_found' if the original result list was empty.

  * 'low_overlap' if results were found but none sufficiently matched the query content.

  * 'low_quality' if results were found but filtered out due to quality issues.

* These signals allow the system to know whether P1 contributed useful evidence or not.

* **Note:** RQC is a common module used after all retrievals. In implementation, it could be the same code invoked for each path’s results. It ensures that only relevant, high-quality evidence proceeds.

After RQC, the (possibly filtered) evidence items are sent to the Evidence Aggregator [M7]. If status was 'no_fit', the aggregator will know P1 had no good results, but this information might still be logged or used for fallback logic.

### [P2] Internet Retrieval Path (External Web/API Search)

The **Internet Retrieval path** is designed for fetching information from external sources, such as web search engines or specific APIs, especially for up-to-date or wide-ranging information. It also uses module M4 for quality checking.

#### *[M5] InternetRetrieval (IR)*

* **Function:** Perform an internet search or call external APIs based on the WorkUnit’s query.

* **Operation:** Depending on configuration, M5 might:

* Use a search engine API to get web results (webpages, news articles, etc.). The query would typically be the WorkUnit text. The top results (titles, snippets, URLs) are retrieved.

* For each top result, M5 may fetch the content (e.g., the text of a webpage) or at least a snippet around the query terms. This could be done via an HTTP request to the URL or using a cached index if available.

* Alternatively, if the query suggests using a specific external API (for instance, a weather API if the question is about weather), M5 could call those APIs and get structured data.

* Normalize the retrieved content into EvidenceItem objects:

  * source_type would be "web" for webpages, or "api" if an external API was used.

  * source_id could be the domain of the website or the name of the API.

  * For web content, include the url field (and possibly doc_id if a cached ID exists).

  * Include retrieved_at timestamp and the router_decision_id.

  * The content field might be a summary or snippet if the full page is too large – focusing on the parts that seem relevant to the query.

  * Attach any raw score if available (some search APIs provide a rank or score).

* Apply domain or content filters: if cfg.ir.allowed_domains is set, restrict results to those domains. If cfg.ir.max_age_days is set, filter out content older than that (to ensure recency, e.g., only last 30 days).

* **Key Parameters:**

* cfg.ir.allowed_domains: list of domains or site patterns to trust or prefer (to avoid unreliable sources).

* cfg.ir.max_age_days: an age threshold for content freshness (for time-sensitive queries).

* cfg.ir.top_n: how many search results or API results to retrieve.

* **Output:** A set of EvidenceItem objects from the web/API. If no results were found or an error occurred (e.g., no internet connectivity or API failure), this could result in an empty list (which RQC will handle as no_fit).

#### *[M4] RetrievalQualityCheck (RQC) – for P2*

* **Function:** Just like in P1, validate the results, with some additional web-specific checks.

* **Additional Checks for Web:**

* **Spam/Source Reliability:** The web can return spam or low-quality content. RQC should check sources against a safe/reliable list. If a result comes from a disallowed or untrusted domain, it might be discarded (or at least flagged).

* **Duplicate elimination:** If multiple web results have essentially the same content (e.g., syndicated news articles), RQC might remove duplicates.

* **Content Safety:** Optionally, ensure the content has no disallowed material if that’s a concern (though this is more of a moderation task).

* Use the same relevance and overlap checks as P1 for consistency. Ensure the snippet or content indeed addresses the query.

* **Output:** As before, an RQCResult with status 'ok' and filtered items, or 'no_fit' with a reason. For example, if the internet search returned results but all were off-topic, reason: 'low_overlap' could be used.

The Internet path is slower than P1 (due to network calls), so it might be used selectively. But it’s crucial for questions that require the latest information or are outside the scope of internal data. The quality check is especially important here to guard against misinformation from the web.

### [P3] Multi-Hop Retrieval Path (Iterative Reasoning)

The **Multi-Hop Retrieval path** handles complex queries that require multiple steps of retrieval and reasoning. This path is orchestrated by a specialized module M6 and also uses RQC after each hop.

#### *[M6] MultiHopOrchestrator (MHO)*

* **Function:** Break down and solve a query via multiple retrieval and reasoning hops. It acts like a conductor, using intermediate answers to guide subsequent searches.

* **Operation:** For a given WorkUnit (which likely was identified by the router as requiring multi-hop):

* M6 first analyzes the query and comes up with a plan or an initial sub-question. This could be done by an LLM prompt that asks, "What are the sub-questions needed to answer this?" or by identifying entities to explore.

* It then issues a search (which could internally reuse M3 or M5 capabilities) for the first sub-question. For example, if the question is "Did X influence Y's work, and how?", M6 might split it into "Who is X? What is Y known for? Did X and Y ever collaborate?" etc., one at a time.

* After the first hop, it obtains some evidence. M6 will pass that evidence through RQC (for that hop) to ensure it's useful.

* Then M6 uses the evidence from the first hop to formulate the next query. For instance, if hop1 found that "X was a mentor of Y", the next hop might specifically search for "X mentor Y influence".

* This process continues for a number of hops until M6 believes the chain of information is sufficient to answer the original question or it hits a configured limit.

* The orchestration may branch (if cfg.mho.branching_factor > 1) – meaning at certain steps, M6 could follow multiple paths in parallel (like exploring different hypotheses). However, branching is advanced; MVP can stick to sequential hops.

* **Key Parameters:**

* cfg.mho.max_hops: the maximum number of iterative hops M6 will perform. Prevents endless digression. For example, max_hops = 3 would limit the process to three sequential queries.

* cfg.mho.branching_factor: how many parallel branches of reasoning to pursue at each step (default 1 for linear, could be >1 for exploring different angles).

* cfg.mho.timeout_ms: a safety timeout to stop the process if it’s taking too long (long queries could potentially loop without finding an answer).

* **Output:** At the end of multi-hop, M6 produces a collection of evidence items (just like other paths). This could include evidence from multiple hops aggregated together. Each EvidenceItem’s provenance will show intermediate sources, but for simplicity they can all be listed as results to answer the main WorkUnit. M6 might also compile a synthesized piece of evidence that summarizes the multi-hop findings, but that's optional. The results then go through RQC.

#### *[M4] RetrievalQualityCheck (RQC) – for P3*

* **Function:** Ensure each hop’s result is relevant before continuing, and validate the final compiled evidence.

* **Usage in hops:** After each hop retrieval that M6 does, RQC should be applied:

* If a hop yields nothing (no_fit), M6 might decide to backtrack or try a different approach. If all approaches fail, M6 will terminate with no answer.

* If a hop yields some info but borderline quality, M6 might still use it but be cautious or try an alternate query.

* **Final check:** Once multi-hop is complete (either by reaching an answer or max hops), RQC does a last pass on the combined evidence set to filter out anything not directly useful for the main query.

* **Output:** Same pattern of RQCResult. Typically, if one hop fails, M6 might handle it internally rather than propagating a failure. By the time it outputs to the aggregator, it will either present some evidence (status: ok) or effectively none (status: no_fit if multi-hop couldn't find anything relevant).

Multi-hop retrieval is effectively an agent that can use the other retrieval modules in a loop. It will likely be implemented with LangGraph as a subgraph or a specialized node that can call out to search tools and incorporate results step by step. The RQC integration ensures that the chain of reasoning stays on track and discards false leads.

### [M7] Evidence Aggregator (EA)

**Role:** Consolidate evidence from all retrieval paths for each WorkUnit.

* **Input:** Sets of evidence from any of the activated paths (P1, P2, P3). By the time it reaches M7, for each WorkUnit we may have:

* A set of EvidenceItems from P1 (or a no_fit signal).

* A set of EvidenceItems from P2 (or a no_fit signal).

* A set of EvidenceItems from P3 (or a no_fit signal).

* **Responsibilities:**

* **Merging:** Combine all evidence items into one unified list for the WorkUnit. If multiple paths returned the same or very similar content, detect duplicates:

  * For text evidence, this could mean checking if one snippet’s text is contained in another or using a similarity metric to identify overlap. If duplicates are found, keep one representative (perhaps the one with higher original score or from a preferred source).

  * Use cfg.ea.dedup_threshold to decide what similarity constitutes a duplicate.

* **Unifying Schema:** Ensure each evidence item has all required fields. If different paths produce slightly different structures, normalize them (this is mostly handled by using the same EvidenceItem model everywhere).

* **Provenance Integrity:** Maintain all provenance info. If we drop a duplicate, we might want to note if it appeared in two sources for completeness (although not strictly necessary to expose).

* **Prioritize or tag by source:** Optionally, the aggregator might tag evidence by which path it came from (if needed for later analysis). E.g., mark an evidence as coming from web vs. internal.

* The aggregator does not rank or filter by relevance (that’s for the reranker next), but it might filter out items that are essentially empty or purely duplicates.

* **Key Parameters:**

* cfg.ea.merge_strategy: could define how to merge duplicates (e.g., prefer internal over web, or prefer more recent evidence).

* cfg.ea.dedup_threshold: similarity threshold for considering two pieces of evidence the same.

* **Output:** A unified **EvidenceSet** (this could simply be a list of EvidenceItems or a wrapper object) for each WorkUnit. In an implementation, M7 might add this to the state [S0] as state.evidence[workunit_id] = [ ...items... ]. This set is then passed to M8 (ReRanker).

The Evidence Aggregator ensures that downstream components deal with a clean, non-redundant set of evidence, and it abstracts away which path the evidence came from. This is useful because the Answer Creator should consider all evidence collectively for the final answer.

### [M8] ReRanker (RR)

**Role:** Rank the evidence by relevance to the original query.

* **Input:** The EvidenceSet for each WorkUnit (from M7). If multiple WorkUnits, M8 will handle each separately.

* **Responsibilities:**

* For each WorkUnit’s evidence list, compute a relevance score of each item **with respect to the original UserQuery** (not just the WorkUnit text if it was a sub-question). The reason is that we ultimately answer the original question, and evidence must be put in that context.

* This can be done with a learned model (e.g., a cross-encoder that takes the query and evidence text and outputs a relevance score) or simpler heuristics. The specific model can be configured via cfg.rr.model_name (for example, using a MiniLM cross encoder or a GPT-4 scoring function).

* Normalize or calibrate scores if combining sources with different scoring systems (since internal DB scores and web search scores may not be directly comparable). The reranker can override the original score_raw.

* Produce a sorted list of evidence items by rr_score (descending). Annotate each EvidenceItem with its new rr_score.

* Optionally, limit to top K items per WorkUnit (dropping the rest) if cfg.rr.top_k is set. This focuses the answer generation on the most pertinent evidence, though non-top-K evidence can be kept in state in case needed.

* Store the ranking result in the state, e.g., [S0].ranked_evidence[workunit_id] = [RankedEvidence, ...].

* **Output:** Ranked list of evidence per WorkUnit (with rr_score). In practice, this flows into the SmartRetrieval Controller (M9) which will consider how good the evidence is.

By re-ranking, we unify evidence relevance scoring across heterogeneous sources, which improves the quality of the final answer (since the Answer Creator can start by focusing on highest-ranked evidence). It also provides a confidence measure: if the top evidence scores are low, the system might realize it doesn’t have a strong basis for an answer.

### [M9] SmartRetrieval Controller (SMR)

**Role:** Decide next steps based on evidence sufficiency.

* **Input:** The ranked evidence sets for all WorkUnits (from M8), plus overall context from [S0] (original query, maybe stats).

* **Responsibilities:** This is a decision point with three possible outcomes:

* **AnswerReady:** If the evidence is strong enough to answer the question confidently, proceed to answer generation.

  * Criteria might include: each WorkUnit has at least one high-relevance evidence item (above some confidence threshold), and collectively the evidence covers all aspects of the query.

  * cfg.smr.min_confidence may be defined (possibly derived from top evidence scores or a trained classifier that predicts answerability). If met or exceeded, no further retrieval is needed.

* **NeedsBetterDecomposition (Refinement):** If some parts of the question have poor evidence or the query might have been interpreted incorrectly, decide to go back and reformulate.

  * For example, if one sub-question returned no good results (no_fit from all paths), maybe that sub-question was phrased poorly. SMR can flag that WorkUnit for reformulation.

  * SMR could also decide to escalate to a more complex path: e.g., maybe the query should have been handled with multi-hop (P3) if it wasn’t already.

  * In effect, SMR will trigger a loop back to [M1] Query Preprocessor with guidance. This guidance can be passed via [S0] or context: e.g., state.loop_feedback might contain notes like "No results for sub-question X, consider rephrasing or broadening it."

  * It increments the loop counter smartretrieval_to_qp. If the count > cfg.loop.max.smartretrieval_to_qp, it will not loop but instead likely go to outcome 3 (insufficient evidence).

* **InsufficientEvidence (Terminate):** If the system determines it cannot answer the query with the available resources:

  * This could be because after some retries, still no useful evidence is found, or perhaps the query is out of scope (e.g., asking for an opinion or something not factual).

  * In this case, the pipeline will not proceed to AnswerCreator in the normal way. Instead, it might prepare a special response like "I'm sorry, I cannot find an answer to that question in the provided sources."

  * Termination here is graceful: log the situation, and move to final answer delivery with a negative or null answer (depending on how we want to handle it).

* **Output:** A decision that is acted upon by the workflow:

* If AnswerReady: pass control to [M10] AnswerCreator.

* If NeedsBetterDecomposition: loop to [M1] (with updated context or instructions for query refinement).

* If InsufficientEvidence: skip to [M10] or [M12] with an instruction to output a "no answer" response (or possibly a specialized fallback answer module, but in our flow we can handle it in AC/IA by checking a flag).

The SmartRetrieval Controller is essentially the brain deciding if we have enough info. It prevents wasted effort (by not always trying to answer when evidence is weak) and triggers iterative improvements. This module could be implemented with simple rules at first (e.g., check counts of evidence and a simple threshold), but it’s designed so we can plug in smarter logic later (like an ML model that predicts answerability).

### [M10] AnswerCreator (AC)

**Role:** Generate the answer using the collected evidence.

* **Input:** All relevant data from state – primarily:

* The original **UserQuery** (for reference of what to answer).

* The list of **WorkUnits** (so AC knows if the question was split and can structure the answer accordingly).

* The **RankedEvidence** for each WorkUnit (from M8).

* Possibly the conversation **history** (for context, especially if the answer should be phrased in context or if user asked follow-up).

* Any instructions from SmartRetrieval (e.g., partial answers allowed or not).

* **Responsibilities:**

* **Construct Answer from Evidence:** AC uses an LLM (model specified by cfg.ac.compose_model, e.g., GPT-4) prompted with all the necessary context to draft an answer. The prompt would include a recap of the question, perhaps a summary of evidence for each sub-question, and instructions to compose a coherent answer **only using that evidence**.

* **No Hallucination Principle:** AC should not introduce facts that are not present in the evidence. It should either quote or paraphrase the evidence content to answer the question. If information is missing, AC either omits it or explicitly states the gap.

* **Citation Mapping:** As AC generates the answer text, it should indicate which evidence supports which part of the answer. This could be done by including references in the draft (like [1], [2] placeholders) or by outputting a structured format mapping answer segments to evidence IDs. The result should populate the Answer.citations field. For example, if the answer says "Paris has a temperate climate【evidence_id:abc】", that evidence_id should correspond to an EvidenceItem about Paris’s climate.

* **Tone and Clarity:** The answer should be formulated clearly, addressing the user’s query completely. Since this is an automated system, the tone should be informative and neutral. If the context is a conversation, it may maintain a conversational tone but focus on delivering factual information.

* **Partial or Insufficient Evidence Handling:**

  * If AC was signaled that some aspects have no evidence (or if it detects any WorkUnit with zero evidence items), it will handle according to policy:

  * If partial answers are allowed (cfg.ac.allow_partial_answer = true), AC may answer the parts it can and explicitly mention it couldn’t find information on the missing parts. For example: "I found information on X 【cite】, but I couldn't find details about Y in the provided sources."

  * If partial answers are not allowed or the main question can't be answered, AC’s output might be an Answer with text like "I'm sorry, I don't have enough information to answer that." (This could be a final answer or lead to termination as decided by M9/M11).

  * AC should set a flag or special content in the Answer object if it is an **insufficient evidence** scenario (so that AnswerCheck or IA can handle it appropriately).

* **Output:** A draft Answer object, including:

* text: the answer string (which may include markers for citations).

* citations: an array mapping parts of the answer to evidence (by IDs). The implementation might simply number the citations in order of appearance.

* limitations: if applicable, e.g., ["Partial answer due to missing data on ..."] or other notes.

* Possibly a flag in the object (or simply encoded in limitations) if the answer is incomplete or uncertain.

The AnswerCreator is effectively the "spoken voice" of the system, assembling the final narrative. It must do so transparently (hence citations). Using an advanced LLM here helps produce fluent, well-structured answers that a user can easily read, while still being grounded in the retrieved facts.

### [M11] AnswerCheck (ACK)

**Role:** Validate and verify the answer’s correctness and support.

* **Input:** The draft Answer from M10, along with the full set of evidence used (from [S0], which M11 can access via the evidence IDs in the citations).

* **Responsibilities:**

* **Cross-Verification:** For each citation in the answer, check that the content of the cited EvidenceItem truly supports the claim made in the answer text. This may involve:

  * Verifying exact facts (numbers, names, dates) against the evidence text.

  * Ensuring no claim in the answer lacks a citation. Ideally, every sentence or clause making a factual statement should have a reference. If the answer text has portions not covered by citations, that’s suspicious for unsupported info.

* **Citation Accuracy:** Ensure the citations are correctly mapped. If an answer sentence says "According to Source X, ..." but the citation provided is actually a different source, that's a mismatch. The content of evidence and the way it’s referenced should align.

* **Check for Hallucinations:** If the answer contains information that none of the evidence items contain, flag it. This could happen if AC mistakenly introduced something. For example, if the answer states a summary or inference that isn’t directly in any source, is that allowed? Usually, the answer can draw simple logical conclusions (like combining two facts), but anything beyond trivial inference should be directly supported by evidence.

* **Validation Score:** M11 might use a secondary LLM or heuristic to rate the answer’s support. If cfg.ack.validation_threshold is set (e.g., expecting a certain confidence), M11 ensures the answer meets that threshold.

* **Outcomes of Verification:**

  * If the answer is **fully supported**, M11 approves it and passes it along to M12 for user delivery.

  * If issues are found, M11 will attempt corrective action:

  * If the issue is minor (maybe just one unsupported sentence), M11 could try to remove or revise that part rather than regenerate the whole answer. However, a simpler approach is to just flag for regeneration with stricter prompting.

  * M11 can augment the system prompt or instructions for M10 and send the same evidence back for another attempt. It sets loop_counters.answercheck_to_ac += 1 and triggers the loop to AnswerCreator. For instance, it might instruct: "The previous answer included unsupported info. Please regenerate and ensure every fact is backed by the sources."

  * If the problem seems to be not with phrasing but with missing data (e.g., the user asked a question that none of the evidence addressed at all, so the answer is basically unsupportable), M11 might decide this is not fixable by re-answering. In such cases, it could trigger a loop back to M1 (perhaps the query needs to be changed or the search broadened). That sets loop_counters.answercheck_to_qp += 1 and directs to Query Preprocessor with a note. For example, "The evidence gathered does not cover the query. Consider rephrasing the query or expanding search."

  * M11 will respect loop limits:

  * If answercheck_to_ac exceeds cfg.ack.max_loops, it will stop asking for regeneration. At that point, it might choose to accept the best answer so far (maybe with a disclaimer) or escalate to a human if that were an option, or just apologize to the user.

  * If answercheck_to_qp exceeds its max (probably 1 or 2 since re-querying is heavy), it will not attempt further reformulation. It may then either accept an incomplete answer or say no answer found.

* **Logging:** M11 should log any changes it makes or problems it finds, for transparency and future debugging. For example, log that "Removed unsupported sentence about [X]" or "Regenerating answer, attempt 2".

* **Output:** If verification passes, a **final Answer** object that is verified. If loops are invoked, intermediate output is the instructions to loop; ultimately it outputs the verified Answer when done.

The AnswerCheck is critical for trustworthiness. It guarantees that the answer the user sees is backed by evidence. In essence, it’s a safety net catching any mistakes from the AnswerCreator or earlier steps. This module can be as sophisticated as needed (even involving additional fact-checking tools or rules).

### [M12] InteractionAnswer (IA)

**Role:** Deliver the answer to the user and handle any end-of-interaction tasks.

* **Input:** The final verified Answer from M11 (or in an edge case, a decision that no answer can be given).

* **Responsibilities:**

* **Formatting for User:** Package the answer text along with citations/provenance information into the format required by the user interface or API. For example, if the UI displays citations as footnotes or tooltips, IA will ensure the answer is formatted accordingly (perhaps converting the Answer.citations into actual reference numbers in the text).

* **Presentation:** Send the answer through the appropriate channel (e.g., as an HTTP response if this is a web service, or as a message in a chat interface). This module might not literally render the UI, but it prepares the data for output.

* **Logging and Telemetry:** Record the final outcome in logs:

  * Log the answer text and the evidence IDs used. This could be useful for auditing what sources were provided.

  * Log timing information (total time to answer, maybe time spent in each module if available).

  * Log the request_id and perhaps a conversation ID if part of a longer chat, along with a success status or any error flags.

  * If cfg.ia.log_level is set to verbose, more details can be logged; otherwise, just essential info.

* **Feedback Mechanism:** If user feedback is enabled, IA might append a prompt like "Was this answer helpful? [Yes/No]" or provide a way for the user to correct the system. Capturing this feedback would be sent to a logging system or back into [S0] for analysis. (Design of the feedback loop is beyond this MVP, but placeholders can be in place.)

* **Memory Update:** If maintaining long-term memory, IA could summarize this Q&A pair and add it to a persistent conversation memory store. This summary might be shorter than the full answer but captures the key points, so the system can recall it in future queries if needed.

* **Output:** From the system’s perspective, no further processing output – the answer is now with the user. Possibly returns a success acknowledgment or ends the session. In an interactive setup, the system would then wait for the next user query, at which point the new query along with this Q&A in history would start the cycle anew.

This final step ensures the answer and its evidence reach the user in a clear manner. It also is the transition point where the system's internal process ends and it goes back to listening for user input.

## Non-Functional Requirements and Additional Notes

**Logging & Monitoring:** All modules should emit logs for their major actions and decisions to a centralized log file or logging service. Each log entry should include the request_id (to tie it to the specific query session) and module code (e.g., [M5] Searching web for "X"). Sensitive data can be sanitized in logs if needed. Logging is crucial for debugging and auditing, especially given the complex control flow (loops, parallel paths). We will maintain logs at least at INFO level for normal operations and DEBUG level for more granular tracing when needed. The log files should rotate or be managed to avoid unlimited growth.

**Testing & Validation:** Each module will have basic unit tests to verify its logic in isolation: - For example, test M1 with various input queries to ensure normalization and decomposition work as expected. - Test that M4 properly filters out evidence given certain inputs. - Test M9’s decisions by simulating different evidence scenarios. Additionally, integration tests for the whole pipeline (with stubbed retrieval results) should be written to ensure that the modules work together (e.g., a full query that exercises a loop). Since the system relies on LLM behavior for some modules, those tests might use fixed prompts and a mock LLM that returns predetermined outputs for consistency. Validation of end-to-end behavior with different types of queries will help ensure robustness of the MVP.

**Performance & Scalability:** For the MVP, a single-process design using LangGraph is acceptable. LangGraph allows concurrent execution of independent nodes (like parallel retrievals), so we will exploit that for [P1]/[P2]/[P3] to reduce latency. As we move to multi-user, the system should run as a service (possibly with Uvicorn/Gunicorn if exposing via FastAPI, given Python 3.13 async capabilities). Each request can be handled by spawning a graph run. We should be mindful of LLM API call latencies (especially for M0 clarifications and M10 answer generation) – these dominate response time. Caching frequent queries or reusing results from previous similar questions could be a future improvement for performance.

**Integration & Deployment:** Query Reactor will be a component in a larger system, likely accessed via an API endpoint (e.g., a REST or WebSocket interface) by a client application. For the MVP: - We ensure the design can handle **multiple concurrent users** by isolating state per request and using asynchronous calls where possible for I/O-bound operations (like web search or database fetch). - We will integrate an API layer (outside the scope of this spec) that receives a user query, initializes the [S0] state and triggers the LangGraph workflow to process the query. Once M12 produces the final answer, the API layer returns it to the client. - Future integration may involve authentication, user-specific contexts, and more complex feedback loops, but the MVP focuses on core QA functionality.

**Security & Privacy:** (Note briefly if relevant) Since the system may call external APIs and web search, we must ensure no sensitive user data is unintentionally sent to third parties. Also, the system should handle potentially malicious inputs gracefully (e.g., very long or complex queries, or queries designed to confuse the LLM). Rate limiting or other controls might be considered at the API layer to prevent abuse.

**Framework Use:** As the development team is familiar with LangGraph and PydanticAI, those frameworks will be used to implement the above modules and data flow: - Each module [M0–M12] can be implemented as a **LangGraph node** (some will be custom agent nodes using LLMs, others simple function nodes for data processing). The graph will encode the possible transitions (including loops). - **Pydantic models** will mirror the Data Contracts section, ensuring that when data passes from one node to another, it is automatically validated (e.g., a WorkUnit must have an id, text, etc., or else an error is raised early). - This combination facilitates a maintainable codebase: the graph structure makes the complex workflow explicit and modifiable, and Pydantic data models reduce bugs by enforcing schemas.

By adhering to this spec, the developers should be able to create a modular, testable Query Reactor system. The design emphasizes clarity (each module’s purpose), traceability (IDs and logs for each step), and verifiability (every answer is grounded in evidence). This will serve as a solid foundation for an MVP that can be iterated on with more advanced features or optimizations in the future.

---
