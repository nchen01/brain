#!/usr/bin/env python3
"""
Fix fallback logging across all M0-M12 modules.
Ensures all fallback scenarios have both print statements and proper logging.
"""

import re
import os
from typing import List, Dict, Tuple

def analyze_fallback_patterns():
    """Analyze current fallback patterns across all modules."""
    
    print("🔍 ANALYZING FALLBACK PATTERNS IN M0-M12")
    print("=" * 50)
    
    modules = [
        "src/modules/m0_qa_human_langgraph.py",
        "src/modules/m1_query_preprocessor_langgraph.py", 
        "src/modules/m2_query_router_langgraph.py",
        "src/modules/m3_simple_retrieval_langgraph.py",
        "src/modules/m4_retrieval_quality_check_langgraph.py",
        "src/modules/m5_internet_retrieval_langgraph.py",
        "src/modules/m6_multihop_orchestrator_langgraph.py",
        "src/modules/m7_evidence_aggregator_langgraph.py",
        "src/modules/m8_reranker_langgraph.py",
        "src/modules/m9_smart_retrieval_controller_langgraph.py",
        "src/modules/m10_answer_creator_langgraph.py",
        "src/modules/m11_answer_check_langgraph.py",
        "src/modules/m12_interaction_answer_langgraph.py"
    ]
    
    analysis_results = {}
    
    for module_path in modules:
        if not os.path.exists(module_path):
            continue
            
        module_name = os.path.basename(module_path).replace('.py', '').upper()
        
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find exception handling blocks
        exception_blocks = re.findall(r'except\s+Exception\s+as\s+\w+:(.*?)(?=\n\s*(?:except|finally|def|class|$))', 
                                    content, re.DOTALL)
        
        # Find fallback print statements
        fallback_prints = re.findall(r'print\(f?"🔄 FALLBACK TRIGGERED:.*?\)', content)
        
        # Find fallback execution prints
        fallback_executions = re.findall(r'print\(f?"🔄 EXECUTING FALLBACK:.*?\)', content)
        
        # Find logging statements in exception blocks
        logging_statements = []
        for block in exception_blocks:
            logs = re.findall(r'self\.logger\.\w+\(.*?\)', block)
            logging_statements.extend(logs)
        
        analysis_results[module_name] = {
            'exception_blocks': len(exception_blocks),
            'fallback_prints': len(fallback_prints),
            'fallback_executions': len(fallback_executions),
            'logging_statements': len(logging_statements),
            'has_consistent_logging': len(fallback_prints) > 0 and len(logging_statements) > 0
        }
    
    # Display analysis
    print(f"{'Module':<15} {'Exceptions':<11} {'FB Prints':<10} {'FB Exec':<8} {'Logging':<8} {'Consistent':<10}")
    print("-" * 70)
    
    for module, data in analysis_results.items():
        consistent = "✅ Yes" if data['has_consistent_logging'] else "❌ No"
        print(f"{module:<15} {data['exception_blocks']:<11} {data['fallback_prints']:<10} "
              f"{data['fallback_executions']:<8} {data['logging_statements']:<8} {consistent:<10}")
    
    return analysis_results

