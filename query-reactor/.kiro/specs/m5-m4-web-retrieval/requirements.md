# Requirements Document

## Introduction

This feature implements M5 (Internet Retrieval) and M4 (Quality Check) modules for the QueryReactor system. M5 will use Perplexity API to retrieve current web information with built-in citations, while M4 will use LLM-based quality assessment to evaluate the retrieved evidence. Both modules will load their prompts from the centralized prompts.md file and integrate seamlessly with the existing QueryReactor workflow.

## Requirements

### Requirement 1: M5 Internet Retrieval Module

**User Story:** As a QueryReactor system, I want to retrieve current information from the web using Perplexity API, so that I can provide up-to-date answers with reliable citations to user queries.

#### Acceptance Criteria

1. WHEN a WorkUnit is processed by M5 THEN the system SHALL perform a Perplexity API search using the WorkUnit text as the query
2. WHEN Perplexity search results are returned THEN the system SHALL extract relevant content and citations from the response
3. WHEN content is extracted THEN the system SHALL create EvidenceItem objects with proper metadata including source URLs, timestamps, and relevance scores
4. WHEN search fails or returns no results THEN the system SHALL handle the error gracefully and log appropriate messages
5. WHEN multiple WorkUnits are processed THEN the system SHALL handle them efficiently with proper rate limiting
6. WHEN search results contain duplicate content THEN the system SHALL deduplicate based on content similarity

### Requirement 2: M4 Quality Check Module

**User Story:** As a QueryReactor system, I want to assess the quality and relevance of retrieved evidence, so that I can filter out low-quality or irrelevant information before answer generation.

#### Acceptance Criteria

1. WHEN evidence items are received THEN the system SHALL evaluate each item's relevance to the original query
2. WHEN evaluating relevance THEN the system SHALL assign a quality score between 0.0 and 1.0
3. WHEN quality assessment is complete THEN the system SHALL filter out evidence below a configurable quality threshold
4. WHEN evidence is filtered THEN the system SHALL preserve high-quality evidence and mark low-quality evidence appropriately
5. WHEN assessment fails THEN the system SHALL default to keeping the evidence with a warning log
6. WHEN multiple evidence items are processed THEN the system SHALL maintain consistent quality standards across all items

### Requirement 3: Prompt Loading System

**User Story:** As a developer, I want both M5 and M4 modules to load their prompts from the centralized prompts.md file, so that prompt management is consistent and maintainable.

#### Acceptance Criteria

1. WHEN modules initialize THEN they SHALL load their respective prompts from prompts.md
2. WHEN prompts.md is updated THEN modules SHALL be able to reload prompts without system restart
3. WHEN a required prompt is missing THEN the system SHALL raise a clear error with the missing prompt name
4. WHEN prompt loading fails THEN the system SHALL provide fallback behavior and log the error
5. WHEN prompts contain variables THEN the system SHALL support template substitution

### Requirement 4: Perplexity API Integration

**User Story:** As the M5 module, I want to integrate with Perplexity API for real-time web search, so that I can retrieve current and comprehensive web information with built-in citations.

#### Acceptance Criteria

1. WHEN performing searches THEN the system SHALL use Perplexity API chat completions endpoint with online models
2. WHEN API keys are required THEN the system SHALL load PERPLEXITY_API_KEY securely from environment variables
3. WHEN rate limits are encountered THEN the system SHALL implement exponential backoff and retry logic with proper 429 status handling
4. WHEN search results are returned THEN the system SHALL extract content from Perplexity response and citations when available
5. WHEN citations are provided THEN the system SHALL use them as structured search results with URLs and titles
6. WHEN no citations are available THEN the system SHALL parse the response content into multiple evidence items

### Requirement 5: Evidence Quality Assessment

**User Story:** As the M4 module, I want to use LLM-based assessment to evaluate evidence quality, so that only relevant and reliable information is passed to answer generation.

#### Acceptance Criteria

1. WHEN assessing evidence THEN the system SHALL use the configured LLM to evaluate relevance and quality
2. WHEN evaluating quality THEN the system SHALL consider factors like relevance, credibility, recency, and completeness
3. WHEN generating quality scores THEN the system SHALL provide reasoning for the assessment
4. WHEN evidence is deemed low quality THEN the system SHALL provide specific reasons for the low score
5. WHEN LLM assessment fails THEN the system SHALL use fallback heuristics based on source credibility and content length
6. WHEN assessment is complete THEN the system SHALL update evidence metadata with quality scores and reasoning

### Requirement 6: Integration with Existing Workflow

**User Story:** As a QueryReactor system, I want M5 and M4 to integrate seamlessly with the existing module architecture, so that they work within the current workflow without breaking existing functionality.

#### Acceptance Criteria

1. WHEN M5 is called THEN it SHALL follow the BaseModule interface and accept ReactorState as input
2. WHEN M4 is called THEN it SHALL process evidence from ReactorState and update the state with quality assessments
3. WHEN modules complete THEN they SHALL return updated ReactorState with proper logging and statistics
4. WHEN errors occur THEN modules SHALL handle them gracefully without crashing the entire workflow
5. WHEN integrated with path coordinator THEN modules SHALL work correctly in parallel execution scenarios
6. WHEN configuration is needed THEN modules SHALL use the existing configuration system