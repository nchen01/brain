# M11 Answer Check Gatekeeper Implementation

## Overview

M11 has been completely redesigned as a **gatekeeper** that validates M10's answers for retrieval compliance and makes intelligent routing decisions. M11 ensures answers are fully based on retrieval data before allowing them to proceed to users.

## 🚪 Gatekeeper Functionality

### Core Responsibility
M11 acts as a **strict gatekeeper** that:
- ✅ Validates answers are fully based on retrieval data
- ✅ Checks for proper evidence ID citations
- ✅ Makes routing decisions based on compliance
- ✅ Provides feedback to M10 for improvements
- ✅ Protects users from non-retrieval content

### 3-Path Routing Logic

#### **Path 1: ✅ Retrieval Compliant → Pass to M12**
- **Condition**: Answer is fully based on retrieval data (≥90% coverage) with proper citations
- **Action**: Pass to M12 with compliance confirmation
- **Message**: "Answer meets all retrieval requirements and is ready for user delivery"

#### **Path 2: 🔄 Not Compliant + Attempts Remaining → Return to M10**
- **Condition**: Answer not retrieval-compliant AND return attempts < max_attempts
- **Action**: Return to M10 with specific improvement guidance
- **Message**: "Answer needs improvement: [specific issues identified]"
- **Counter**: Increment return attempt counter

#### **Path 3: ⚠️ Max Attempts Reached → Pass to M12 with Issues**
- **Condition**: Answer not retrieval-compliant AND return attempts = max_attempts
- **Action**: Pass to M12 with detailed limitation notes
- **Message**: "Answer has limitations: [specific issues]. Some information may not be from retrieval sources."

## 🔍 Validation Process

### 1. **Retrieval Compliance Check**
- **Citation Analysis**: Validates evidence ID format `[Evidence ID: ev_xxx]`
- **Content Verification**: Compares answer content against provided evidence
- **External Knowledge Detection**: Identifies phrases indicating non-retrieval content
- **Coverage Calculation**: Determines percentage of answer based on retrieval

### 2. **Compliance Scoring**
- **Retrieval Coverage**: 0.0-1.0 (percentage based on retrieval data)
- **Citation Accuracy**: 0.0-1.0 (accuracy of evidence ID citations)
- **Evidence Support**: 0.0-1.0 (how well evidence supports claims)

### 3. **Issue Identification**
- **Non-Retrieval Parts**: Specific content not based on evidence
- **Missing Citations**: Claims without proper evidence ID references
- **External Knowledge Indicators**: Phrases like "generally known", "experts agree"

## ⚙️ Configuration

### Key Parameters:
- **Max Return Attempts**: 2 (configurable)
- **Compliance Threshold**: 0.9 (90% retrieval coverage required)
- **Citation Required**: True (evidence IDs mandatory)
- **Evidence ID Format**: `[Evidence ID: ev_xxx]`

### Decision Matrix:
| Compliance Status | Attempt Status | Decision | Action |
|------------------|----------------|----------|---------|
| ✅ Compliant | Any | Pass to M12 | Deliver to user |
| ❌ Non-compliant | < Max attempts | Return to M10 | Improve answer |
| ❌ Non-compliant | = Max attempts | Pass to M12* | Note limitations |

*With detailed limitation notes for user transparency

## 📝 Prompts Added to prompts.md

### 1. `m11_retrieval_validation` ⭐ **CRITICAL**
- **Purpose**: Core gatekeeper function - validates retrieval compliance
- **Input**: Answer + available evidence context
- **Output**: RetrievalValidation with compliance assessment
- **Usage**: `_validate_retrieval_compliance()` method

### 2. `m11_structure_analysis` (Legacy)
- **Purpose**: Analyze answer organization and clarity
- **Input**: Answer text
- **Output**: AnswerAnalysis with structure scores
- **Usage**: `_analyze_answer_structure()` method

### 3. `m11_accuracy_check` (Legacy)
- **Purpose**: Verify factual accuracy against evidence
- **Input**: Answer + evidence text
- **Output**: AccuracyCheck with verification results
- **Usage**: `_check_factual_accuracy()` method

