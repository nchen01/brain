#!/usr/bin/env python3
"""Test Perplexity API integration for M5."""

import asyncio
import sys
from uuid import uuid4
import time

sys.path.insert(0, 'src')

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.modules.m5_internet_retrieval_langgraph import M5InternetRetrievalLangGraph

async def test_perplexity_integration():
    """Test M5 with Perplexity API."""
    
    print("🔍 M5 Perplexity API Integration Test")
    print("=" * 60)
    
    # Create test query
    user_id = uuid4()
    conversation_id = uuid4()
    query_id = uuid4()
    
    user_query = UserQuery(
        user_id=user_id,
        conversation_id=conversation_id,
        id=query_id,
        text="What are the latest developments in quantum computing?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    workunit = WorkUnit(
        parent_query_id=query_id,
        text="quantum computing breakthroughs 2024",
        user_id=user_id,
        conversation_id=conversation_id,
        timestamp=int(time.time() * 1000),
        is_subquestion=True,
        priority=0
    )
    
    # Create state
    state = ReactorState(original_query=user_query)
    state.add_workunit(workunit)
    
    print(f"📝 Query: '{workunit.text}'")
    print(f"🔍 Testing M5 with Perplexity API...")
    
    # Test M5 configuration
    m5 = M5InternetRetrievalLangGraph()
    print(f"\n🔧 M5 Configuration:")
    print(f"   API Key: {'✅ Configured' if m5.api_key and m5.api_key != 'your_perplexity_api_key' else '❌ Not configured'}")
    print(f"   Model: {m5.model}")
    print(f"   Max Results: {m5.max_results}")
    print(f"   Timeout: {m5.timeout_seconds}s")
    
    # Execute M5
    print(f"\n🚀 Executing M5...")
    result_state = await m5.execute(state)
    
    print(f"\n📊 Results:")
    print(f"   Evidence Items: {len(result_state.evidences)}")
    
    if result_state.evidences:
        print(f"\n📄 Sample Results:")
        for i, evidence in enumerate(result_state.evidences[:3], 1):
            print(f"\n   {i}. {evidence.title}")
            print(f"      URL: {evidence.provenance.url}")
            print(f"      Content Length: {len(evidence.content)} chars")
            print(f"      Content Preview: {evidence.content[:150]}...")
            
            # Check if this looks like Perplexity content
            is_perplexity = 'perplexity.ai' in evidence.provenance.url
            content_quality = "High" if len(evidence.content) > 200 else "Low"
            print(f"      Source: {'🤖 Perplexity' if is_perplexity else '🌐 Web'}")
            print(f"      Quality: {content_quality}")
    
    # Analysis
    print(f"\n📈 Analysis:")
    avg_content_length = sum(len(e.content) for e in result_state.evidences) / len(result_state.evidences) if result_state.evidences else 0
    print(f"   Average Content Length: {avg_content_length:.0f} characters")
    
    perplexity_results = sum(1 for e in result_state.evidences if 'perplexity.ai' in e.provenance.url)
    print(f"   Perplexity Results: {perplexity_results}/{len(result_state.evidences)}")
    
    high_quality = sum(1 for e in result_state.evidences if len(e.content) > 200)
    print(f"   High Quality Content: {high_quality}/{len(result_state.evidences)}")
    
    if perplexity_results > 0:
        print(f"\n✅ Perplexity API integration successful!")
        print(f"   M5 is now using Perplexity for enhanced search results")
    else:
        print(f"\n⚠️ Using placeholder data")
        print(f"   Configure PERPLEXITY_API_KEY in .env to enable Perplexity search")
    
    return result_state

if __name__ == "__main__":
    asyncio.run(test_perplexity_integration())