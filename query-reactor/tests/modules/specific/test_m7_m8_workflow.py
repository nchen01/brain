#!/usr/bin/env python3
"""Comprehensive test for M7→M8 workflow: Evidence Aggregator to ReRanker."""

import asyncio
import time
from uuid import uuid4

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance, WorkUnit
from src.models.types import SourceType
from src.modules.m7_evidence_aggregator_langgraph import evidence_aggregator_langgraph
from src.modules.m8_reranker_langgraph import ReRankerLangGraph


async def test_m7_m8_workflow():
    """Test the complete M7→M8 workflow with WorkUnit-based ranking."""
    
    print("=" * 70)
    print("M7 → M8 WORKFLOW TEST: Evidence Aggregation → ReRanking")
    print("=" * 70)
    
    # Create test data
    user_id = uuid4()
    conversation_id = uuid4()
    query_id = uuid4()
    
    # Create user query
    user_query = UserQuery(
        user_id=user_id,
        conversation_id=conversation_id,
        id=query_id,
        text="What are the benefits and challenges of renewable energy adoption?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    # Create WorkUnits (from M1 decomposition)
    workunit1 = WorkUnit(
        parent_query_id=query_id,
        text="What are the benefits of renewable energy?",
        user_id=user_id,
        conversation_id=conversation_id,
        timestamp=int(time.time() * 1000),
        is_subquestion=True,
        priority=0
    )
    
    workunit2 = WorkUnit(
        parent_query_id=query_id,
        text="What are the challenges of renewable energy adoption?",
        user_id=user_id,
        conversation_id=conversation_id,
        timestamp=int(time.time() * 1000),
        is_subquestion=True,
        priority=1
    )
    
    # Create evidence items with varying relevance to WorkUnits
    evidence_items = [
        # High relevance to WorkUnit 1 (benefits)
        EvidenceItem(
            workunit_id=workunit1.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Renewable energy sources like solar and wind power produce clean electricity without greenhouse gas emissions, significantly reducing environmental impact and air pollution in urban areas.",
            title="Environmental Benefits of Renewable Energy",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.db,
                source_id="environmental_research_db",
                url="https://env-research.org/renewable-benefits",
                retrieval_path="P1",
                router_decision_id=workunit1.id,
                language="en"
            )
        ),
        
        # Duplicate content (should be removed by M7)
        EvidenceItem(
            workunit_id=workunit1.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Solar and wind energy produce clean electricity without greenhouse gas emissions and reduce environmental impact.",
            title="Clean Energy Environmental Impact",
            score_raw=0.85,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="clean_energy_web",
                url="https://example.com/clean-energy",
                retrieval_path="P2",
                router_decision_id=workunit1.id,
                language="en"
            )
        ),
        
        # High relevance to WorkUnit 2 (challenges)
        EvidenceItem(
            workunit_id=workunit2.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Renewable energy adoption faces significant challenges including high initial installation costs, intermittency issues requiring energy storage solutions, and the need for substantial grid infrastructure upgrades.",
            title="Challenges in Renewable Energy Implementation",
            score_raw=0.88,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="energy_challenges_analysis",
                url="https://energy-analysis.org/challenges",
                retrieval_path="P2",
                router_decision_id=workunit2.id,
                language="en"
            )
        ),
        
        # Medium relevance to WorkUnit 1 (economic benefits)
        EvidenceItem(
            workunit_id=workunit1.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Renewable energy creates jobs in manufacturing, installation, and maintenance sectors, contributing to economic growth and energy independence.",
            title="Economic Benefits of Renewable Energy",
            score_raw=0.82,
            provenance=Provenance(
                source_type=SourceType.db,
                source_id="economic_research_db",
                url="https://econ-research.org/renewable-jobs",
                retrieval_path="P1",
                router_decision_id=workunit1.id,
                language="en"
            )
        ),
        
        # Low relevance (general information)
        EvidenceItem(
            workunit_id=workunit1.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Energy consumption patterns vary significantly across different regions and seasons, influenced by climate, population density, and industrial activity.",
            title="Global Energy Consumption Patterns",
            score_raw=0.65,
            provenance=Provenance(
                source_type=SourceType.api,
                source_id="energy_stats_api",
                url="https://api.energy-stats.org/consumption",
                retrieval_path="P3",
                router_decision_id=workunit1.id,
                language="en"
            )
        ),
        
        # Medium relevance to WorkUnit 2 (technical challenges)
        EvidenceItem(
            workunit_id=workunit2.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Grid integration of renewable energy requires advanced forecasting systems and smart grid technologies to manage variable power generation from wind and solar sources.",
            title="Technical Challenges of Grid Integration",
            score_raw=0.80,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="grid_technology_web",
                url="https://grid-tech.com/integration-challenges",
                retrieval_path="P2",
                router_decision_id=workunit2.id,
                language="en"
            )
        )
    ]
    
    # Create initial state
    state = ReactorState(original_query=user_query)
    state.add_workunit(workunit1)
    state.add_workunit(workunit2)
    
    for evidence in evidence_items:
        state.add_evidence(evidence)
    
    print(f"\n📥 INITIAL STATE:")
    print(f"User Query: {user_query.text}")
    print(f"WorkUnits: {len(state.workunits)}")
    for i, wu in enumerate(state.workunits, 1):
        print(f"  {i}. {wu.text}")
    print(f"Evidence Items: {len(state.evidences)}")
    for i, evidence in enumerate(state.evidences, 1):
        print(f"  {i}. [{evidence.score_raw:.2f}] {evidence.title}")
        print(f"     WorkUnit: {evidence.workunit_id}")
        print(f"     Content: {evidence.content[:80]}...")
    
    # STEP 1: Execute M7 Evidence Aggregator
    print(f"\n🔄 STEP 1: M7 EVIDENCE AGGREGATOR")
    print("-" * 50)
    
    m7_start_time = time.time()
    try:
        m7_result_state = await evidence_aggregator_langgraph.execute(state)
        m7_execution_time = time.time() - m7_start_time
        
        print(f"✅ M7 completed in {m7_execution_time:.2f} seconds")
        print(f"Evidence after M7: {len(m7_result_state.evidences)}")
        
        # Show M7 results
        if hasattr(m7_result_state, 'deduplication_results'):
            dedup = m7_result_state.deduplication_results
            print(f"Deduplication: {dedup.original_count} → {dedup.final_count} ({dedup.duplicate_count} duplicates removed)")
        
        if hasattr(m7_result_state, 'consistency_validation'):
            validation = m7_result_state.consistency_validation
            print(f"Consistency Score: {validation.consistency_score:.2f}")
        
        print(f"\nM7 Output Evidence:")
        for i, evidence in enumerate(m7_result_state.evidences, 1):
            print(f"  {i}. [{evidence.score_raw:.2f}] {evidence.title}")
            print(f"     WorkUnit: {evidence.workunit_id}")
            print(f"     Source: {evidence.provenance.source_type.value}")
        
    except Exception as e:
        print(f"❌ M7 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # STEP 2: Execute M8 ReRanker
    print(f"\n🎯 STEP 2: M8 RERANKER")
    print("-" * 50)
    
    m8_module = ReRankerLangGraph()
    m8_start_time = time.time()
    
    try:
        m8_result_state = await m8_module.execute(m7_result_state)
        m8_execution_time = time.time() - m8_start_time
        
        print(f"✅ M8 completed in {m8_execution_time:.2f} seconds")
        print(f"Evidence after M8: {len(m8_result_state.evidences)}")
        
        # Show M8 results
        if hasattr(m8_result_state, 'adaptive_strategy'):
            strategy = m8_result_state.adaptive_strategy
            print(f"Ranking Strategy: {strategy.strategy_name}")
            print(f"Strategy Rationale: {strategy.strategy_rationale}")
            print(f"Expected Improvement: {strategy.expected_improvement:.2f}")
        
        if hasattr(m8_result_state, 'evidence_scores'):
            print(f"Evidence Scores Generated: {len(m8_result_state.evidence_scores)}")
        
        if hasattr(m8_result_state, 'ranking_validation'):
            validation = m8_result_state.ranking_validation
            print(f"Ranking Consistency: {validation.ranking_consistency:.2f}")
            print(f"Top Items Quality: {validation.top_items_quality:.2f}")
            print(f"Diversity Score: {validation.diversity_score:.2f}")
        
        print(f"\nM8 Ranked Evidence (by relevance to WorkUnits):")
        for i, evidence in enumerate(m8_result_state.evidences, 1):
            # Find corresponding WorkUnit
            workunit = next((wu for wu in m8_result_state.workunits if wu.id == evidence.workunit_id), None)
            workunit_text = workunit.text if workunit else "Unknown WorkUnit"
            
            print(f"  {i}. [{evidence.score_raw:.2f}] {evidence.title}")
            print(f"     WorkUnit: {workunit_text}")
            print(f"     Content: {evidence.content[:100]}...")
            print(f"     Source: {evidence.provenance.source_type.value} - {evidence.provenance.source_id}")
            
            # Show M8 scoring if available
            if hasattr(m8_result_state, 'evidence_scores'):
                score_info = next((s for s in m8_result_state.evidence_scores if s.evidence_id == str(evidence.id)), None)
                if score_info:
                    print(f"     M8 Scores: Relevance={score_info.relevance_score:.2f}, Quality={score_info.quality_score:.2f}, Composite={score_info.composite_score:.2f}")
            print()
        
    except Exception as e:
        print(f"❌ M8 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # STEP 3: Analysis and Comparison
    print(f"\n📊 WORKFLOW ANALYSIS")
    print("-" * 50)
    
    # Compare before and after
    original_count = len(state.evidences)
    m7_count = len(m7_result_state.evidences)
    final_count = len(m8_result_state.evidences)
    
    print(f"Evidence Count: {original_count} → {m7_count} (M7) → {final_count} (M8)")
    
    # Calculate quality improvements
    original_avg_score = sum(e.score_raw for e in state.evidences) / len(state.evidences)
    final_avg_score = sum(e.score_raw for e in m8_result_state.evidences) / len(m8_result_state.evidences)
    
    print(f"Average Score: {original_avg_score:.3f} → {final_avg_score:.3f}")
    print(f"Quality Improvement: {((final_avg_score - original_avg_score) / original_avg_score * 100):.1f}%")
    
    # Execution times
    total_time = m7_execution_time + m8_execution_time
    print(f"Execution Times: M7={m7_execution_time:.2f}s, M8={m8_execution_time:.2f}s, Total={total_time:.2f}s")
    
    # WorkUnit coverage analysis
    print(f"\nWorkUnit Coverage Analysis:")
    for workunit in m8_result_state.workunits:
        workunit_evidence = [e for e in m8_result_state.evidences if e.workunit_id == workunit.id]
        print(f"  '{workunit.text}': {len(workunit_evidence)} evidence items")
        
        if workunit_evidence:
            avg_score = sum(e.score_raw for e in workunit_evidence) / len(workunit_evidence)
            top_score = max(e.score_raw for e in workunit_evidence)
            print(f"    Average Score: {avg_score:.3f}, Top Score: {top_score:.3f}")
    
    # Show ranking effectiveness
    print(f"\nRanking Effectiveness:")
    if len(m8_result_state.evidences) >= 2:
        top_evidence = m8_result_state.evidences[0]
        bottom_evidence = m8_result_state.evidences[-1]
        print(f"  Top Ranked: {top_evidence.title} (Score: {top_evidence.score_raw:.3f})")
        print(f"  Bottom Ranked: {bottom_evidence.title} (Score: {bottom_evidence.score_raw:.3f})")
        print(f"  Score Range: {top_evidence.score_raw - bottom_evidence.score_raw:.3f}")
    
    # Verify M8 used prompts from prompts.md
    print(f"\n🔍 PROMPT VERIFICATION:")
    print(f"M8 should have used prompts from prompts.md:")
    print(f"  - m8_strategy_selection: For determining ranking strategy")
    print(f"  - m8_evidence_scoring: For scoring evidence relevance to WorkUnits")
    print(f"  - m8_ranking_validation: For validating ranking quality")
    
    print(f"\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_m7_m8_workflow())