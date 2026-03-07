#!/usr/bin/env python3
"""Demo script to test M5 Internet Retrieval module with Perplexity API."""

import asyncio
import time
from uuid import uuid4

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.modules.m5_internet_retrieval_langgraph import M5InternetRetrievalLangGraph


async def test_m5_module():
    """Test M5 module with sample input and show output."""
    
    print("=" * 60)
    print("M5 Internet Retrieval Module Test")
    print("=" * 60)
    
    # Create test data
    user_id = uuid4()
    conversation_id = uuid4()
    query_id = uuid4()
    
    # Create a user query
    user_query = UserQuery(
        user_id=user_id,
        conversation_id=conversation_id,
        id=query_id,
        text="What are the latest developments in artificial intelligence in 2024?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    # Create a work unit
    workunit = WorkUnit(
        parent_query_id=query_id,
        text="Latest AI developments 2024 machine learning breakthroughs",
        user_id=user_id,
        conversation_id=conversation_id,
        timestamp=int(time.time() * 1000),
        is_subquestion=True,
        priority=0
    )
    
    # Create reactor state
    state = ReactorState(original_query=user_query)
    state.add_workunit(workunit)
    
    print("\n📥 INPUT:")
    print(f"User Query: {user_query.text}")
    print(f"WorkUnit: {workunit.text}")
    print(f"User ID: {user_id}")
    print(f"Conversation ID: {conversation_id}")
    print(f"Number of WorkUnits: {len(state.workunits)}")
    
    # Initialize M5 module
    m5_module = M5InternetRetrievalLangGraph()
    
    print(f"\n🔧 MODULE CONFIGURATION:")
    print(f"Module Code: {m5_module.module_code}")
    print(f"Path ID: {m5_module.path_id}")
    print(f"Model: {m5_module.model}")
    print(f"Max Results: {m5_module.max_results}")
    print(f"Timeout: {m5_module.timeout_seconds}s")
    print(f"Rate Limit Delay: {m5_module.rate_limit_delay}s")
    print(f"API Key Configured: {'Yes' if m5_module.api_key and m5_module.api_key != 'your_perplexity_api_key' else 'No (using placeholder)'}")
    
    # Execute the module
    print(f"\n🚀 EXECUTING M5 MODULE...")
    start_time = time.time()
    
    try:
        result_state = await m5_module.execute(state)
        execution_time = time.time() - start_time
        
        print(f"✅ Execution completed in {execution_time:.2f} seconds")
        
        print(f"\n📤 OUTPUT:")
        print(f"Number of Evidence Items: {len(result_state.evidences)}")
        
        # Display evidence details
        for i, evidence in enumerate(result_state.evidences, 1):
            print(f"\n--- Evidence Item {i} ---")
            print(f"Title: {evidence.title}")
            print(f"Content Length: {len(evidence.content)} characters")
            print(f"Content Preview: {evidence.content[:200]}...")
            print(f"Source URL: {evidence.provenance.url}")
            print(f"Source Type: {evidence.provenance.source_type.value}")
            print(f"Retrieval Path: {evidence.provenance.retrieval_path}")
            print(f"Score: {evidence.score_raw}")
            print(f"WorkUnit ID: {evidence.workunit_id}")
            
        # Show state statistics
        print(f"\n📊 STATISTICS:")
        print(f"Total WorkUnits Processed: {len(state.workunits)}")
        print(f"Total Evidence Items Created: {len(result_state.evidences)}")
        print(f"Average Evidence Score: {sum(e.score_raw for e in result_state.evidences) / len(result_state.evidences):.3f}")
        print(f"Total Content Characters: {sum(len(e.content) for e in result_state.evidences)}")
        
        # Show unique sources
        unique_sources = set(e.provenance.url for e in result_state.evidences)
        print(f"Unique Sources: {len(unique_sources)}")
        for source in unique_sources:
            print(f"  - {source}")
            
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ Execution failed after {execution_time:.2f} seconds")
        print(f"Error: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        
        # Still show any evidence that might have been created
        if hasattr(state, 'evidences') and state.evidences:
            print(f"\nPartial Results: {len(state.evidences)} evidence items were created before the error")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_m5_module())