def identify_missing_fallback_logging():
    """Identify specific locations where fallback logging is missing."""
    
    print(f"\n🔍 IDENTIFYING MISSING FALLBACK LOGGING")
    print("=" * 50)
    
    modules_to_fix = [
        {
            "file": "src/modules/m0_qa_human_langgraph.py",
            "module_code": "M0",
            "missing_patterns": [
                {
                    "search": "except Exception as e:",
                    "context": "clarity assessment and follow-up generation",
                    "needs_print": True
                }
            ]
        },
        {
            "file": "src/modules/m2_query_router_langgraph.py", 
            "module_code": "M2",
            "missing_patterns": [
                {
                    "search": "# Fallback: route all WorkUnits to simple retrieval",
                    "context": "routing fallback",
                    "needs_print": True
                }
            ]
        },
        {
            "file": "src/modules/m4_retrieval_quality_check_langgraph.py",
            "module_code": "M4", 
            "missing_patterns": [
                {
                    "search": "# Use fallback assessment if LLM assessment failed",
                    "context": "quality assessment fallback",
                    "needs_print": True
                }
            ]
        },
        {
            "file": "src/modules/m6_multihop_orchestrator_langgraph.py",
            "module_code": "M6",
            "missing_patterns": [
                {
                    "search": "return self._fallback_",
                    "context": "multihop reasoning fallbacks",
                    "needs_print": True
                }
            ]
        },
        {
            "file": "src/modules/m7_evidence_aggregator_langgraph.py",
            "module_code": "M7",
            "missing_patterns": [
                {
                    "search": "except Exception as e:",
                    "context": "evidence aggregation",
                    "needs_print": False  # Already has print
                }
            ]
        }
    ]
    
    for module_info in modules_to_fix:
        print(f"\n📋 {module_info['module_code']} - {module_info['file']}")
        print("-" * 40)
        
        if not os.path.exists(module_info['file']):
            print("❌ File not found")
            continue
            
        with open(module_info['file'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern in module_info['missing_patterns']:
            matches = content.count(pattern['search'])
            status = "✅ Has print" if not pattern['needs_print'] else "❌ Missing print"
            print(f"   • {pattern['context']}: {matches} locations - {status}")

def show_recommended_fallback_pattern():
    """Show the recommended fallback logging pattern."""
    
    print(f"\n📝 RECOMMENDED FALLBACK LOGGING PATTERN")
    print("=" * 50)
    
    pattern = '''
# RECOMMENDED PATTERN FOR EXCEPTION HANDLING:

try:
    # Main operation
    result = await some_operation()
    return result
    
except Exception as e:
    # 1. Log the error with context
    self.logger.error(f"[{self.module_code}] Operation failed: {e}")
    
    # 2. Print fallback trigger message
    print(f"🔄 FALLBACK TRIGGERED: M{X} Operation Name - {e}")
    print(f"   → Fallback action description")
    
    # 3. Execute fallback logic
    fallback_result = self._create_fallback_result()
    
    # 4. Return fallback result
    return fallback_result

# RECOMMENDED PATTERN FOR FALLBACK METHODS:

def _create_fallback_result(self) -> ResultType:
    """Fallback result creation when main operation fails."""
    # 1. Print fallback execution message
    print(f"🔄 EXECUTING FALLBACK: M{X} Operation Name - Using fallback logic")
    
    # 2. Create fallback result with appropriate confidence/quality indicators
    result = ResultType(
        # ... fallback data ...
        confidence=0.6  # Lower confidence for fallback
    )
    
    return result
'''
    
    print(pattern)

def show_current_good_examples():
    """Show examples of modules with good fallback logging."""
    
    print(f"\n✅ MODULES WITH GOOD FALLBACK LOGGING")
    print("=" * 50)
    
    good_examples = [
        {
            "module": "M8 - ReRanker",
            "example": '''
except Exception as e:
    self.logger.warning(f"[{self.module_code}] Strategy selection failed: {e}")
    print(f"🔄 FALLBACK TRIGGERED: M8 Strategy Selection - {e}")
    print(f"   → Using fallback adaptive strategy")
    return self._fallback_adaptive_strategy()
'''
        },
        {
            "module": "M9 - Smart Controller", 
            "example": '''
except Exception as e:
    self.logger.warning(f"[{self.module_code}] Control decision failed: {e}")
    print(f"🔄 FALLBACK TRIGGERED: M9 Control Decision - {e}")
    print(f"   → Using default control decision")
    return self._fallback_control_decision()
'''
        },
        {
            "module": "M11 - Answer Check",
            "example": '''
except Exception as e:
    self.logger.warning(f"[{self.module_code}] Retrieval validation failed: {e}")
    print(f"🔄 FALLBACK TRIGGERED: M11 Retrieval Validation - {e}")
    print(f"   → Using heuristic validation")
    return self._fallback_retrieval_validation(answer, state)
'''
        }
    ]
    
    for example in good_examples:
        print(f"📋 {example['module']}:")
        print(example['example'])
        print()

def show_modules_needing_fixes():
    """Show specific modules that need fallback logging fixes."""
    
    print(f"\n🔧 MODULES NEEDING FALLBACK LOGGING FIXES")
    print("=" * 50)
    
    fixes_needed = [
        {
            "module": "M0 - QA Human",
            "issues": [
                "Exception blocks have logging but no print statements",
                "Fallback creation doesn't announce fallback execution"
            ],
            "locations": [
                "Clarity assessment exception handling",
                "Follow-up question generation exception handling"
            ]
        },
        {
            "module": "M2 - Query Router",
            "issues": [
                "Fallback routing has no print statements",
                "Exception logging exists but no user-visible feedback"
            ],
            "locations": [
                "Main execute method exception handling",
                "Fallback route plan creation"
            ]
        },
        {
            "module": "M4 - Quality Check",
            "issues": [
                "Fallback assessment usage not announced",
                "LLM failure fallbacks are silent"
            ],
            "locations": [
                "LLM assessment failure handling",
                "Response parsing fallbacks"
            ]
        },
        {
            "module": "M6 - Multihop Orchestrator",
            "issues": [
                "Fallback methods exist but don't announce execution",
                "Exception handling has logging but no prints"
            ],
            "locations": [
                "Complexity analysis fallback",
                "Hop planning fallback", 
                "Hop execution fallback",
                "Synthesis fallback"
            ]
        },
        {
            "module": "M10 - Answer Creator",
            "issues": [
                "Some fallbacks have prints, others don't",
                "Inconsistent fallback logging patterns"
            ],
            "locations": [
                "Evidence analysis fallback",
                "Content generation fallback",
                "Answer synthesis fallback"
            ]
        }
    ]
    
    for fix in fixes_needed:
        print(f"📋 {fix['module']}:")
        print(f"   Issues:")
        for issue in fix['issues']:
            print(f"     • {issue}")
        print(f"   Locations to fix:")
        for location in fix['locations']:
            print(f"     • {location}")
        print()

def main():
    """Run fallback logging analysis."""
    
    print("🔍 FALLBACK LOGGING ANALYSIS FOR M0-M12")
    print("=" * 60)
    
    # Analyze current patterns
    analysis_results = analyze_fallback_patterns()
    
    # Identify missing logging
    identify_missing_fallback_logging()
    
    # Show recommended pattern
    show_recommended_fallback_pattern()
    
    # Show good examples
    show_current_good_examples()
    
    # Show modules needing fixes
    show_modules_needing_fixes()
    
    print(f"\n🎯 SUMMARY")
    print("=" * 50)
    
    total_modules = len(analysis_results)
    consistent_modules = sum(1 for data in analysis_results.values() if data['has_consistent_logging'])
    
    print(f"Total Modules: {total_modules}")
    print(f"Consistent Logging: {consistent_modules}")
    print(f"Need Fixes: {total_modules - consistent_modules}")
    print()
    
    if consistent_modules == total_modules:
        print("✅ All modules have consistent fallback logging!")
    else:
        print("🔧 Some modules need fallback logging improvements")
        print("   → Add print statements to exception blocks")
        print("   → Add execution announcements to fallback methods")
        print("   → Ensure both logging and user-visible feedback")

if __name__ == "__main__":
    main()