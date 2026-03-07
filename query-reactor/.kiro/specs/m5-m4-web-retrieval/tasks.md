# Implementation Plan

- [x] 1. Set up project structure and dependencies


  - Create M5 and M4 module files with proper imports and base class inheritance
  - Add required dependencies for Google Search API and web scraping
  - Update prompts.md with M4 quality assessment prompt
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 2. Implement M5 Internet Retrieval module (m5_internet_retrieval_langgraph.py)
  - [x] 2.1 Create M5InternetRetrievalLangGraph class inheriting from RetrievalModule

    - Implement basic class structure with proper initialization
    - Set up configuration loading for Perplexity API credentials
    - _Requirements: 1.1, 4.1, 4.2, 6.1_

  - [x] 2.2 Implement Perplexity API integration

    - Create _search_perplexity method using Perplexity chat completions endpoint
    - Handle API authentication with Bearer token and request formatting
    - Implement error handling for API failures and 429 rate limiting
    - _Requirements: 1.1, 4.1, 4.3, 4.4_

  - [x] 2.3 Implement Perplexity response parsing functionality

    - Create _parse_perplexity_response method to extract citations and content
    - Implement _split_content_into_results for content without citations
    - Handle both citation-based and content-based result creation
    - _Requirements: 1.1, 4.5, 4.6_

  - [x] 2.4 Implement evidence creation and state management

    - Create _create_evidence_items method to convert search results to EvidenceItem objects
    - Implement proper provenance metadata with source URLs and timestamps
    - Handle deduplication of similar content
    - _Requirements: 1.2, 1.3, 1.6, 6.2_

  - [x] 2.5 Implement main execute method with error handling

    - Create main execute method following BaseModule interface
    - Implement comprehensive error handling and logging
    - Add support for processing multiple WorkUnits
    - _Requirements: 1.4, 1.5, 6.3, 6.4_

- [ ] 3. Implement M4 Quality Check module (m4_retrieval_quality_check_langgraph.py)
  - [x] 3.1 Create M4QualityCheckLangGraph class inheriting from LLMModule

    - Implement basic class structure with LLM configuration
    - Set up prompt loading from prompts.md
    - Create QualityAssessment Pydantic model for structured output
    - _Requirements: 2.1, 3.1, 3.4, 5.1_

  - [x] 3.2 Implement LLM-based quality assessment

    - Create _assess_evidence_quality method using structured LLM output
    - Implement prompt template substitution with evidence content and query
    - Handle LLM API calls with proper error handling and timeouts
    - _Requirements: 2.2, 2.3, 5.2, 5.3_

  - [x] 3.3 Implement evidence filtering and scoring logic

    - Create _filter_evidence_by_quality method with configurable thresholds
    - Implement quality score validation and normalization
    - Add fallback heuristic scoring when LLM assessment fails
    - _Requirements: 2.4, 2.5, 5.4, 5.5_

  - [x] 3.4 Implement path-aware quality checking

    - Create check_path_evidence_quality method for path coordinator integration
    - Implement batch processing for multiple evidence items
    - Add quality metadata to evidence items
    - _Requirements: 2.1, 2.6, 5.6, 6.2_

  - [x] 3.5 Implement main execute method and state management

    - Create main execute method following BaseModule interface
    - Implement comprehensive error handling with fallback behavior
    - Add logging and performance tracking
    - _Requirements: 2.4, 2.5, 6.3, 6.4_

- [ ] 4. Update path coordinator integration
  - [x] 4.1 Modify m2d5_path_coordinator.py to integrate M4 quality checks




    - Import M4 quality check module
    - Update _execute_single_path method to call M4 after each retrieval path
    - Ensure proper error handling when M4 fails
    - _Requirements: 6.5, 6.6_

  - [x] 4.2 Update path coordinator to handle M5 for P2 path


    - Import M5 internet retrieval module
    - Add M5 execution case for P2 path in _execute_single_path
    - Ensure proper state management and error handling
    - _Requirements: 6.1, 6.2, 6.5_

- [ ] 5. Add configuration and prompt updates
  - [x] 5.1 Update prompts.md with M4 quality assessment prompt


    - Add m4_quality_assessment prompt with proper template variables
    - Include clear instructions for quality scoring dimensions
    - Test prompt template variable substitution
    - _Requirements: 3.2, 3.3, 5.2_

  - [x] 5.2 Add configuration entries for M5 and M4 modules




    - Document required environment variables in .env template
    - Add module-specific configuration options
    - Set up reasonable defaults for all configurable parameters
    - _Requirements: 3.1, 4.2, 6.6_

- [ ] 6. Create comprehensive tests
  - [x] 6.1 Create tests for M5 Internet Retrieval (test_m5_internet_retrieval_langgraph.py)




    - Test Perplexity API integration with mock responses
    - Test citation parsing and content splitting functionality
    - Test evidence creation and deduplication
    - Test error handling scenarios including 429 rate limiting
    - _Requirements: 1.1, 1.4, 4.1, 4.3_



  - [x] 6.2 Create tests for M4 Quality Check (test_m4_retrieval_quality_check_langgraph.py)


    - Test LLM quality assessment with mock responses
    - Test evidence filtering logic
    - Test batch processing functionality
    - Test fallback behavior when LLM fails
    - _Requirements: 2.1, 2.4, 5.1, 5.5_

  - [ ]* 6.3 Create integration tests for M5-M4 workflow
    - Test complete workflow from WorkUnit to quality-filtered evidence
    - Test path coordinator integration
    - Test performance under load
    - _Requirements: 6.5, 6.6_



- [ ] 7. Enhance Perplexity API integration
  - [ ] 7.1 Improve Perplexity API request configuration
    - Update search prompt to be more specific for comprehensive results
    - Optimize model selection and parameters for better search results
    - Implement proper return_citations parameter handling
    - _Requirements: 4.1, 4.4, 4.5_

  - [ ] 7.2 Enhance citation and content processing
    - Improve _parse_perplexity_response to better handle citation data
    - Optimize _split_content_into_results for better content chunking
    - Add better fallback content extraction for non-Perplexity URLs
    - _Requirements: 4.5, 4.6, 1.2_

- [ ] 8. Documentation and deployment preparation
  - [ ] 8.1 Update module documentation and examples
    - Document M5 and M4 configuration options



    - Provide usage examples and troubleshooting guide
    - Update system architecture documentation
    - _Requirements: 3.1, 6.6_

  - [ ] 8.2 Validate end-to-end functionality
    - Test complete QueryReactor workflow with M5 and M4 enabled
    - Verify proper integration with existing modules
    - Test with real Perplexity API calls using configured API key
    - _Requirements: 6.1, 6.2, 6.5, 6.6_