### 4. `m11_citation_validation` (Legacy)
- **Purpose**: Assess citation quality and completeness
- **Input**: Answer + available evidence
- **Output**: CitationValidation with citation assessment
- **Usage**: `_validate_answer_citations()` method

### 5. `m11_completeness_assessment` (Legacy)
- **Purpose**: Evaluate query coverage completeness
- **Input**: Query + answer
- **Output**: CompletenessAssessment with coverage scores
- **Usage**: `_assess_answer_completeness()` method

## 🔄 Enhanced Fallback Logging

M11 now provides clear visibility into gatekeeper decisions:

```
🔄 FALLBACK TRIGGERED: M11 Retrieval Validation - LLM timeout
   → Using heuristic validation

🔄 M11 GATEKEEPER: Answer not retrieval-compliant (0.65)
   → Returning to M10 (attempt 1/2)

🔄 M11 GATEKEEPER: Max attempts reached (2)
   → Passing to M12 with limitation notes
```

## 📊 Validation Examples

### ✅ **Compliant Answer**:
```
"Solar energy provides significant benefits according to retrieval sources. 
Solar panels reduce electricity bills by 70-90% [Evidence ID: ev_001] and 
produce zero emissions during operation [Evidence ID: ev_002]."

Result: ✅ Pass to M12 - Fully retrieval-compliant
```

### ❌ **Non-Compliant Answer**:
```
"Solar energy is generally known to be beneficial. It's commonly understood 
that solar panels save money and help the environment."

Issues: No citations, external knowledge phrases
Result: 🔄 Return to M10 - Needs retrieval-based content
```

### ⚠️ **Max Attempts Reached**:
```
"Solar energy has benefits including cost savings [Evidence ID: ev_001]. 
It's widely recognized as environmentally friendly."

Issues: Mixed retrieval/external content, after 2 attempts
Result: ⚠️ Pass to M12 with limitations noted
```

## 🎯 State Information

### For M10 (Return Path):
```python
state.gatekeeper_decision = {
    "decision": "return_to_m10",
    "reason": "Answer not retrieval-compliant",
    "issues_found": ["Missing citations", "External knowledge detected"],
    "message_for_target": "Answer needs improvement: add evidence ID citations"
}
state.m11_return_attempts = 1  # Incremented counter
```

### For M12 (Pass Path):
```python
state.gatekeeper_decision = {
    "decision": "pass_to_m12",
    "retrieval_compliance": True,  # or False with limitations
    "message_for_target": "Answer meets all retrieval requirements" 
    # or "Answer has limitations: [specific issues]"
}
```

## 🔧 Implementation Details

### Workflow Changes:
- **Before**: Complex multi-node quality analysis workflow
- **After**: Streamlined 2-node gatekeeper workflow
  1. `validate_retrieval` - Check retrieval compliance
  2. `make_gatekeeper_decision` - Route based on compliance

### Key Methods:
- `_validate_retrieval_compliance()` - Core validation logic
- `_make_gatekeeper_routing_decision()` - Routing decision logic
- `_fallback_retrieval_validation()` - Heuristic fallback validation

### Error Handling:
- Comprehensive fallback methods for all validation steps
- Clear error messages for debugging
- Graceful degradation with appropriate routing decisions

## 🎯 Benefits

### **For System Integrity:**
- **Quality Assurance**: Ensures only retrieval-based answers reach users
- **Transparency**: Clear tracking of compliance and limitations
- **Reliability**: Consistent validation across all answers
- **Traceability**: Complete audit trail of gatekeeper decisions

### **For User Trust:**
- **Accuracy**: All delivered answers are evidence-based
- **Transparency**: Users know when information has limitations
- **Consistency**: Uniform quality standards across all responses
- **Reliability**: No external knowledge contamination

### **For Development:**
- **Debugging**: Clear visibility into validation failures
- **Monitoring**: Easy tracking of compliance rates
- **Optimization**: Feedback loop for improving M10 performance
- **Maintenance**: Simple gatekeeper logic easy to understand and modify

M11 now serves as a robust gatekeeper that maintains the integrity of the retrieval-based answer system while providing clear feedback for continuous improvement!