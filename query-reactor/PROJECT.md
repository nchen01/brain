# QueryReactor Project Structure Guide

This document provides a comprehensive guide to the QueryReactor project structure, explaining the purpose and relationships of major files and directories. This is essential reading for developers working on or maintaining the QueryReactor system.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [Module Architecture](#module-architecture)
5. [Data Flow](#data-flow)
6. [Configuration System](#configuration-system)
7. [Development Workflow](#development-workflow)
8. [Maintenance Guidelines](#maintenance-guidelines)

## Project Overview

QueryReactor is a production-ready, modular smart query and question-answering system built with:

- **LangGraph**: Workflow orchestration framework
- **Pydantic**: Type-safe data models and validation
- **FastAPI**: Async API service layer
- **Python 3.13**: Modern Python with async capabilities

The system processes user queries through a graph-based workflow with 13 specialized modules, supporting multi-user concurrent operations with full observability.

### Recent Major Improvements (Current Version)

- **Centralized Prompt Management**: All 33 prompts loaded from `prompts.md` with no hardcoded prompts
- **Comprehensive Fallback Logging**: All M0-M12 modules have enhanced error handling with user feedback
- **Enhanced Module Capabilities**: 
  - M9 Smart Controller with WorkUnit feedback and adaptive decision making
  - M11 Gatekeeper with strict retrieval compliance validation
  - M12 Context-aware delivery based on routing decisions
- **Production Readiness**: Robust error handling, monitoring, and debugging capabilities

## Directory Structure

```
QueryReactor/
├── .kiro/                          # Kiro IDE specifications
│   └── specs/query-reactor/        # Project specifications
│       ├── requirements.md         # System requirements
│       ├── design.md              # Architecture design
│       └── tasks.md               # Implementation tasks
├── src/                           # Main source code
│   ├── api/                       # API service layer
│   ├── config/                    # Configuration management
│   ├── logging/                   # Logging infrastructure
│   ├── models/                    # Data models and types
│   ├── modules/                   # Processing modules (M0-M12)
│   ├── observability/             # Monitoring and tracing
│   ├── services/                  # Business logic services
│   └── workflow/                  # LangGraph orchestration
├── monitoring/                    # Monitoring configuration
├── logs/                         # Application logs (created at runtime)
├── config.md                     # System configuration
├── prompts.md                    # Centralized prompt management (33 prompts)
├── .env.example                  # Environment variables template
├── main.py                       # Application entry point
├── Dockerfile                    # Container configuration
├── docker-compose.yml            # Multi-service deployment
├── README.md                     # User documentation
├── PROJECT.md                    # This file
└── IMPLEMENTATION_SUMMARY.md     # Implementation overview
```

## Core Components

### 1. Entry Point (`main.py`)

**Purpose**: Main application entry point with CLI interface
**Key Functions**:
- `start_server()`: Launches FastAPI server
- `run_test_query()`: Executes test queries
- `check_health()`: System health validation
- `show_configuration()`: Configuration display

**Usage**:
```bash
python main.py server    # Start API server
python main.py test      # Run test query
python main.py health    # Health check
python main.py config    # Show config
```

### 2. Configuration System (`src/config/`)

#### `src/config/loader.py`
**Purpose**: Central configuration management
**Key Classes**:
- `ConfigLoader`: Loads config.md, prompts.md, and .env files
- Provides unified access to all configuration values

**Configuration Files**:
- `config.md`: System parameters, model settings, thresholds
- `prompts.md`: Centralized prompt management - 33 prompts for all M0-M12 modules
- `.env`: Sensitive credentials (not in version control)
- `.env.example`: Template for environment setup

**Prompt Management System**:
- **No Hardcoded Prompts**: All modules use `_get_prompt()` method
- **Single Source of Truth**: All prompts in `prompts.md`
- **Fallback Support**: Graceful degradation when prompts fail
- **Version Control**: Track prompt changes through git

### 3. Data Models (`src/models/`)

#### `src/models/core.py`
**Purpose**: Core Pydantic data models
**Key Models**:
- `UserQuery`: User request with multi-tenant isolation
- `WorkUnit`: Query decomposition units
- `EvidenceItem`: Retrieved evidence with provenance
- `RankedEvidence`: Evidence after reranking
- `Answer`: Final response with citations

#### `src/models/state.py`
**Purpose**: State management for LangGraph workflow
**Key Classes**:
- `ReactorState`: Main workflow state container
- `LoopCounters`: Loop prevention and tracking
- `StateManager`: State operations and utilities

#### `src/models/results.py`
**Purpose**: Operation result models
**Key Models**:
- `RQCResult`: Retrieval quality check results
- `SMRDecisionResult`: Smart controller decisions
- `VerificationResult`: Answer verification outcomes

### 4. Workflow Orchestration (`src/workflow/`)

#### `src/workflow/graph.py`
**Purpose**: LangGraph workflow definition
**Key Classes**:
- `QueryReactorGraph`: Main workflow orchestrator
- Defines all 13 modules as nodes
- Manages parallel execution and loops
- Handles conditional routing between modules

#### `src/workflow/loop_controller.py`
**Purpose**: Loop management and control flow
**Key Functions**:
- Loop limit enforcement
- Graceful termination handling
- Loop feedback management

## Module Architecture

The system consists of 13 specialized modules (M0-M12) organized in processing stages:

### Query Processing Stage

#### `src/modules/m0_qa_human.py`
**Purpose**: Interactive query clarification
**Key Features**:
- Ambiguity detection and resolution
- Multi-turn clarification dialogs
- Confidence assessment

#### `src/modules/m1_query_preprocessor.py`
**Purpose**: Query normalization and decomposition
**Key Features**:
- Text normalization and cleaning
- Reference resolution using history
- Query decomposition into sub-questions
- WorkUnit creation and tracking

#### `src/modules/m2_query_router.py`
**Purpose**: Intelligent path selection
**Key Features**:
- Heuristic-based routing decisions
- Multi-path parallel routing
- Path selection reasoning

### Retrieval Stage (Parallel Paths)

#### `src/modules/m3_simple_retrieval.py`
**Purpose**: Internal database simulation (Path P1)
**V1.0 Implementation**: Dummy evidence generation
**V1.1 Target**: Real database integration

#### `src/modules/m5_internet_retrieval.py`
**Purpose**: Web search simulation (Path P2)
**V1.0 Implementation**: Dummy web evidence
**V1.1 Target**: Real web search APIs

#### `src/modules/m6_multihop_orchestrator.py`
**Purpose**: Multi-step reasoning (Path P3)
**V1.0 Implementation**: Simulated reasoning chains
**V1.1 Target**: Real iterative reasoning

#### `src/modules/m4_retrieval_quality_check.py`
**Purpose**: Evidence validation (used by all paths)
**Key Features**:
- Relevance threshold filtering
- Content quality assessment
- Query overlap validation
- Duplicate detection

### Evidence Processing Stage

#### `src/modules/m7_evidence_aggregator.py`
**Purpose**: Evidence consolidation
**Key Features**:
- Multi-path evidence merging
- Deduplication based on similarity
- Provenance preservation
- Schema unification

#### `src/modules/m8_reranker.py`
**Purpose**: Relevance-based ranking
**V1.0 Implementation**: Heuristic scoring
**V1.1 Target**: ML-based ranking models

#### `src/modules/m9_smart_retrieval_controller_langgraph.py`
**Purpose**: Intelligent flow control with WorkUnit feedback
**Key Features**:
- **WorkUnit Performance Analysis**: Tracks success/failure rates
- **Adaptive Decision Making**: Uses feedback to improve routing
- **Quality-Based Control**: Makes decisions based on evidence quality
- **Loop Management**: Prevents infinite loops with intelligent termination

**Key Decisions**:
- `continue`: Continue retrieval with more attempts
- `terminate`: End retrieval and proceed to answer generation
- `return_to_qp`: Loop back to query preprocessing for refinement

### Answer Generation Stage

#### `src/modules/m10_answer_creator_langgraph.py`
**Purpose**: Retrieval-only answer generation
**Key Features**:
- **Strict Retrieval-Only Policy**: No external knowledge allowed
- **Evidence Analysis**: Comprehensive analysis of retrieved evidence
- **Citation Mapping**: Precise tracking of evidence sources
- **Multi-WorkUnit Synthesis**: Combines answers from multiple WorkUnits
- **Quality Indicators**: Confidence scoring and limitation tracking

#### `src/modules/m11_answer_check_langgraph.py`
**Purpose**: Gatekeeper verification with quality assurance
**Key Features**:
- **Retrieval Compliance Validation**: Ensures answers are fully retrieval-based
- **Multi-Attempt Processing**: Returns to M10 for improvements when needed
- **Quality Gatekeeper**: Strict validation before user delivery
- **Issue Detection**: Identifies citation problems, external knowledge, missing sources

**Key Checks**:
- Structure analysis and coherence
- Factual accuracy against evidence
- Citation validation and completeness
- Answer completeness assessment

#### `src/modules/m12_interaction_answer_langgraph.py`
**Purpose**: Context-aware user delivery
**Key Features**:
- **Context-Aware Delivery**: Adapts responses based on routing context from M9/M11
- **Quality Communication**: Indicates when answers meet strict retrieval requirements
- **Limitation Transparency**: Clear communication about answer limitations
- **No-Data Responses**: Helpful responses when insufficient data is available
- **Metadata Enrichment**: Rich context about sources, processing, and quality

### Base Classes (`src/modules/base.py`)

**Purpose**: Common functionality for all modules
**Key Classes**:
- `BaseModule`: Common module interface
- `LLMModule`: LLM-enabled modules
- `RetrievalModule`: Retrieval-specific functionality

## Data Flow

### 1. Request Processing Flow

```
User Request → API Service → LangGraph Workflow → Module Execution → Response
```

### 2. Module Execution Flow

```
M0 (Clarification) → M1 (Preprocessing) → M2 (Routing)
                                            ↓
M3/M5/M6 (Retrieval) → M4 (Quality Check) → M7 (Aggregation)
                                            ↓
M8 (Ranking) → M9 (Controller) → M10 (Answer) → M11 (Check) → M12 (Delivery)
```

### 3. Loop-back Mechanisms

- **M9 → M1**: Query refinement loop
- **M11 → M10**: Answer regeneration loop
- **M11 → M1**: Query reformulation loop

## Configuration System

### Configuration Hierarchy

1. **Environment Variables** (`.env`): Sensitive credentials
2. **System Configuration** (`config.md`): Model settings, thresholds
3. **Agent Prompts** (`prompts.md`): Module-specific prompts
4. **Default Values**: Hardcoded fallbacks in code

### Key Configuration Categories

- **Model Settings**: `ac.model`, `qa.model`, etc.
- **Thresholds**: `smr.min_confidence`, `rqc.min_score`
- **Loop Limits**: `loop.max.smartretrieval_to_qp`
- **Feature Flags**: `qp.enable_decomposition`
- **API Settings**: `api.host`, `api.port`

## Development Workflow

### Adding New Modules

1. **Create Module File**: `src/modules/mX_module_name.py`
2. **Implement Base Class**: Extend `BaseModule` or `LLMModule`
3. **Add to Workflow**: Update `src/workflow/graph.py`
4. **Update Imports**: Modify `src/modules/__init__.py`
5. **Add Configuration**: Update `config.md` and `prompts.md`
6. **Add Tests**: Create test cases

### Modifying Existing Modules

1. **Understand Dependencies**: Check which modules depend on changes
2. **Update Data Models**: Modify `src/models/` if needed
3. **Test Integration**: Ensure workflow still functions
4. **Update Documentation**: Modify relevant docs

### Adding New Retrieval Paths

1. **Create Retrieval Module**: Follow M3/M5/M6 pattern
2. **Update Router**: Modify M2 routing logic
3. **Add Quality Check**: Ensure M4 handles new path
4. **Update Aggregator**: Modify M7 if needed
5. **Add Configuration**: Update path-specific settings

## Maintenance Guidelines

### Code Organization Principles

1. **Separation of Concerns**: Each module has single responsibility
2. **Type Safety**: All data models use Pydantic validation
3. **Error Handling**: Comprehensive exception handling with fallback logging
4. **Logging**: Structured logging with request correlation and user feedback
5. **Configuration**: External configuration for all tunable parameters
6. **Prompt Management**: Centralized prompts with no hardcoded strings
7. **Fallback Systems**: Robust fallback mechanisms with clear user communication

### Performance Considerations

1. **Async/Await**: All I/O operations are asynchronous
2. **Parallel Execution**: Retrieval paths run concurrently
3. **State Management**: Efficient state passing between modules
4. **Memory Management**: Proper cleanup of large objects
5. **Connection Pooling**: For external service connections (V1.1)

### Security Best Practices

1. **Credential Management**: All secrets in environment variables
2. **Input Validation**: Pydantic models validate all inputs
3. **Rate Limiting**: Per-user request limiting
4. **Authentication**: JWT-based auth system
5. **CORS Configuration**: Proper cross-origin settings

### Monitoring and Debugging

1. **Enhanced Fallback Logging**: All M0-M12 modules have comprehensive fallback logging
   - User-visible feedback: `🔄 FALLBACK TRIGGERED: M{X} Operation - {error}`
   - Developer debugging: Detailed logs with context and error information
   - Execution announcements: `🔄 EXECUTING FALLBACK: M{X} Operation - Using fallback logic`
2. **Structured Logging**: JSON logs with correlation IDs
3. **OpenTelemetry**: Distributed tracing support
4. **Metrics Collection**: Performance and usage metrics
5. **Health Checks**: Comprehensive system health validation
6. **Error Tracking**: Detailed error logging and reporting

### Version Management

- **V1.0**: Current dummy implementation for testing
- **V1.1**: Planned full implementation with real integrations
- **Migration Path**: Clear upgrade path from V1.0 to V1.1

### Testing Strategy

1. **Unit Tests**: Individual module testing
2. **Integration Tests**: End-to-end workflow testing
3. **Load Tests**: Multi-user concurrent testing
4. **Health Monitoring**: Continuous system validation

## Key Relationships

### Module Dependencies

- **M1 ↔ M9**: Loop-back for query refinement
- **M2 → M3/M5/M6**: Routing to retrieval paths
- **M3/M5/M6 → M4**: Quality checking
- **M4 → M7**: Evidence aggregation
- **M10 ↔ M11**: Answer generation and verification
- **M11 ↔ M1**: Query reformulation loop

### Data Model Relationships

- **UserQuery → WorkUnit**: Query decomposition
- **WorkUnit → EvidenceItem**: Evidence retrieval
- **EvidenceItem → RankedEvidence**: Ranking process
- **RankedEvidence → Answer**: Answer generation
- **Answer → Citation**: Evidence referencing

### Configuration Dependencies

- **Modules → config.md**: Runtime parameters
- **Modules → prompts.md**: Agent instructions
- **API → .env**: Sensitive credentials
- **Workflow → All configs**: Orchestration settings

## Recent Verification and Improvements

### Prompt Management Verification
- **Scope**: All M0-M12 modules verified for prompt compliance
- **Results**: 100% compliance - no hardcoded prompts found
- **Implementation**: All modules use `_get_prompt()` method to load from `prompts.md`
- **Documentation**: `M0_M6_PROMPT_VERIFICATION_SUMMARY.md`

### Fallback Logging Verification
- **Scope**: All M0-M12 modules verified for comprehensive fallback logging
- **Results**: 100% compliance - all modules have proper fallback logging
- **Features**: 
  - 52 fallback trigger messages for user feedback
  - 26 fallback execution announcements for debugging
  - 60 logged exceptions with proper error handling
- **Documentation**: `FALLBACK_LOGGING_VERIFICATION_SUMMARY.md`

### Module Enhancement Verification
- **M9 Smart Controller**: Enhanced with WorkUnit feedback system
- **M10 Answer Creator**: Strict retrieval-only implementation
- **M11 Answer Check**: Gatekeeper functionality with quality assurance
- **M12 Interaction Answer**: Context-aware delivery system
- **Documentation**: Individual module implementation summaries

### Quality Assurance
- **Testing**: Comprehensive test suites for all major components
- **Verification**: Automated compliance checking for prompts and logging
- **Documentation**: Complete documentation of all improvements and verifications
- **Production Readiness**: Enhanced error handling, monitoring, and reliability

This project structure enables maintainable, scalable development while preserving the modular architecture and clear separation of concerns essential for the QueryReactor system.