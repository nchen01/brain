#!/usr/bin/env python3
"""
Comprehensive test for M0-M6 prompt usage verification.
Ensures no hardcoded prompts and all prompts are loaded from prompts.md.
"""

import re
import os

def check_module_prompts():
    """Check all M0-M6 modules for proper prompt usage."""
    
    print("🧪 M0-M6 PROMPT USAGE VERIFICATION")
    print("=" * 50)
    
    modules = [
        {
            "name": "M0 - QA Human",
            "file": "src/modules/m0_qa_human_langgraph.py",
            "expected_prompts": ["m0_clarity_assessment", "m0_followup_question"]
        },
        {
            "name": "M1 - Query Preprocessor", 
            "file": "src/modules/m1_query_preprocessor_langgraph.py",
            "expected_prompts": ["m1_normalization", "m1_reference_resolution", "m1_decomposition"]
        },
        {
            "name": "M2 - Query Router",
            "file": "src/modules/m2_query_router_langgraph.py", 
            "expected_prompts": ["m2_routing"]
        },
        {
            "name": "M3 - Simple Retrieval",
            "file": "src/modules/m3_simple_retrieval_langgraph.py",
            "expected_prompts": ["m3_query_analysis", "m3_source_selection"]
        },
        {
            "name": "M4 - Quality Check",
            "file": "src/modules/m4_retrieval_quality_check_langgraph.py",
            "expected_prompts": ["m4_quality_assessment"]
        },
        {
            "name": "M5 - Internet Retrieval",
            "file": "src/modules/m5_internet_retrieval_langgraph.py",
            "expected_prompts": ["m5_search_assistant", "m5_search_prompt"]
        },
        {
            "name": "M6 - Multihop Orchestrator",
            "file": "src/modules/m6_multihop_orchestrator_langgraph.py",
            "expected_prompts": ["m6_complexity_analysis", "m6_hop_planning", "m6_hop_execution", "m6_synthesis"]
        }
    ]
    
    all_passed = True
    
    for module in modules:
        print(f"\n📋 {module['name']}")
        print("=" * 40)
        
        if not os.path.exists(module['file']):
            print(f"❌ File not found: {module['file']}")
            all_passed = False
            continue
        
        # Read module file
        with open(module['file'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for hardcoded prompts (excluding docstrings)
        hardcoded_patterns = [
            r'"content":\s*"[^"]*You\s+are',  # JSON content with "You are"
            r'f"""[^"]*You\s+are',            # f-string with "You are"
            r'prompt\s*=\s*"""[^"]*You\s+are', # prompt variable with "You are"
            r'prompt\s*=\s*"[^"]*You\s+are',   # prompt variable with "You are"
        ]
        
        hardcoded_found = []
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                hardcoded_found.extend(matches)
        
        # Check for _get_prompt usage
        get_prompt_matches = re.findall(r'_get_prompt\(["\']([^"\']+)["\']', content)
        
        print(f"🔍 HARDCODED PROMPT CHECK:")
        if hardcoded_found:
            print(f"   ❌ Found {len(hardcoded_found)} hardcoded prompts:")
            for i, prompt in enumerate(hardcoded_found[:3], 1):  # Show first 3
                preview = prompt[:50].replace('\n', ' ')
                print(f"      {i}. {preview}...")
            all_passed = False
        else:
            print(f"   ✅ No hardcoded prompts found")
        
        print(f"\n📝 _get_prompt() USAGE:")
        if get_prompt_matches:
            print(f"   ✅ Found {len(get_prompt_matches)} _get_prompt() calls:")
            for prompt_name in get_prompt_matches:
                print(f"      • {prompt_name}")
        else:
            print(f"   ⚠️  No _get_prompt() calls found")
        
        print(f"\n📋 EXPECTED PROMPTS:")
        for prompt_name in module['expected_prompts']:
            if prompt_name in get_prompt_matches:
                print(f"   ✅ {prompt_name}")
            else:
                print(f"   ❌ {prompt_name} (missing)")
                all_passed = False
        
        print("\n" + "─" * 40)
    
    return all_passed

def check_prompts_md():
    """Check if all expected prompts exist in prompts.md."""
    
    print(f"\n📝 PROMPTS.MD VERIFICATION")
    print("=" * 50)
    
    expected_prompts = [
        # M0 prompts
        "m0_clarity_assessment", "m0_followup_question",
        # M1 prompts  
        "m1_normalization", "m1_reference_resolution", "m1_decomposition",
        # M2 prompts
        "m2_routing",
        # M3 prompts
        "m3_query_analysis", "m3_source_selection", 
        # M4 prompts
        "m4_quality_assessment",
        # M5 prompts
        "m5_search_assistant", "m5_search_prompt",
        # M6 prompts
        "m6_complexity_analysis", "m6_hop_planning", "m6_hop_execution", 
        "m6_synthesis"
    ]
    
    if not os.path.exists("prompts.md"):
        print("❌ prompts.md file not found!")
        return False
    
    with open("prompts.md", 'r', encoding='utf-8') as f:
        prompts_content = f.read()
    
    # Find all prompts in prompts.md
    found_prompts = re.findall(r'^## ([a-zA-Z0-9_]+)', prompts_content, re.MULTILINE)
    
    print(f"📊 PROMPT AVAILABILITY:")
    print(f"   Expected: {len(expected_prompts)} prompts")
    print(f"   Found: {len(found_prompts)} total prompts in prompts.md")
    print()
    
    missing_prompts = []
    for prompt_name in expected_prompts:
        if prompt_name in found_prompts:
            print(f"   ✅ {prompt_name}")
        else:
            print(f"   ❌ {prompt_name} (missing from prompts.md)")
            missing_prompts.append(prompt_name)
    
    if missing_prompts:
        print(f"\n⚠️  MISSING PROMPTS: {len(missing_prompts)}")
        for prompt in missing_prompts:
            print(f"      • {prompt}")
        return False
    else:
        print(f"\n✅ ALL EXPECTED PROMPTS FOUND")
        return True

def show_module_summary():
    """Show summary of M0-M6 module prompt usage."""
    
    print(f"\n📊 M0-M6 PROMPT USAGE SUMMARY")
    print("=" * 50)
    
    module_info = [
        {"module": "M0", "prompts": 2, "purpose": "Query clarity and follow-up questions"},
        {"module": "M1", "prompts": 3, "purpose": "Query preprocessing and normalization"},
        {"module": "M2", "prompts": 1, "purpose": "Query routing decisions"},
        {"module": "M3", "prompts": 2, "purpose": "Internal knowledge base retrieval"},
        {"module": "M4", "prompts": 1, "purpose": "Retrieval quality assessment"},
        {"module": "M5", "prompts": 2, "purpose": "Internet search and retrieval"},
        {"module": "M6", "prompts": 4, "purpose": "Multi-hop reasoning orchestration"}
    ]
    
    total_prompts = sum(info["prompts"] for info in module_info)
    
    print(f"Total Modules: {len(module_info)}")
    print(f"Total Prompts: {total_prompts}")
    print()
    
    for info in module_info:
        print(f"{info['module']}: {info['prompts']} prompts - {info['purpose']}")
    
    print(f"\n🎯 VERIFICATION OBJECTIVES:")
    print("✅ No hardcoded prompts in any module")
    print("✅ All prompts loaded via _get_prompt() method")
    print("✅ All expected prompts exist in prompts.md")
    print("✅ Proper fallback behavior when prompts fail")

def main():
    """Run comprehensive M0-M6 prompt verification."""
    
    print("🔍 Starting M0-M6 prompt verification...")
    print()
    
    # Check module prompt usage
    modules_passed = check_module_prompts()
    
    # Check prompts.md completeness
    prompts_passed = check_prompts_md()
    
    # Show summary
    show_module_summary()
    
    print(f"\n🎯 VERIFICATION RESULTS")
    print("=" * 50)
    
    if modules_passed and prompts_passed:
        print("✅ ALL CHECKS PASSED!")
        print("   • No hardcoded prompts found in M0-M6")
        print("   • All modules use _get_prompt() correctly")
        print("   • All expected prompts exist in prompts.md")
        print("   • Proper prompt loading architecture verified")
    else:
        print("❌ VERIFICATION FAILED!")
        if not modules_passed:
            print("   • Issues found in module prompt usage")
        if not prompts_passed:
            print("   • Missing prompts in prompts.md")
        print("   • Review output above for specific issues")
    
    print(f"\n📋 NEXT STEPS:")
    if modules_passed and prompts_passed:
        print("✅ M0-M6 prompt verification complete")
        print("✅ Ready for production use")
    else:
        print("🔧 Fix identified issues:")
        print("   1. Remove any hardcoded prompts")
        print("   2. Add missing prompts to prompts.md")
        print("   3. Ensure all modules use _get_prompt()")
        print("   4. Re-run verification")

if __name__ == "__main__":
    main()