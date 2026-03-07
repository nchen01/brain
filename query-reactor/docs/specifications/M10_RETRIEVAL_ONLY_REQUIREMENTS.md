# M10 Retrieval-Only Requirements Implementation

## Overview

M10 prompts have been updated to enforce STRICT retrieval-only answer generation with mandatory source referencing. M10 can now ONLY generate answers from provided retrieval information and MUST reference all sources.

## 🚫 ABSOLUTE RESTRICTIONS

### What M10 CANNOT Do:
- ❌ **Use external knowledge** or information from training data
- ❌ **Make assumptions** or inferences beyond what evidence explicitly states
- ❌ **Fill gaps** with external information when evidence is insufficient
- ❌ **Speculate** or provide information not directly supported by evidence
- ❌ **Add facts, data, or explanations** not present in retrieval sources
- ❌ **Supplement incomplete information** with training knowledge
- ❌ **Create connections** between evidence items using external knowledge

## ✅ MANDATORY REQUIREMENTS

### What M10 MUST Do:
- ✅ **Use ONLY retrieval evidence** for all information in answers
- ✅ **Cite EVERY piece of information** with specific evidence IDs
- ✅ **Reference ALL sources** used in the answer
- ✅ **Acknowledge insufficient evidence** when retrieval is incomplete
- ✅ **Preserve source citations** when synthesizing multiple components
- ✅ **Be explicit about limitations** due to missing evidence

## 📝 Updated Prompts

### 1. `m10_evidence_analysis`
**Key Changes:**
- 🚫 CANNOT supplement evaluation with external knowledge
- 🚫 CANNOT assume information not in evidence text
- ✅ MUST evaluate ONLY evidence content
- ✅ MUST extract ONLY explicit information from text

**Purpose:** Analyze evidence items strictly based on their content without external knowledge supplementation.

### 2. `m10_content_generation`
**Key Changes:**
- 🚫 CANNOT use external knowledge or training data
- 🚫 CANNOT make assumptions beyond evidence
- 🚫 CANNOT fill gaps with external information
- ✅ MUST cite EVERY piece of information with evidence IDs
- ✅ MUST acknowledge when evidence is insufficient
- ✅ MUST reference sources for all claims

**Purpose:** Generate answers using ONLY retrieval evidence with mandatory source citations.

### 3. `m10_answer_synthesis`
**Key Changes:**
- 🚫 CANNOT add information not present in answer components
- 🚫 CANNOT use external knowledge to fill gaps between components
- 🚫 CANNOT make connections not supported by retrieved information
- ✅ MUST preserve ALL original citations from components
- ✅ MUST maintain source references in final answer
- ✅ MUST acknowledge information gaps explicitly

**Purpose:** Synthesize multiple answer components while preserving all source references and avoiding external knowledge.

## 🔗 Citation Requirements

### Mandatory Citation Format:
```
Every factual statement: "Fact [Evidence ID: ev_xxx]"
Multiple sources: "Fact1 [Evidence ID: ev_001] and Fact2 [Evidence ID: ev_002]"
Conflicting sources: "According to [Evidence ID: ev_001], X. However, [Evidence ID: ev_002] states Y"
```

### Citation Tracking:
- **evidence_id**: Exact ID of the source evidence item
- **span_start**: Character position where cited information begins
- **span_end**: Character position where cited information ends

### Examples:
✅ **CORRECT**: "Solar panels reduce costs by 70% [Evidence ID: ev_001]"
❌ **WRONG**: "Solar panels reduce costs by 70% and are environmentally friendly" (missing citation)

## ⚠️ Insufficient Evidence Handling

### Response Templates:

#### No Evidence Available:
```
"Based on the available retrieval sources, I cannot provide an answer to this question because no relevant evidence was found."
```

#### Partial Evidence Only:
```
"Based on the available retrieval sources, I can address [specific aspects] but cannot provide complete information about [missing aspects] due to insufficient evidence."
```

#### Low Quality Evidence:
```
"The available evidence provides limited information: [what's available with citations]. However, this is insufficient for a comprehensive answer."
```

#### Evidence Doesn't Match Query:
```
"The available retrieval sources do not contain information that directly addresses this specific question."
```

## 📊 Answer Generation Process

### 1. Evidence Analysis (Retrieval-Only)
- Evaluate ONLY content present in evidence text
- Extract key points directly from evidence
- Assess quality based on text clarity and detail
- No external knowledge supplementation

### 2. Content Generation (Evidence-Only)
- Use ONLY information from provided evidence
- Include evidence ID citations for every fact
- Acknowledge limitations when evidence is insufficient
- Never supplement with external knowledge

### 3. Answer Synthesis (Source-Preserving)
- Combine components while preserving ALL citations
- Maintain source references from all components
- Acknowledge gaps when information is missing
- No external connections between evidence items

## 🎯 Quality Verification

### Every Answer Must:
1. **Trace back to evidence**: Every sentence must reference specific evidence
2. **Include citations**: Every factual claim must have evidence ID citation
3. **Acknowledge limitations**: Explicitly state when evidence is insufficient
4. **Preserve sources**: All source references must be maintained

### Verification Checklist:
- [ ] All information comes from retrieval evidence
- [ ] Every fact includes evidence ID citation
- [ ] No external knowledge added
- [ ] Limitations clearly acknowledged
- [ ] Source references preserved in synthesis

## 🔍 Example Scenarios

### Complete Evidence - Good Answer:
**Query**: "What are the benefits of solar energy?"
**Evidence**: Cost savings and environmental data
**Answer**: "Solar energy provides significant benefits according to the retrieval sources. Solar panels reduce electricity bills by 70-90% [Evidence ID: ev_001] and produce zero emissions during operation [Evidence ID: ev_002]."

### Partial Evidence - Limited Answer:
**Query**: "How do electric cars compare to gas cars?"
**Evidence**: Only cost information available
**Answer**: "Based on the available retrieval sources, I can provide cost information but cannot address environmental comparisons due to insufficient evidence. Electric vehicles cost $5,000 more upfront but save $1,200 annually [Evidence ID: ev_003]."

### No Evidence - Cannot Answer:
**Query**: "What are the latest fusion energy developments?"
**Evidence**: None available
**Answer**: "Based on the available retrieval sources, I cannot provide an answer to this question because no relevant evidence was found."

## 🎯 Benefits

### For Answer Quality:
- **Accuracy**: All information is verifiable through source citations
- **Transparency**: Users can trace every fact to its source
- **Reliability**: No hallucination or external knowledge contamination
- **Trust**: Clear acknowledgment of limitations builds user confidence

### For System Integrity:
- **Traceability**: Every piece of information has a clear source
- **Auditability**: All answers can be verified against retrieval sources
- **Consistency**: No variation based on external knowledge
- **Reliability**: Predictable behavior based only on provided evidence

### For Debugging:
- **Source Tracking**: Easy to identify which evidence contributed what information
- **Gap Identification**: Clear visibility into missing information
- **Quality Assessment**: Evidence quality directly impacts answer quality
- **Error Isolation**: Problems can be traced to specific evidence items

This implementation ensures M10 operates as a pure retrieval-based answer generator that maintains complete transparency and traceability while never supplementing with external knowledge.