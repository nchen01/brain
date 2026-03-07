#!/usr/bin/env python3
"""Detailed test script for M7 Evidence Aggregator module nodes."""

import asyncio
import time
from uuid import uuid4

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance
from src.models.types import SourceType
from src.modules.m7_evidence_aggregator_langgraph import evidence_aggregator_langgraph


async def test_m7_nodes():
    """Test individual M7 nodes to understand the aggregation process."""
    
    print("=" * 60)
    print("M7 Evidence Aggregator - Detailed Node Testing")
    print("=" * 60)
    
    # Create test data with more obvious duplicates
    user_id = uuid4()
    conversation_id = uuid4()
    query_id = uuid4()
    
    user_query = UserQuery(
        user_id=user_id,
        conversation_id=conversation_id,
        id=query_id,
        text="What are the benefits of renewable energy?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    # Create evidence with clear duplicates and similarities
    evidence1 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Solar energy is clean and renewable. It produces no emissions.",
        title="Solar Energy Benefits",
        score_raw=0.9,
        provenance=Provenance(
            source_type=SourceType.db,
            source_id="solar_db",
            url="https://solar-db.com/benefits",
            retrieval_path="P1",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Very similar content (should be detected as duplicate)
    evidence2 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Solar energy is clean and renewable and produces no emissions.",
        title="Clean Solar Power",
        score_raw=0.85,
        provenance=Provenance(
            source_type=SourceType.web,
            source_id="web_solar",
            url="https://example.com/solar",
            retrieval_path="P2",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Different but related content
    evidence3 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Wind power generates electricity without pollution and is sustainable.",
        title="Wind Energy Advantages",
        score_raw=0.88,
        provenance=Provenance(
            source_type=SourceType.db,
            source_id="wind_db",
            url="https://wind-db.com/advantages",
            retrieval_path="P1",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Exact duplicate content
    evidence4 = EvidenceItem(
        workunit_id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        content="Solar energy is clean and renewable. It produces no emissions.",  # Exact same as evidence1
        title="Duplicate Solar Info",
        score_raw=0.80,
        provenance=Provenance(
            source_type=SourceType.api,
            source_id="api_solar",
            url="https://api.example.com/solar",
            retrieval_path="P3",
            router_decision_id=uuid4(),
            language="en"
        )
    )
    
    # Create state
    state = ReactorState(original_query=user_query)
    state.add_evidence(evidence1)
    state.add_evidence(evidence2)
    state.add_evidence(evidence3)
    state.add_evidence(evidence4)
    
    print(f"\n📥 INPUT EVIDENCE:")
    for i, evidence in enumerate(state.evidences, 1):
        print(f"{i}. {evidence.title}: '{evidence.content}' (Score: {evidence.score_raw})")
    
    # Test individual nodes
    print(f"\n🔍 TESTING INDIVIDUAL NODES:")
    
    # 1. Test collection analysis
    print(f"\n1️⃣ COLLECTION ANALYSIS NODE:")
    try:
        collection_state = await evidence_aggregator_langgraph._collect_evidence_node(state)
        if hasattr(collection_state, 'evidence_collection'):
            collection = collection_state.evidence_collection
            print(f"✅ Collection Analysis Complete:")
            print(f"   Total Evidence: {collection.total_evidence}")
            print(f"   Source Distribution: {collection.source_distribution}")
            print(f"   Quality Distribution: {collection.quality_distribution}")
            print(f"   Coverage Analysis: {collection.coverage_analysis}")
            print(f"   Confidence: {collection.confidence}")
        else:
            print(f"❌ No collection analysis results")
    except Exception as e:
        print(f"❌ Collection analysis failed: {e}")
    
    # 2. Test deduplication
    print(f"\n2️⃣ DEDUPLICATION NODE:")
    try:
        dedup_state = await evidence_aggregator_langgraph._deduplicate_node(collection_state)
        if hasattr(dedup_state, 'deduplication_results'):
            dedup = dedup_state.deduplication_results
            print(f"✅ Deduplication Complete:")
            print(f"   Original Count: {dedup.original_count}")
            print(f"   Duplicate Count: {dedup.duplicate_count}")
            print(f"   Final Count: {dedup.final_count}")
            print(f"   Duplicate Pairs: {len(dedup.duplicate_pairs)}")
            for pair in dedup.duplicate_pairs:
                print(f"     - {pair}")
            print(f"   Method: {dedup.deduplication_method}")
            print(f"   Confidence: {dedup.confidence}")
            print(f"   Evidence after dedup: {len(dedup_state.evidences)}")
        else:
            print(f"❌ No deduplication results")
    except Exception as e:
        print(f"❌ Deduplication failed: {e}")
        dedup_state = collection_state
    
    # 3. Test source merging
    print(f"\n3️⃣ SOURCE MERGING NODE:")
    try:
        merge_state = await evidence_aggregator_langgraph._merge_sources_node(dedup_state)
        if hasattr(merge_state, 'source_merging'):
            merging = merge_state.source_merging
            print(f"✅ Source Merging Complete:")
            print(f"   Merged Groups: {len(merging.merged_groups)}")
            for group in merging.merged_groups:
                print(f"     - Group: {group}")
            print(f"   Merge Strategies: {merging.merge_strategies}")
            print(f"   Quality Improvements: {merging.quality_improvements}")
            print(f"   Information Gain: {merging.information_gain}")
            print(f"   Confidence: {merging.confidence}")
        else:
            print(f"❌ No source merging results")
    except Exception as e:
        print(f"❌ Source merging failed: {e}")
        merge_state = dedup_state
    
    # 4. Test consistency validation
    print(f"\n4️⃣ CONSISTENCY VALIDATION NODE:")
    try:
        validation_state = await evidence_aggregator_langgraph._validate_consistency_node(merge_state)
        if hasattr(validation_state, 'consistency_validation'):
            validation = validation_state.consistency_validation
            print(f"✅ Consistency Validation Complete:")
            print(f"   Consistency Score: {validation.consistency_score}")
            print(f"   Conflicting Evidence: {len(validation.conflicting_evidence)}")
            for conflict in validation.conflicting_evidence:
                print(f"     - Conflict: {conflict}")
            print(f"   Consensus Items: {len(validation.consensus_items)}")
            print(f"   Uncertainty Areas: {validation.uncertainty_areas}")
            print(f"   Validation Method: {validation.validation_method}")
            print(f"   Confidence: {validation.confidence}")
        else:
            print(f"❌ No consistency validation results")
    except Exception as e:
        print(f"❌ Consistency validation failed: {e}")
        validation_state = merge_state
    
    # Test utility functions
    print(f"\n🔧 TESTING UTILITY FUNCTIONS:")
    
    # Test content hash generation
    hash1 = evidence_aggregator_langgraph._generate_content_hash(evidence1.content)
    hash4 = evidence_aggregator_langgraph._generate_content_hash(evidence4.content)
    print(f"Content Hash Test:")
    print(f"   Evidence 1 hash: {hash1}")
    print(f"   Evidence 4 hash: {hash4}")
    print(f"   Same content? {hash1 == hash4}")
    
    # Test similarity calculation
    similarity_12 = evidence_aggregator_langgraph._calculate_content_similarity(evidence1.content, evidence2.content)
    similarity_13 = evidence_aggregator_langgraph._calculate_content_similarity(evidence1.content, evidence3.content)
    print(f"\nSimilarity Test:")
    print(f"   Evidence 1 vs 2: {similarity_12:.3f}")
    print(f"   Evidence 1 vs 3: {similarity_13:.3f}")
    
    # Final comparison
    print(f"\n📊 FINAL COMPARISON:")
    print(f"Original Evidence Count: {len(state.evidences)}")
    print(f"Final Evidence Count: {len(validation_state.evidences)}")
    
    print(f"\nFinal Evidence Items:")
    for i, evidence in enumerate(validation_state.evidences, 1):
        print(f"{i}. {evidence.title}: '{evidence.content}' (Score: {evidence.score_raw})")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_m7_nodes())