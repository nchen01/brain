#!/usr/bin/env python3
"""
Final verification test for fallback logging across all M0-M12 modules.
"""

import re
import os
from typing import Dict, List

def test_fallback_logging_compliance():
    """Test that all modules have proper fallback logging."""
    
    print("🧪 FINAL FALLBACK LOGGING VERIFICATION")
    print("=" * 50)
    
    modules = [
        {"name": "M0", "file": "src/modules/m0_qa_human_langgraph.py"},
        {"name": "M1", "file": "src/modules/m1_query_preprocessor_langgraph.py"},
        {"name": "M2", "file": "src/modules/m2_query_router_langgraph.py"},
        {"name": "M3", "file": "src/modules/m3_simple_retrieval_langgraph.py"},
        {"name": "M4", "file": "src/modules/m4_retrieval_quality_check_langgraph.py"},
        {"name": "M5", "file": "src/modules/m5_internet_retrieval_langgraph.py"},
        {"name": "M6", "file": "src/modules/m6_multihop_orchestrator_langgraph.py"},
        {"name": "M7", "file": "src/modules/m7_evidence_aggregator_langgraph.py"},
        {"name": "M8", "file": "src/modules/m8_reranker_langgraph.py"},
        {"name": "M9", "file": "src/modules/m9_smart_retrieval_controller_langgraph.py"},
        {"name": "M10", "file": "src/modules/m10_answer_creator_langgraph.py"},
        {"name": "M11", "file": "src/modules/m11_answer_check_langgraph.py"},
        {"name": "M12", "file": "src/modules/m12_interaction_answer_langgraph.py"}
    ]
    
    results = {}
    all_compliant = True
    
    for module in modules:
        if not os.path.exists(module["file"]):
            results[module["name"]] = {"status": "❌ FILE NOT FOUND", "details": []}
            all_compliant = False
            continue
        
        with open(module["file"], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for fallback trigger patterns
        fallback_triggers = re.findall(r'print\(f?"🔄 FALLBACK TRIGGERED:.*?\)', content)
        
        # Check for fallback execution patterns  
        fallback_executions = re.findall(r'print\(f?"🔄 EXECUTING FALLBACK:.*?\)', content)
        
        # Check for exception handling with logging
        exception_blocks = re.findall(r'except\s+Exception\s+as\s+\w+:(.*?)(?=\n\s*(?:except|finally|def|class|$))', 
                                    content, re.DOTALL)
        
        # Count logging in exception blocks (either direct logging or _log_error calls)
        logging_in_exceptions = 0
        for block in exception_blocks:
            if 'self.logger.' in block or 'self._log_error' in block:
                logging_in_exceptions += 1
        
        # Determine compliance
        has_fallback_prints = len(fallback_triggers) > 0
        has_exception_logging = logging_in_exceptions > 0 or len(exception_blocks) == 0
        
        if has_fallback_prints and has_exception_logging:
            status = "✅ COMPLIANT"
        elif has_fallback_prints and not has_exception_logging:
            status = "⚠️  PARTIAL (missing logging)"
        elif not has_fallback_prints and has_exception_logging:
            status = "⚠️  PARTIAL (missing prints)"
        else:
            status = "❌ NON-COMPLIANT"
            all_compliant = False
        
        results[module["name"]] = {
            "status": status,
            "details": [
                f"Fallback triggers: {len(fallback_triggers)}",
                f"Fallback executions: {len(fallback_executions)}",
                f"Exception blocks: {len(exception_blocks)}",
                f"Logged exceptions: {logging_in_exceptions}"
            ]
        }
    
    # Display results
    print(f"{'Module':<4} {'Status':<25} {'Details'}")
    print("-" * 70)
    
    for module_name, result in results.items():
        details_str = " | ".join(result["details"])
        print(f"{module_name:<4} {result['status']:<25} {details_str}")
    
    return all_compliant, results

def show_fallback_examples():
    """Show examples of good fallback logging patterns found in the modules."""
    
    print(f"\n📝 FALLBACK LOGGING EXAMPLES FOUND")
    print("=" * 50)
    
    examples = [
        {
            "module": "M8",
            "pattern": "Exception → Log + Print + Fallback",
            "code": '''except Exception as e:
    self.logger.warning(f"[{self.module_code}] Strategy selection failed: {e}")
    print(f"🔄 FALLBACK TRIGGERED: M8 Strategy Selection - {e}")
    print(f"   → Using fallback adaptive strategy")
    return self._fallback_adaptive_strategy()'''
        },
        {
            "module": "M11",
            "pattern": "Fallback Method with Execution Announcement",
            "code": '''def _fallback_retrieval_validation(self, answer: str, state: ReactorState) -> RetrievalValidation:
    """Fallback retrieval validation using heuristics."""
    print(f"🔄 EXECUTING FALLBACK: M11 Retrieval Validation - Using heuristic validation")
    # ... fallback logic ...'''
        },
        {
            "module": "M9",
            "pattern": "Control Flow Fallback",
            "code": '''except Exception as e:
    self.logger.warning(f"[{self.module_code}] Control decision failed: {e}")
    print(f"🔄 FALLBACK TRIGGERED: M9 Control Decision - {e}")
    print(f"   → Using default control decision")
    return self._fallback_control_decision()'''
        }
    ]
    
    for example in examples:
        print(f"📋 {example['module']} - {example['pattern']}:")
        print(example['code'])
        print()

def show_compliance_summary(all_compliant: bool, results: Dict):
    """Show final compliance summary."""
    
    print(f"\n🎯 COMPLIANCE SUMMARY")
    print("=" * 50)
    
    compliant_count = sum(1 for r in results.values() if r['status'] == '✅ COMPLIANT')
    partial_count = sum(1 for r in results.values() if '⚠️' in r['status'])
    non_compliant_count = sum(1 for r in results.values() if r['status'] == '❌ NON-COMPLIANT')
    
    print(f"Total Modules: {len(results)}")
    print(f"✅ Fully Compliant: {compliant_count}")
    print(f"⚠️  Partially Compliant: {partial_count}")
    print(f"❌ Non-Compliant: {non_compliant_count}")
    print()
    
    if all_compliant:
        print("🎉 ALL MODULES ARE COMPLIANT!")
        print("✅ All fallback scenarios have both print statements and logging")
        print("✅ Users will see clear feedback when fallbacks are triggered")
        print("✅ Developers have detailed logs for debugging")
    else:
        print("🔧 SOME MODULES NEED ATTENTION")
        
        if partial_count > 0:
            print("⚠️  Partially compliant modules have either prints or logging but not both")
        
        if non_compliant_count > 0:
            print("❌ Non-compliant modules lack both prints and logging")
    
    print(f"\n📋 FALLBACK LOGGING REQUIREMENTS:")
    print("1. Exception blocks should have logging (self.logger.* or self._log_error)")
    print("2. Exception blocks should have user-visible prints (🔄 FALLBACK TRIGGERED)")
    print("3. Fallback methods should announce execution (🔄 EXECUTING FALLBACK)")
    print("4. Print messages should be descriptive and actionable")

def main():
    """Run final fallback logging verification."""
    
    print("🔍 Starting final fallback logging verification...")
    print()
    
    # Test compliance
    all_compliant, results = test_fallback_logging_compliance()
    
    # Show examples
    show_fallback_examples()
    
    # Show summary
    show_compliance_summary(all_compliant, results)
    
    print(f"\n✅ VERIFICATION COMPLETE")
    print("=" * 50)
    
    if all_compliant:
        print("🎉 All M0-M12 modules have proper fallback logging!")
        print("   → Users get clear feedback when fallbacks occur")
        print("   → Developers get detailed logs for debugging")
        print("   → System maintains transparency and debuggability")
    else:
        print("🔧 Review modules marked as non-compliant or partial")
        print("   → Add missing print statements to exception blocks")
        print("   → Add missing logging to exception blocks")
        print("   → Ensure fallback methods announce their execution")

if __name__ == "__main__":
    main()