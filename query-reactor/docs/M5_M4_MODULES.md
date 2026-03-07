# M5 Internet Retrieval and M4 Quality Check Modules

## Overview

This document describes the M5 (Internet Retrieval) and M4 (Quality Check) modules implemented for the QueryReactor system. These modules work together to provide high-quality web search results with intelligent quality filtering.

## Architecture

### Data Flow
```
WorkUnits → Path Coordinator → M5 (Internet Retrieval) → M4 (Quality Check) → Filtered Evidence
```

### Module Integration
- **M5**: Handles P2 (Internet Retrieval) path from M2 router
- **M4**: Reusable quality gate applied after each retrieval path (P1, P2, P3)

## M5 Internet Retrieval Module

### Purpose
M5 performs real-time web search using Perplexity API to retrieve current, AI-curated information that may not be available in internal knowledge bases.

### Key Features
- Perplexity API integration for AI-curated search results
- High-quality content extraction with built-in summarization
- Structured responses with citations and sources
- Rate limiting and error handling
- Fallback to placeholder data for development/testing

### Configuration

#### Environment Variables
```bash
# Required for Perplexity API
PERPLEXITY_API_KEY=your_perplexity_api_key

# Optional configuration
M5_MAX_RESULTS=10
M5_MODEL=llama-3.1-sonar-small-128k-online
```

#### Config.md Settings
```
m5.model = "llama-3.1-sonar-small-128k-online"
m5.max_results = 10
m5.rate_limit_delay = 1.0
m5.timeout_seconds = 30
```

### Usage Example

```python
from src.modules.m5_internet_retrieval_langgraph import m5_internet_retrieval
from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit

# Create state with WorkUnits
state = ReactorState(original_query=user_query)
state.add_workunit(workunit)

# Execute internet retrieval
result_state = await m5_internet_retrieval.execute(state)

# Access retrieved evidence
for evidence in result_state.evidences:
    print(f"Title: {evidence.title}")
    print(f"Content: {evidence.content[:100]}...")
    print(f"Source: {evidence.provenance.url}")
```

### Error Handling

M5 handles various error scenarios gracefully:

1. **Missing API Credentials**: Falls back to placeholder search results
2. **Rate Limiting**: Implements exponential backoff and retry logic
3. **Network Failures**: Returns partial results when possible
4. **Content Extraction Failures**: Falls back to search snippets

## M4 Quality Check Module

### Purpose
M4 uses LLM-based assessment to evaluate the quality and relevance of retrieved evidence, filtering out low-quality information before answer generation.

### Key Features
- LLM-powered quality assessment
- Multi-dimensional scoring (relevance, credibility, recency, completeness)
- Configurable quality thresholds
- Batch processing for efficiency
- Fallback heuristic scoring when LLM fails

### Quality Assessment Dimensions

1. **Relevance** (0.0-1.0): How well the evidence addresses the query
2. **Credibility** (0.0-1.0): Trustworthiness of the source and content
3. **Recency** (0.0-1.0): How current the information is
4. **Completeness** (0.0-1.0): How comprehensive the information is

### Configuration

#### Config.md Settings
```
m4.model = "gpt-5-nano-2025-08-07"
m4.quality_threshold = 0.6
m4.batch_size = 5
m4.timeout_seconds = 10
```

### Usage Example

```python
from src.modules.m4_retrieval_quality_check_langgraph import m4_quality_check

# Check quality for specific path
result_state = await m4_quality_check.check_path_evidence_quality(state, "P2")

# Or check all evidence
result_state = await m4_quality_check.execute(state)

# Evidence below quality threshold is automatically filtered out
print(f"Kept {len(result_state.evidences)} high-quality evidence items")
```

### Quality Assessment Prompt

The M4 module uses a structured prompt from `prompts.md`:

