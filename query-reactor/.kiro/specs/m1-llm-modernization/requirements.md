# Requirements Document

## Introduction

The M1 Query Preprocessor module currently suffers from critical LLM response parsing failures due to outdated JSON parsing approaches and inconsistent error handling. This modernization effort will align M1 with the successful structured output pattern used in M0, eliminate Pydantic validation errors, fix state management issues, and ensure robust fallback behavior. The goal is to achieve reliable query preprocessing with proper error handling and consistent LLM integration patterns across the QueryReactor system.

## Requirements

### Requirement 1: Modernize LLM Integration Architecture

**User Story:** As a developer, I want M1 to use the same modern structured output pattern as M0, so that LLM responses are parsed reliably without JSON validation errors.

#### Acceptance Criteria

1. WHEN M1 calls an LLM THEN it SHALL use ChatOpenAI().with_structured_output() pattern instead of raw JSON parsing
2. WHEN structured output is configured THEN the LLM SHALL return validated Pydantic objects directly without manual parsing
3. WHEN M1 processes normalization requests THEN it SHALL receive QueryNormalizationOutput objects without parse_raw() calls
4. WHEN M1 processes reference resolution THEN it SHALL receive ReferenceResolutionOutput objects through structured output
5. WHEN M1 processes decomposition requests THEN it SHALL receive QueryDecompositionOutput objects with automatic validation

### Requirement 2: Fix Pydantic Model Compatibility

**User Story:** As a developer, I want M1 to use current Pydantic v2 methods, so that deprecated method warnings are eliminated and validation works correctly.

#### Acceptance Criteria

1. WHEN M1 converts Pydantic objects to dictionaries THEN it SHALL use model_dump() instead of deprecated dict() method
2. WHEN M1 parses JSON responses THEN it SHALL use model_validate_json() instead of deprecated parse_raw() method
3. WHEN M1 validates data THEN it SHALL use current Pydantic v2 validation patterns
4. WHEN M1 handles validation errors THEN it SHALL catch ValidationError with proper error messages
5. WHEN M1 creates model instances THEN it SHALL use current constructor patterns without deprecated methods

### Requirement 3: Implement Robust State Management

**User Story:** As a developer, I want M1 to handle ReactorState attributes correctly, so that dynamic attribute access works reliably without AttributeError exceptions.

#### Acceptance Criteria

1. WHEN M1 sets preprocessing_metadata THEN it SHALL ensure the attribute is properly initialized on ReactorState before any access attempts
2. WHEN M1 accesses state attributes THEN it SHALL use safe attribute checking with hasattr() or getattr() with defaults instead of direct access
3. WHEN M1 encounters missing attributes THEN it SHALL handle the error gracefully by initializing the attribute or using fallback values without crashing
4. WHEN M1 modifies state THEN it SHALL ensure all changes are compatible with LangGraph state management and Pydantic model validation
5. WHEN M1 passes state between nodes THEN it SHALL maintain proper ReactorState type consistency and avoid passing dict objects where ReactorState is expected

#### Technical Context

The current M1 implementation has several state management issues:

- **Dynamic Attribute Problem**: M1 tries to access `state.preprocessing_metadata` but this attribute doesn't exist initially, causing `AttributeError: 'ReactorState' object has no attribute 'preprocessing_metadata'`
- **Initialization Timing**: The module sets `state.preprocessing_metadata = {}` in one node but tries to access it in fallback scenarios before it's been set
- **Type Consistency**: Some code paths pass dict objects instead of ReactorState objects, causing `'dict' object has no attribute 'add_history_turn'` errors
- **Fallback Access Patterns**: The current code uses `if hasattr(state, 'preprocessing_metadata'):` but this check fails because the attribute is set dynamically

The solution requires:
- Proper attribute initialization in ReactorState model or early in M1 processing
- Consistent use of safe attribute access patterns throughout M1
- Ensuring all state modifications maintain the correct object type
- Implementing graceful fallback when expected attributes are missing

### Requirement 4: Establish Consistent Error Handling and Fallback Behavior

**User Story:** As a system operator, I want M1 to handle LLM failures gracefully, so that the system continues processing with appropriate fallback responses instead of crashing.

#### Acceptance Criteria

1. WHEN LLM calls fail THEN M1 SHALL implement fallback processing that creates valid WorkUnit objects
2. WHEN validation errors occur THEN M1 SHALL log the error and proceed with safe default values
3. WHEN reference resolution fails THEN M1 SHALL use simple text processing as fallback
4. WHEN decomposition fails THEN M1 SHALL treat the query as a single WorkUnit without sub-questions
5. WHEN any node fails THEN M1 SHALL ensure the processing pipeline continues with degraded but functional behavior

### Requirement 5: Improve Test Compatibility and Mock Handling

**User Story:** As a developer, I want M1 tests to work correctly with the new architecture, so that the module can be tested reliably in both unit and integration scenarios.

#### Acceptance Criteria

1. WHEN tests mock LLM responses THEN M1 SHALL handle both structured output and fallback scenarios correctly
2. WHEN tests provide mock sequences THEN M1 SHALL consume responses in the correct order regardless of fallback behavior
3. WHEN tests expect specific outputs THEN M1 SHALL produce consistent results that match expected Pydantic models
4. WHEN tests run with mocked dependencies THEN M1 SHALL not fail due to missing external services
5. WHEN integration tests run THEN M1 SHALL work correctly with real LLM services and proper error handling

### Requirement 6: Maintain Backward Compatibility with QueryReactor System

**User Story:** As a system architect, I want M1 modernization to integrate seamlessly with existing modules, so that the overall QueryReactor workflow continues to function without breaking changes.

#### Acceptance Criteria

1. WHEN M1 outputs WorkUnit objects THEN they SHALL maintain the same structure and fields expected by downstream modules
2. WHEN M1 processes queries THEN it SHALL continue to support the same input formats from M0
3. WHEN M1 completes processing THEN it SHALL update ReactorState in ways compatible with M2 and other modules
4. WHEN M1 handles conversation history THEN it SHALL maintain compatibility with existing memory management patterns
5. WHEN M1 integrates with LangGraph THEN it SHALL preserve the same node interface and edge connections

### Requirement 7: Enhance Logging and Observability

**User Story:** As a system administrator, I want detailed logging from M1 operations, so that I can monitor performance and debug issues effectively.

#### Acceptance Criteria

1. WHEN M1 processes queries THEN it SHALL log all major operations with request IDs for traceability
2. WHEN M1 encounters errors THEN it SHALL log detailed error information including context and recovery actions
3. WHEN M1 uses fallback behavior THEN it SHALL log the reason for fallback and the alternative action taken
4. WHEN M1 calls LLMs THEN it SHALL log timing information and response validation status
5. WHEN M1 completes processing THEN it SHALL log summary statistics including WorkUnit counts and processing paths taken