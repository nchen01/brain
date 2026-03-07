#!/usr/bin/env python3
"""
Test M9's WorkUnit feedback system for M1 and M12.
Demonstrates how M9 analyzes WorkUnit performance and provides detailed feedback.
"""

def simulate_workunit_feedback_scenarios():
    """Simulate different WorkUnit performance scenarios and M9's feedback."""
    
    print("🧪 M9 WORKUNIT FEEDBACK SYSTEM TEST")
    print("=" * 50)
    
    print("\n📋 FEEDBACK SYSTEM OVERVIEW:")
    print("-" * 30)
    print("M9 now analyzes WorkUnit performance and provides detailed feedback:")
    print("• For M1: Specific guidance on how to improve sub-questions")
    print("• For M12: Explanation of why retrieval failed")
    print()
    
    scenarios = [
        {
            "name": "Poor Quality WorkUnits",
            "workunits": [
                {"id": "wu1", "text": "What is it?", "evidence_count": 1, "avg_quality": 0.3},
                {"id": "wu2", "text": "How does this work?", "evidence_count": 0, "avg_quality": 0.0},
                {"id": "wu3", "text": "Tell me more", "evidence_count": 2, "avg_quality": 0.4}
            ],
            "overall_quality": 0.45,
            "coverage_score": 0.3,
            "turns": 2,
            "max_turns": 3
        },
        {
            "name": "Similar/Redundant WorkUnits",
            "workunits": [
                {"id": "wu1", "text": "What are the benefits of solar energy?", "evidence_count": 3, "avg_quality": 0.6},
                {"id": "wu2", "text": "What are solar energy benefits?", "evidence_count": 2, "avg_quality": 0.5},
                {"id": "wu3", "text": "How does solar power help?", "evidence_count": 4, "avg_quality": 0.7}
            ],
            "overall_quality": 0.55,
            "coverage_score": 0.4,
            "turns": 1,
            "max_turns": 3
        },
        {
            "name": "Max Turns Reached - Failed Retrieval",
            "workunits": [
                {"id": "wu1", "text": "Complex technical question", "evidence_count": 0, "avg_quality": 0.0},
                {"id": "wu2", "text": "Another difficult query", "evidence_count": 1, "avg_quality": 0.2},
            ],
            "overall_quality": 0.25,
            "coverage_score": 0.2,
            "turns": 3,
            "max_turns": 3
        },
        {
            "name": "Good Quality - Success Case",
            "workunits": [
                {"id": "wu1", "text": "What are renewable energy sources?", "evidence_count": 5, "avg_quality": 0.8},
                {"id": "wu2", "text": "How do solar panels work?", "evidence_count": 4, "avg_quality": 0.7},
                {"id": "wu3", "text": "What are wind energy advantages?", "evidence_count": 3, "avg_quality": 0.9}
            ],
            "overall_quality": 0.82,
            "coverage_score": 0.85,
            "turns": 2,
            "max_turns": 3
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("=" * 40)
        
        # Simulate M9's analysis
        workunit_feedback = analyze_workunit_performance(scenario["workunits"])
        routing_decision = make_routing_decision(scenario, workunit_feedback)
        
        print(f"Overall Quality: {scenario['overall_quality']:.3f}")
        print(f"Coverage Score: {scenario['coverage_score']:.3f}")
        print(f"Turns: {scenario['turns']}/{scenario['max_turns']}")
        print()
        
        print("🔍 WORKUNIT ANALYSIS:")
        print("-" * 20)
        for wu in scenario["workunits"]:
            effectiveness = get_effectiveness(wu["avg_quality"], wu["evidence_count"])
            print(f"• {wu['text'][:40]}...")
            print(f"  Evidence: {wu['evidence_count']}, Quality: {wu['avg_quality']:.2f}, Status: {effectiveness}")
        print()
        
        print("⚠️  ISSUES IDENTIFIED:")
        for issue in workunit_feedback["issues_identified"]:
            print(f"• {issue}")
        print()
        
        print("💡 IMPROVEMENT SUGGESTIONS:")
        for suggestion in workunit_feedback["improvement_suggestions"]:
            print(f"• {suggestion}")
        print()
        
        print(f"🛣️  ROUTING DECISION: → {routing_decision['next_module']}")
        print(f"Reason: {routing_decision['reason']}")
        
        if routing_decision['next_module'] == 'M1':
            print("\n📤 FEEDBACK FOR M1 (Query Refinement):")
            guidance = routing_decision.get('refinement_guidance', {})
            print("Current Approach Issues:")
            for issue in guidance.get('current_approach_issues', []):
                print(f"  • {issue}")
            print("Suggested Improvements:")
            for improvement in guidance.get('suggested_improvements', []):
                print(f"  • {improvement}")
            print("Alternative Strategies:")
            for strategy in guidance.get('alternative_strategies', []):
                print(f"  • {strategy}")
                
        elif routing_decision['next_module'] == 'M12':
            print("\n📤 FEEDBACK FOR M12 (User Communication):")
            limitations = routing_decision.get('retrieval_limitations', {})
            print(f"Message: {routing_decision.get('message_for_m12', 'No message')}")
            print("Retrieval Limitations:")
            print(f"  • Max turns reached: {limitations.get('max_turns_reached', False)}")
            print(f"  • Final quality: {limitations.get('final_quality', 0):.3f}")
            print("Evidence Gaps:")
            for gap in limitations.get('evidence_gaps', []):
                print(f"  • {gap}")
        
        print("\n" + "─" * 50)


def analyze_workunit_performance(workunits):
    """Simulate M9's WorkUnit performance analysis."""
    
    total_workunits = len(workunits)
    issues = []
    suggestions = []
    
    # Analyze individual WorkUnits
    low_quality_count = sum(1 for wu in workunits if wu["avg_quality"] < 0.5)
    no_evidence_count = sum(1 for wu in workunits if wu["evidence_count"] == 0)
    
    # Identify issues
    if low_quality_count > total_workunits * 0.5:
        issues.append("Majority of sub-questions producing low-quality evidence")
        suggestions.append("Reformulate sub-questions to be more specific and answerable")
    
    if no_evidence_count > 0:
        issues.append(f"{no_evidence_count} sub-questions retrieved no evidence")
        suggestions.append("Replace unanswerable sub-questions with alternative approaches")
    
    # Check for similarity (simplified)
    texts = [wu["text"].lower() for wu in workunits]
    if len(set(texts)) < len(texts):
        issues.append("Some sub-questions are duplicates")
        suggestions.append("Generate more diverse sub-questions")
    
    # Check for vague questions
    vague_indicators = ["what is it", "how does this", "tell me more", "explain"]
    vague_count = sum(1 for wu in workunits 
                     if any(indicator in wu["text"].lower() for indicator in vague_indicators))
    
    if vague_count > 0:
        issues.append("Some sub-questions are too vague or unclear")
        suggestions.append("Make sub-questions more specific and focused")
    
    return {
        "total_workunits": total_workunits,
        "issues_identified": issues,
        "improvement_suggestions": suggestions,
        "performance_metrics": {
            "avg_evidence_per_workunit": sum(wu["evidence_count"] for wu in workunits) / total_workunits,
            "avg_quality_across_workunits": sum(wu["avg_quality"] for wu in workunits) / total_workunits,
            "successful_workunits": sum(1 for wu in workunits if wu["avg_quality"] >= 0.6),
            "failed_workunits": sum(1 for wu in workunits if wu["evidence_count"] == 0)
        }
    }


def make_routing_decision(scenario, workunit_feedback):
    """Simulate M9's routing decision with enhanced feedback."""
    
    quality_threshold = 0.7
    overall_quality = scenario["overall_quality"]
    current_turns = scenario["turns"]
    max_turns = scenario["max_turns"]
    
    # Path 2: Max turns reached
    if current_turns >= max_turns:
        if overall_quality < quality_threshold:
            message = f"Unable to find sufficient relevant data after {max_turns} retrieval attempts."
        else:
            message = f"Retrieval completed after {max_turns} attempts."
        
        return {
            "next_module": "M12",
            "reason": f"Maximum retrieval turns ({max_turns}) reached",
            "message_for_m12": message,
            "retrieval_limitations": {
                "max_turns_reached": True,
                "final_quality": overall_quality,
                "evidence_gaps": ["Insufficient high-quality sources", "Limited topic coverage"],
                "quality_distribution": {"high": 1, "medium": 2, "low": 3}
            }
        }
    
    # Path 3: Good quality
    if overall_quality >= quality_threshold:
        return {
            "next_module": "M10",
            "reason": f"Evidence quality sufficient ({overall_quality:.3f})"
        }
    
    # Path 1: Poor quality, refine
    return {
        "next_module": "M1",
        "reason": f"Evidence quality insufficient ({overall_quality:.3f}), refining query",
        "refinement_guidance": {
            "current_approach_issues": workunit_feedback["issues_identified"],
            "suggested_improvements": workunit_feedback["improvement_suggestions"],
            "evidence_gaps": ["Missing key information", "Poor source quality"],
            "quality_problems": ["Low evidence scores", "Incomplete coverage"],
            "alternative_strategies": [
                "Try broader, more general sub-questions",
                "Focus on fundamental concepts",
                "Use more common terminology"
            ]
        }
    }


def get_effectiveness(avg_quality, evidence_count):
    """Determine WorkUnit effectiveness."""
    if evidence_count == 0:
        return "failed"
    elif avg_quality < 0.5:
        return "poor"
    elif avg_quality < 0.7:
        return "moderate"
    else:
        return "good"


def show_state_information_structure():
    """Show the structure of state information M9 provides."""
    
    print("\n📊 STATE INFORMATION STRUCTURE:")
    print("=" * 50)
    
    print("\n🔄 FOR M1 (Query Refinement):")
    print("-" * 30)
    print("state.routing_decision = {")
    print("  'next_module': 'M1',")
    print("  'reason': 'Evidence quality insufficient',")
    print("  'workunit_feedback': {")
    print("    'total_workunits': 3,")
    print("    'workunit_analysis': {")
    print("      'wu1': {")
    print("        'text': 'What is renewable energy?',")
    print("        'evidence_count': 2,")
    print("        'avg_quality': 0.45,")
    print("        'effectiveness': 'poor',")
    print("        'issues': ['Low quality evidence', 'Too broad']")
    print("      }")
    print("    },")
    print("    'issues_identified': ['Vague sub-questions', 'Poor coverage'],")
    print("    'improvement_suggestions': ['Be more specific', 'Focus on facts']")
    print("  },")
    print("  'refinement_guidance': {")
    print("    'current_approach_issues': [...],")
    print("    'suggested_improvements': [...],")
    print("    'alternative_strategies': [...]")
    print("  }")
    print("}")
    
    print("\n🛑 FOR M12 (User Communication):")
    print("-" * 30)
    print("state.routing_decision = {")
    print("  'next_module': 'M12',")
    print("  'reason': 'Maximum retrieval turns reached',")
    print("  'message_for_m12': 'Unable to find sufficient relevant data...',")
    print("  'workunit_feedback': {")
    print("    'performance_metrics': {")
    print("      'failed_workunits': 2,")
    print("      'avg_quality_across_workunits': 0.25")
    print("    }")
    print("  },")
    print("  'retrieval_limitations': {")
    print("    'max_turns_reached': True,")
    print("    'final_quality': 0.35,")
    print("    'evidence_gaps': ['Missing technical details', 'No expert sources'],")
    print("    'quality_distribution': {'high': 0, 'medium': 1, 'low': 4}")
    print("  }")
    print("}")


def main():
    """Run WorkUnit feedback system test."""
    
    # Show feedback scenarios
    simulate_workunit_feedback_scenarios()
    
    # Show state information structure
    show_state_information_structure()
    
    print("\n🎯 KEY BENEFITS:")
    print("=" * 50)
    print("✅ M1 receives specific guidance on how to improve sub-questions")
    print("✅ M12 gets detailed explanation of why retrieval failed")
    print("✅ WorkUnit performance analysis identifies specific issues")
    print("✅ Alternative strategies suggested based on failure patterns")
    print("✅ Quality problems clearly categorized and explained")
    print("✅ Evidence gaps identified for better user communication")


if __name__ == "__main__":
    main()