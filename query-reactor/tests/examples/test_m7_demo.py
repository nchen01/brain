#!/usr/bin/env python3
"""Demo script to test M7 Evidence Aggregator module."""

import asyncio
import time
from uuid import uuid4

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m7_evidence_aggregator_langgraph import evidence_aggregator_langgraph


async def test_m7_module():
    """Test M7 module with sample evidence and show aggregation results."""
    
    print("=" * 60)
    print("M7 Evidence Aggregator Module Test")
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
        text="What are the environmental benefits of renewable energy?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    # Create test evidence items with potential duplicates and overlaps
    evidence1 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Renewable energy sources like solar and wind power produce electricity without greenhouse gas emissions during operation.",
        title="Clean Energy Environmental Benefits",
        score_raw=0.9,
        provenance=Provenance(
            source_type=SourceType.db,  # Using correct enum value
            source_id="energy_research_db",
            url="https://energy-db.example.com/doc1",
            retrieval_path="P1",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Similar content (potential duplicate)
    evidence2 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Solar and wind energy generate clean electricity without producing greenhouse gases during their operation phase.",
        title="Renewable Energy Clean Generation",
        score_raw=0.85,
        provenance=Provenance(
            source_type=SourceType.web,
            source_id="web_search_result",
            url="https://example.com/renewable-energy",
            retrieval_path="P2",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Complementary content
    evidence3 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Renewable energy reduces air pollution and helps combat climate change by decreasing reliance on fossil fuels.",
        title="Renewable Energy Climate Impact",
        score_raw=0.88,
        provenance=Provenance(
            source_type=SourceType.db,
            source_id="climate_research_db",
            url="https://climate-db.example.com/doc3",
            retrieval_path="P1",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Different perspective
    evidence4 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="While renewable energy has environmental benefits, the manufacturing of solar panels and wind turbines does have some environmental impact.",
        title="Renewable Energy Manufacturing Impact",
        score_raw=0.75,
        provenance=Provenance(
            source_type=SourceType.web,
            source_id="environmental_analysis",
            url="https://example.org/manufacturing-impact",
            retrieval_path="P2",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Create reactor state with evidence
    state = ReactorState(original_query=user_query)
    state.add_evidence(evidence1)
    state.add_evidence(evidence2)
    state.add_evidence(evidence3)
    state.add_evidence(evidence4)
    
    print(f"\n📥 INPUT:")
    print(f"User Query: {user_query.text}")
    print(f"Evidence Items: {len(state.evidences)}")
    
    for i, evidence in enumerate(state.evidences, 1):
        print(f"\n--- Evidence {i} ---")
        print(f"Title: {evidence.title}")
        print(f"Content: {evidence.content[:100]}...")
        print(f"Score: {evidence.score_raw}")
        print(f"Source: {evidence.provenance.source_type.value} - {evidence.provenance.source_id}")
        print(f"Path: {evidence.provenance.retrieval_path}")
    
    # Execute M7 module
    print(f"\n🚀 EXECUTING M7 MODULE...")
    start_time = time.time()
    
    try:
        result_state = await evidence_aggregator_langgraph.execute(state)
        execution_time = time.time() - start_time
        
        print(f"✅ Execution completed in {execution_time:.2f} seconds")
        
        print(f"\n📤 OUTPUT:")
        print(f"Final Evidence Count: {len(result_state.evidences)}")
        
        # Show aggregation results
        if hasattr(result_state, 'evidence_collection'):
            collection = result_state.evidence_collection
            print(f"\n📊 EVIDENCE COLLECTION ANALYSIS:")
            print(f"Total Evidence: {collection.total_evidence}")
            print(f"Source Distribution: {collection.source_distribution}")
            print(f"Quality Distribution: {collection.quality_distribution}")
            print(f"Coverage Analysis: {collection.coverage_analysis}")
            print(f"Confidence: {collection.confidence}")
        
        if hasattr(result_state, 'deduplication_results'):
            dedup = result_state.deduplication_results
            print(f"\n🔄 DEDUPLICATION RESULTS:")
            print(f"Original Count: {dedup.original_count}")
            print(f"Duplicate Count: {dedup.duplicate_count}")
            print(f"Final Count: {dedup.final_count}")
            print(f"Method: {dedup.deduplication_method}")
            print(f"Confidence: {dedup.confidence}")
            if dedup.duplicate_pairs:
                print(f"Duplicate Pairs: {len(dedup.duplicate_pairs)}")
        
        if hasattr(result_state, 'source_merging'):
            merging = result_state.source_merging
            print(f"\n🔗 SOURCE MERGING RESULTS:")
            print(f"Merged Groups: {len(merging.merged_groups)}")
            print(f"Merge Strategies: {merging.merge_strategies}")
            print(f"Information Gain: {merging.information_gain}")
            print(f"Confidence: {merging.confidence}")
        
        if hasattr(result_state, 'consistency_validation'):
            validation = result_state.consistency_validation
            print(f"\n✅ CONSISTENCY VALIDATION:")
            print(f"Consistency Score: {validation.consistency_score}")
            print(f"Conflicting Evidence: {len(validation.conflicting_evidence)}")
            print(f"Consensus Items: {len(validation.consensus_items)}")
            print(f"Uncertainty Areas: {validation.uncertainty_areas}")
            print(f"Validation Method: {validation.validation_method}")
            print(f"Confidence: {validation.confidence}")
        
        # Show final evidence
        print(f"\n📋 FINAL EVIDENCE ITEMS:")
        for i, evidence in enumerate(result_state.evidences, 1):
            print(f"\n--- Final Evidence {i} ---")
            print(f"ID: {evidence.id}")
            print(f"Title: {evidence.title}")
            print(f"Content: {evidence.content[:150]}...")
            print(f"Score: {evidence.score_raw}")
            print(f"Source: {evidence.provenance.source_type.value}")
        
        # Show aggregation statistics
        print(f"\n📈 AGGREGATION STATISTICS:")
        original_count = getattr(result_state, 'original_evidence_count', len(state.evidences))
        final_count = len(result_state.evidences)
        reduction_rate = (original_count - final_count) / original_count * 100 if original_count > 0 else 0
        
        print(f"Original Evidence: {original_count}")
        print(f"Final Evidence: {final_count}")
        print(f"Reduction Rate: {reduction_rate:.1f}%")
        
        # Calculate quality improvement
        original_avg_score = sum(e.score_raw for e in state.evidences) / len(state.evidences)
        final_avg_score = sum(e.score_raw for e in result_state.evidences) / len(result_state.evidences) if result_state.evidences else 0
        quality_improvement = (final_avg_score - original_avg_score) / original_avg_score * 100 if original_avg_score > 0 else 0
        
        print(f"Original Avg Score: {original_avg_score:.3f}")
        print(f"Final Avg Score: {final_avg_score:.3f}")
        print(f"Quality Improvement: {quality_improvement:.1f}%")
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ Execution failed after {execution_time:.2f} seconds")
        print(f"Error: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_m7_module())