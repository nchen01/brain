# Implementation Plan

- [x] 1. Set up modernized LLM integration infrastructure in m1_query_preprocessor_langgraph.py


  - Add StructuredLLMFactory class with methods for normalization, resolution, and decomposition LLMs
  - Update imports to include ChatOpenAI and model_manager for structured output functionality
  - Implement model_manager integration for consistent model selection and parameter optimization
  - Test the new LLM factory methods with simple calls to verify structured output works
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Update Pydantic models for v2 compatibility in m1_query_preprocessor_langgraph.py


  - [x] 2.1 Add ModernBaseModel class with updated methods

    - Add to_dict() method replacing deprecated dict()
    - Add from_json() method replacing deprecated parse_raw()
    - Add from_dict() method replacing deprecated parse_obj()
    - Test the new methods with sample data to verify compatibility
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 Update existing Pydantic output models in the same file

    - Modify QueryNormalizationOutput to inherit from ModernBaseModel
    - Modify ReferenceResolutionOutput to inherit from ModernBaseModel
    - Modify QueryDecompositionOutput to inherit from ModernBaseModel
    - Test model creation and validation with sample data
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Implement enhanced state management components in m1_query_preprocessor_langgraph.py


  - [x] 3.1 Add StateAttributeManager class to the file

    - Add ensure_preprocessing_metadata() method
    - Add safe_get_attribute() and safe_set_attribute() methods
    - Add get_current_query_text() method with clarified_query priority
    - Add get_conversation_context() method with filtering
    - Test state management methods with sample ReactorState objects
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Add StateValidator class to the file

    - Add validate_state_type() method
    - Add validate_required_attributes() method
    - Add proper error handling for type mismatches
    - Test validation methods with valid and invalid state objects
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Add ReactorStateExtensions class to the file

    - Add initialize_m1_attributes() method
    - Add ensure_history_management() method
    - Add proper attribute initialization and history tracking
    - Test state initialization and history management with sample data
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Modernize LangGraph processing nodes in m1_query_preprocessor_langgraph.py


  - [x] 4.1 Update _normalize_query_node method with structured output


    - Replace JSON parsing with structured LLM calls using StructuredLLMFactory
    - Integrate StateAttributeManager for safe attribute handling
    - Add comprehensive error handling with fallback processing
    - Update to use get_current_query_text() for proper query handling
    - Test normalization node with various query inputs and error conditions
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3_

  - [x] 4.2 Update _resolve_references_node method with context awareness

    - Replace JSON parsing with structured LLM calls using StructuredLLMFactory
    - Integrate conversation context filtering and formatting
    - Add proper history management to avoid query duplication
    - Implement enhanced fallback reference resolution
    - Test reference resolution with conversation history and edge cases
    - _Requirements: 1.1, 1.4, 3.1, 3.2, 4.1, 4.2, 4.3_

  - [x] 4.3 Update _decompose_query_node method with context awareness

    - Replace JSON parsing with structured LLM calls using StructuredLLMFactory
    - Add conversation context consideration for decomposition decisions
    - Implement enhanced fallback decomposition with better pattern recognition
    - Ensure proper sub-question generation based on context
    - Test decomposition with various query types and conversation contexts
    - _Requirements: 1.1, 1.5, 3.1, 3.2, 4.1, 4.2, 4.3_

  - [x] 4.4 Update _create_workunits_node method

    - Ensure compatibility with modernized decomposition output
    - Add proper WorkUnit metadata and traceability
    - Maintain backward compatibility with existing WorkUnit structure
    - Test WorkUnit creation with various decomposition results
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5. Implement comprehensive error handling system


  - [x] 5.1 Create three-tier error handling infrastructure

    - Implement _safe_llm_call() method for LLM-level error handling
    - Implement _safe_node_execution() method for node-level error handling
    - Update main execute() method for module-level error handling
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.2 Enhance fallback processing mechanisms

    - Update _fallback_normalize() with better text processing
    - Update _fallback_resolve_references() with enhanced context analysis
    - Update _fallback_decompose() with improved pattern recognition
    - Add _create_fallback_workunit() method for complete failure scenarios
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Update main module execution flow in m1_query_preprocessor_langgraph.py


  - [x] 6.1 Modernize execute() method in QueryPreprocessorLangGraph class

    - Integrate ReactorStateExtensions for proper initialization
    - Add proper history management to avoid duplication
    - Ensure loop counter reset on first M1 entry
    - Add comprehensive logging and error recovery
    - Test the complete execution flow with various input scenarios
    - _Requirements: 3.1, 3.2, 3.3, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 6.2 Update _build_graph() method in QueryPreprocessorLangGraph class

    - Ensure all nodes use modernized implementations
    - Maintain existing edge connections and workflow structure
    - Add proper error propagation between nodes
    - Test the complete LangGraph workflow execution
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Add enhanced logging and observability


  - [x] 7.1 Implement detailed operation logging

    - Add logging for LLM calls with timing information
    - Add logging for state transitions and attribute changes
    - Add logging for fallback behavior activation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 7.2 Add error and recovery logging

    - Log detailed error information with context
    - Log recovery actions and fallback processing
    - Add summary statistics logging for completed processing
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 8. Update helper methods and utilities in m1_query_preprocessor_langgraph.py


  - [x] 8.1 Add conversation context formatting methods to QueryPreprocessorLangGraph class

    - Add _format_conversation_context() method
    - Add proper timestamp and role formatting
    - Ensure context relevance filtering
    - Test context formatting with various history scenarios
    - _Requirements: 3.1, 3.2, 6.4_

  - [x] 8.2 Update entity extraction methods in QueryPreprocessorLangGraph class

    - Enhance _extract_entities_from_history() for better reference resolution
    - Add improved pattern matching for entity recognition
    - Implement context-aware entity selection
    - Test entity extraction with various conversation histories
    - _Requirements: 4.2, 4.3_

- [x] 9. Test the modernized M1 module thoroughly


  - [x] 9.1 Test new components with sample data

    - Test StructuredLLMFactory with mocked LLM responses
    - Test StateAttributeManager methods with various state configurations
    - Test StateValidator with valid and invalid state objects
    - Test ReactorStateExtensions initialization and history management
    - Run getDiagnostics to check for any syntax or import errors
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.2 Test modernized processing nodes

    - Test normalization node with structured output and fallback scenarios
    - Test reference resolution node with conversation context
    - Test decomposition node with context-aware processing
    - Test complete workflow with various query types and error conditions
    - Verify all nodes work correctly with the new architecture
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.3 Test compatibility with existing system



    - Test backward compatibility with existing QueryReactor modules
    - Test WorkUnit structure compatibility with downstream modules
    - Test ReactorState compatibility with M2 and other modules
    - Test conversation history integration with M0 output
    - Run the existing M1 tests to ensure they still pass
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 10. Performance optimization and cleanup in m1_query_preprocessor_langgraph.py



  - [x] 10.1 Optimize LLM call patterns in the modernized code

    - Implement efficient model loading and reuse in StructuredLLMFactory
    - Add proper async handling for concurrent processing
    - Optimize prompt formatting and context preparation
    - Test performance improvements with timing measurements
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 10.2 Clean up deprecated code and imports in the file

    - Remove old JSON parsing code and deprecated Pydantic methods
    - Update imports to use modern LangChain and Pydantic patterns
    - Remove unused fallback code that's been replaced
    - Add proper type hints and documentation
    - Run getDiagnostics to ensure no issues remain
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_