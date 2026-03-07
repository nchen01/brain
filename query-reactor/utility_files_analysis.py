#!/usr/bin/env python3
"""
Analysis of utility files to determine if they should be kept or removed.
"""

import os
from datetime import datetime

def analyze_utility_files():
    """Analyze utility files and provide recommendations."""
    
    print("🔍 UTILITY FILES ANALYSIS")
    print("=" * 50)
    
    files_to_analyze = [
        "cleanup_inventory.py",
        "cleanup_legacy_modules.py", 
        "m8_prompt_analysis.py",
        "organize_md_files.py",
        "organize_test_files.py"
    ]
    
    recommendations = {}
    
    for file in files_to_analyze:
        if os.path.exists(file):
            # Get file stats
            stat = os.stat(file)
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Analyze purpose and current relevance
            if file == "cleanup_inventory.py":
                recommendations[file] = {
                    "purpose": "Legacy module cleanup inventory and analysis",
                    "current_relevance": "LOW - Legacy cleanup already completed",
                    "recommendation": "REMOVE",
                    "reason": "Legacy cleanup tasks are complete, this was a one-time utility",
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M")
                }
            
            elif file == "cleanup_legacy_modules.py":
                recommendations[file] = {
                    "purpose": "Automated legacy module cleanup script",
                    "current_relevance": "LOW - Legacy cleanup already completed", 
                    "recommendation": "REMOVE",
                    "reason": "Legacy cleanup tasks are complete, this was a one-time utility",
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M")
                }
            
            elif file == "m8_prompt_analysis.py":
                recommendations[file] = {
                    "purpose": "M8 ReRanker prompt usage analysis",
                    "current_relevance": "LOW - Analysis already completed and documented",
                    "recommendation": "REMOVE",
                    "reason": "Analysis complete, results documented in M8_PROMPT_USAGE_SUMMARY.md",
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M")
                }
            
            elif file == "organize_md_files.py":
                recommendations[file] = {
                    "purpose": "Markdown file organization utility",
                    "current_relevance": "LOW - Organization task completed",
                    "recommendation": "REMOVE",
                    "reason": "MD file organization complete, results documented in MD_ORGANIZATION_SUMMARY.md",
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M")
                }
            
            elif file == "organize_test_files.py":
                recommendations[file] = {
                    "purpose": "Test file organization utility",
                    "current_relevance": "LOW - Organization task completed",
                    "recommendation": "REMOVE", 
                    "reason": "Test file organization complete, results documented in TEST_ORGANIZATION_SUMMARY.md",
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M")
                }
        else:
            recommendations[file] = {
                "purpose": "File not found",
                "current_relevance": "N/A",
                "recommendation": "N/A",
                "reason": "File does not exist",
                "size": 0,
                "modified": "N/A"
            }
    
    # Display analysis
    print(f"📊 ANALYSIS RESULTS:")
    print()
    
    for file, info in recommendations.items():
        print(f"📋 {file}")
        print(f"   Purpose: {info['purpose']}")
        print(f"   Current Relevance: {info['current_relevance']}")
        print(f"   Size: {info['size']} bytes")
        print(f"   Last Modified: {info['modified']}")
        print(f"   Recommendation: {info['recommendation']}")
        print(f"   Reason: {info['reason']}")
        print()
    
    # Summary
    remove_files = [f for f, info in recommendations.items() if info['recommendation'] == 'REMOVE']
    keep_files = [f for f, info in recommendations.items() if info['recommendation'] == 'KEEP']
    
    print("🎯 SUMMARY")
    print("=" * 50)
    print(f"Files to REMOVE: {len(remove_files)}")
    print(f"Files to KEEP: {len(keep_files)}")
    print()
    
    if remove_files:
        print("📋 FILES TO REMOVE:")
        for file in remove_files:
            print(f"   ❌ {file} - {recommendations[file]['reason']}")
        print()
        
        print("🔧 REMOVAL COMMANDS:")
        for file in remove_files:
            print(f"Remove-Item -Path \".\\{file}\" -Force")
    
    if keep_files:
        print("📋 FILES TO KEEP:")
        for file in keep_files:
            print(f"   ✅ {file} - {recommendations[file]['reason']}")
    
    return recommendations

def main():
    """Main analysis function."""
    recommendations = analyze_utility_files()
    
    print("\\n📝 DETAILED ANALYSIS:")
    print("=" * 50)
    print("All analyzed files are one-time utilities that served their purpose:")
    print()
    print("✅ COMPLETED TASKS:")
    print("   • Legacy module cleanup - DONE")
    print("   • M8 prompt analysis - DONE (documented)")
    print("   • MD file organization - DONE (documented)")
    print("   • Test file organization - DONE (documented)")
    print()
    print("📋 DOCUMENTATION PRESERVED:")
    print("   • MD_ORGANIZATION_SUMMARY.md - MD file organization results")
    print("   • TEST_ORGANIZATION_SUMMARY.md - Test file organization results")
    print("   • docs/misc/M8_PROMPT_USAGE_SUMMARY.md - M8 analysis results")
    print("   • docs/legacy/ - Legacy cleanup documentation")
    print()
    print("🎯 RECOMMENDATION: Remove all utility files as they are no longer needed")
    print("   The results of their work are preserved in documentation files.")

if __name__ == "__main__":
    main()