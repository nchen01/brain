# M8 ReRanker Prompt Usage Summary

## Question: Which prompts are actually used by M8?

**Answer: M8 uses exactly 3 prompts from prompts.md:**

### 1. `m8_strategy_selection`
- **Location in code**: `_determine_adaptive_strategy()` method (line ~220)
- **Purpose**: Determines optimal ranking strategy based on query and evidence characteristics
- **Input**: Query text + evidence summary (count, average score, source types)
- **Output**: `AdaptiveStrategy` Pydantic model with weight adjustments
- **Temperature**: 0.3 (moderate creativity for strategy selection)
- **Fallback**: `_fallback_adaptive_strategy()` - returns balanced default weights

### 2. `m8_evidence_scoring`
- **Location in code**: Used in TWO methods:
  - `_calculate_evidence_scores()` method (line ~255) - main scoring
  - `_calculate_relevance_score()` method (line ~439) - relevance-only scoring
- **Purpose**: Scores evidence items on 5 dimensions (relevance, quality, credibility, recency, completeness)
- **Input**: WorkUnit question + evidence title/content/source
- **Output**: `EvidenceScoring` Pydantic model with multi-dimensional scores
- **Temperature**: 0.2 (low creativity for consistent scoring)
- **Fallback**: `_fallback_evidence_scoring()` - uses heuristic calculations

### 3. `m8_ranking_validation`
- **Location in code**: `_validate_ranking_quality()` method (line ~355)
- **Purpose**: Validates the quality and consistency of the final ranking
- **Input**: Original query + ranking summary (top 5 items with scores)
- **Output**: `RankingValidation` Pydantic model with quality metrics
- **Temperature**: 0.1 (very low creativity for objective validation)
- **Fallback**: `_fallback_ranking_validation()` - uses statistical consistency checks

## Prompt Usage Flow

```
M8 Execution Flow:
1. Strategy Selection → m8_strategy_selection
2. Evidence Scoring → m8_evidence_scoring (for each evidence item)
3. Ranking Algorithm → (no prompt, pure algorithm)
4. Ranking Validation → m8_ranking_validation
```

## Key Features

### Structured Output
- All 3 prompts use **structured LLM output** with Pydantic models
- This ensures consistent, validated responses
- Uses `method="function_calling"` for reliability

### Temperature Settings
- **Strategy Selection**: 0.3 (allows some creativity in strategy choice)
- **Evidence Scoring**: 0.2 (consistent scoring across items)
- **Ranking Validation**: 0.1 (objective validation with minimal variation)

### Enhanced Fallback Logging
All prompts now include enhanced fallback logging:
```
🔄 FALLBACK TRIGGERED: M8 [Operation] - [Error Message]
   → [Fallback Action Description]

🔄 EXECUTING FALLBACK: M8 [Operation] - [Fallback Method Description]
```

## Fallback Methods

When LLM calls fail, M8 uses these fallback strategies:

1. **Strategy Selection Fallback**: Returns balanced default weights
2. **Evidence Scoring Fallback**: Uses heuristic calculations based on:
   - Content length and structure
   - Word density and meaningfulness
   - Source credibility mapping
   - Completeness indicators
3. **Ranking Validation Fallback**: Uses statistical methods:
   - Score consistency analysis
   - Top items quality assessment
   - Result diversity calculations

## Verification

✅ **All required prompts are present in prompts.md**
✅ **All prompts have corresponding fallback methods**
✅ **Enhanced fallback logging is implemented**
✅ **Structured output ensures reliable parsing**
✅ **Temperature settings are optimized per task**

## Testing

You can test M8 and see the enhanced fallback logging by:
1. Running `python test_m8_comprehensive.py` (requires dependencies)
2. Running `python test_m8_simple.py` (simulation without dependencies)
3. Running `python m8_prompt_analysis.py` (detailed analysis)

## Summary

M8 is well-designed with:
- **3 specific prompts** for different ranking tasks
- **Robust fallback methods** for all operations
- **Enhanced logging** for easy debugging
- **Structured output** for reliable parsing
- **Optimized temperature settings** for each task type

The enhanced fallback logging makes it much easier to identify when and why M8 falls back to heuristic methods, improving debugging and system monitoring capabilities.