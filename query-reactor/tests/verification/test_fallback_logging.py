#!/usr/bin/env python3
"""
Test script to demonstrate enhanced fallback logging in QueryReactor modules.
This script intentionally triggers fallback scenarios to show the new logging.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import ReactorState, Query, WorkUnit, EvidenceItem
from src.modules.m8_reranker_langgraph import reranker_langgraph
from src.modules.m1_query_preprocessor_langgraph import query_preprocessor_langgraph
from src.modules.m5_internet_retrieval_langgraph import internet_retrieval_langgraph


async def test_fallback_scenarios():
    """Test various fallback scenarios to demonstrate enhanced logging."""
    
    print("🧪 TESTING ENHANCED FALLBACK LOGGING")
    print("=" * 50)
    
    # Create test state with minimal data to trigger fallbacks
    test_query = Query(
        id="test-fallback-001",
        text="What is quantum computing?",
        user_id="test-user",
        conversation_id="test-conv"
    )
    
    state = ReactorState(original_query=test_query)
    
    # Test 1: M8 with no evidence (should trigger fallbacks)
    print("\n📋 TEST 1: M8 ReRanker with no evidence")
    print("-" * 30)
    try:
        result_state = await reranker_langgraph.execute(state)
        print("✅ M8 completed (no fallbacks expected - no evidence to rank)")
    except Exception as e:
        print(f"❌ M8 failed: {e}")
    
    # Test 2: M8 with evidence but force API failures by corrupting config
    print("\n📋 TEST 2: M8 ReRanker with evidence (may trigger LLM fallbacks)")
    print("-" * 30)
    
    # Add some test evidence
    test_workunit = WorkUnit(
        id="test-wu-001",
        parent_query_id=test_query.id,
        text="What is quantum computing?",
        priority=1.0,
        complexity=0.5
    )
    state.add_workunit(test_workunit)
    
    # Add test evidence
    test_evidence = EvidenceItem(
        id="test-ev-001",
        workunit_id=test_workunit.id,
        title="Quantum Computing Basics",
        content="Quantum computing is a type of computation that harnesses quantum mechanical phenomena.",
        score_raw=0.8
    )
    state.add_evidence(test_evidence)
    
    try:
        # This might trigger fallbacks if LLM calls fail
        result_state = await reranker_langgraph.execute(state)
        print("✅ M8 completed successfully")
        print(f"   Evidence count: {len(result_state.evidences)}")
        if hasattr(result_state, 'evidence_scores'):
            print(f"   Evidence scores generated: {len(result_state.evidence_scores)}")
    except Exception as e:
        print(f"❌ M8 failed: {e}")
    
    # Test 3: M1 with problematic query (may trigger fallbacks)
    print("\n📋 TEST 3: M1 Query Preprocessor (may trigger fallbacks)")
    print("-" * 30)
    
    # Create a new state for M1 testing
    problematic_query = Query(
        id="test-fallback-002",
        text="",  # Empty query to potentially trigger fallbacks
        user_id="test-user",
        conversation_id="test-conv"
    )
    
    m1_state = ReactorState(original_query=problematic_query)
    
    try:
        result_state = await query_preprocessor_langgraph.execute(m1_state)
        print("✅ M1 completed")
        print(f"   WorkUnits created: {len(result_state.workunits)}")
        if hasattr(result_state, 'preprocessing_metadata'):
            fallback_used = result_state.preprocessing_metadata.get('fallback_used', False)
            print(f"   Fallback used: {fallback_used}")
    except Exception as e:
        print(f"❌ M1 failed: {e}")
    
    # Test 4: M5 with invalid configuration (should trigger fallbacks)
    print("\n📋 TEST 4: M5 Internet Retrieval (may trigger API fallbacks)")
    print("-" * 30)
    
    # Create state with WorkUnit for M5
    m5_state = ReactorState(original_query=test_query)
    m5_state.add_workunit(test_workunit)
    
    try:
        # This will likely trigger API fallbacks due to missing/invalid API keys
        result_state = await internet_retrieval_langgraph.execute(m5_state)
        print("✅ M5 completed")
        print(f"   Evidence items retrieved: {len(result_state.evidences)}")
    except Exception as e:
        print(f"❌ M5 failed: {e}")
    
    print("\n🎯 FALLBACK LOGGING TEST COMPLETE")
    print("=" * 50)
    print("Look for 🔄 FALLBACK TRIGGERED and 🔄 EXECUTING FALLBACK messages above.")
    print("These indicate when fallback methods are being used due to errors.")


if __name__ == "__main__":
    asyncio.run(test_fallback_scenarios())