```markdown
## m4_quality_assessment
You are an evidence quality assessor. Evaluate the relevance, credibility, recency, and completeness of the provided evidence for answering the given query.

Original Query: {original_query}
Evidence Source: {evidence_source}
Evidence Title: {evidence_title}
Evidence Content: {evidence_content}

Assess the evidence on these dimensions (0.0 to 1.0):
- Relevance: How well does this evidence address the query?
- Credibility: How trustworthy is the source and content?
- Recency: How current is the information (if applicable)?
- Completeness: How comprehensive is the information?

You must respond with a valid JSON object containing these fields:
- relevance_score: float (0.0 to 1.0)
- credibility_score: float (0.0 to 1.0)
- recency_score: float (0.0 to 1.0)
- completeness_score: float (0.0 to 1.0)
- overall_score: float (0.0 to 1.0)
- reasoning: string explaining your assessment
- should_keep: boolean indicating if evidence meets quality threshold
```

## Path Coordinator Integration

The modules are integrated into the path coordinator (`m2d5_path_coordinator.py`) to ensure consistent quality checking across all retrieval paths:

```python
async def _execute_single_path(self, plan: PathExecutionPlan, 
                             path_state: ReactorState) -> PathExecutionResult:
    # Execute retrieval path
    if plan.path_id == "P1":
        result_state = await simple_retrieval_langgraph.execute(path_state)
    elif plan.path_id == "P2":
        result_state = await m5_internet_retrieval.execute(path_state)
    elif plan.path_id == "P3":
        result_state = await m6_multihop.execute(path_state)
    
    # Apply quality check to evidence from this path
    quality_checked_state = await m4_quality_check.check_path_evidence_quality(
        result_state, plan.path_id
    )
    
    return self._create_path_result(quality_checked_state, plan)
```

## Performance Considerations

### M5 Performance
- **Parallel Processing**: Multiple WorkUnits processed concurrently
- **Content Extraction**: Limited to 10KB per page with 15s timeout
- **Caching**: Search results cached for 1 hour, content for 24 hours
- **Rate Limiting**: Exponential backoff for API rate limits

### M4 Performance
- **Batch Processing**: Up to 5 evidence items assessed in parallel
- **Model Optimization**: Uses task-optimized model parameters
- **Early Termination**: Skips assessment for obviously low-quality evidence
- **Fallback Speed**: Heuristic scoring when LLM assessment fails

## Testing

### Running Tests

```bash
# Test M5 Internet Retrieval
pytest tests/modules/test_m5_internet_retrieval_langgraph.py -v

# Test M4 Quality Check
pytest tests/modules/test_m4_retrieval_quality_check_langgraph.py -v

# Run all module tests
pytest tests/modules/ -v
```

### Test Coverage

Both modules include comprehensive tests covering:
- Normal operation scenarios
- Error handling and edge cases
- API integration (with mocking)
- Configuration loading
- Performance under load

## Troubleshooting

### Common Issues

1. **No Search Results**
   - Check Google API credentials in `.env`
   - Verify search engine ID is correct
   - Check API quota and billing

2. **Quality Check Filtering Too Much**
   - Lower `m4.quality_threshold` in config.md
   - Check LLM model availability
   - Review quality assessment prompt

3. **Slow Performance**
   - Reduce `m5.max_results` for faster searches
   - Disable content extraction: `m5.content_extraction_enabled = false`
   - Increase `m4.batch_size` for better parallelization

### Debug Logging

Enable debug logging to troubleshoot issues:

```bash
LOG_LEVEL=DEBUG python -m src.main
```

### API Monitoring

Monitor Google Search API usage:
- Check quota usage in Google Cloud Console
- Monitor rate limiting in application logs
- Track API costs and usage patterns

## Best Practices

1. **API Key Security**
   - Store API keys in environment variables
   - Never commit API keys to version control
   - Rotate API keys regularly

2. **Quality Threshold Tuning**
   - Start with default threshold (0.6)
   - Adjust based on result quality
   - Monitor filtered vs. kept evidence ratios

3. **Performance Optimization**
   - Use appropriate batch sizes for your workload
   - Enable caching for repeated queries
   - Monitor and optimize timeout values

4. **Error Handling**
   - Always handle API failures gracefully
   - Implement proper retry logic
   - Log errors for monitoring and debugging

## Future Enhancements

Potential improvements for future versions:

1. **Additional Search Engines**: Bing, DuckDuckGo integration
2. **Advanced Content Extraction**: Better parsing for specific content types
3. **Machine Learning Quality**: Train custom quality assessment models
4. **Semantic Deduplication**: Use embeddings for better duplicate detection
5. **Real-time Monitoring**: Dashboard for API usage and quality metrics