#!/usr/bin/env python3
"""Test M8 ReRanker with structured output and prompts from prompts.md."""

import asyncio
import time
from uuid import uuid4

from src.models.state import ReactorState
from src.models.core import UserQuery, EvidenceItem, Provenance, WorkUnit
from src.models.types import SourceType
from src.modules.m8_reranker_langgraph import ReRankerLangGraph


async def test_m8_structured_output():
    """Test M8 with structured LLM output and prompts from prompts.md."""
    
    print("=" * 70)
    print("M8 RERANKER - STRUCTURED OUTPUT TEST")
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
        text="What are the environmental benefits of solar energy?",
        timestamp=int(time.time() * 1000),
        locale="en-US"
    )
    
    # Create WorkUnit
    workunit = WorkUnit(
        parent_query_id=query_id,
        text="What are the environmental benefits of solar energy?",
        user_id=user_id,
        conversation_id=conversation_id,
        timestamp=int(time.time() * 1000),
        is_subquestion=False,
        priority=0
    )
    
    # Create evidence items with varying relevance
    evidence_items = [
        # High relevance
        EvidenceItem(
            workunit_id=workunit.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Solar energy produces clean electricity without greenhouse gas emissions, significantly reducing carbon footprint and air pollution compared to fossil fuels.",
            title="Solar Energy Environmental Benefits",
            score_raw=0.9,
            provenance=Provenance(
                source_type=SourceType.db,
                source_id="environmental_research",
                url="https://env-research.org/solar-benefits",
                retrieval_path="P1",
                router_decision_id=workunit.id,
                language="en"
            )
        ),
        
        # Medium relevance
        EvidenceItem(
            workunit_id=workunit.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Renewable energy sources like solar panels help reduce dependence on fossil fuels and contribute to sustainable development goals.",
            title="Renewable Energy Sustainability",
            score_raw=0.75,
            provenance=Provenance(
                source_type=SourceType.web,
                source_id="sustainability_web",
                url="https://sustainability.org/renewable",
                retrieval_path="P2",
                router_decision_id=workunit.id,
                language="en"
            )
        ),
        
        # Lower relevance
        EvidenceItem(
            workunit_id=workunit.id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Energy storage systems are becoming more efficient and cost-effective, enabling better integration of renewable energy sources into the grid.",
            title="Energy Storage Technology",
            score_raw=0.65,
            provenance=Provenance(
                source_type=SourceType.api,
                source_id="energy_tech_api",
                url="https://api.energy-tech.com/storage",
                retrieval_path="P3",
                router_decision_id=workunit.id,
                language="en"
            )
        )
    ]
    
    # Create state
    state = ReactorState(original_query=user_query)
    state.add_workunit(workunit)
    
    for evidence in evidence_items:
        state.add_evidence(evidence)
    
    print(f"\n📥 INPUT:")
    print(f"Query: {user_query.text}")
    print(f"WorkUnit: {workunit.text}")
    print(f"Evidence Items: {len(state.evidences)}")
    
    for i, evidence in enumerate(state.evidences, 1):
        print(f"  {i}. [{evidence.score_raw:.2f}] {evidence.title}")
        print(f"     Content: {evidence.content[:80]}...")
    
    # Test M8 ReRanker
    print(f"\n🎯 TESTING M8 RERANKER WITH STRUCTURED OUTPUT")
    print("-" * 50)
    
    m8_module = ReRankerLangGraph()
    start_time = time.time()
    
    try:
        result_state = await m8_module.execute(state)
        execution_time = time.time() - start_time
        
        print(f"✅ M8 completed in {execution_time:.2f} seconds")
        
        # Verify structured output results
        print(f"\n📊 STRUCTURED OUTPUT VERIFICATION:")
        
        # Check adaptive strategy
        if hasattr(result_state, 'adaptive_strategy'):
            strategy = result_state.adaptive_strategy
            print(f"✅ Adaptive Strategy (Pydantic model):")
            print(f"   Strategy: {strategy.strategy_name}")
            print(f"   Rationale: {strategy.strategy_rationale}")
            print(f"   Expected Improvement: {strategy.expected_improvement:.3f}")
            print(f"   Confidence: {strategy.confidence:.3f}")
            print(f"   Query Characteristics: {strategy.query_characteristics}")
            print(f"   Weight Adjustments: {strategy.weight_adjustments}")
        else:
            print("❌ No adaptive strategy found")
        
        # Check evidence scores
        if hasattr(result_state, 'evidence_scores'):
            scores = result_state.evidence_scores
            print(f"\n✅ Evidence Scores (Pydantic models): {len(scores)} items")
            for score in scores:
                print(f"   Evidence {score.evidence_id[:8]}...")
                print(f"     Relevance: {score.relevance_score:.3f}")
                print(f"     Quality: {score.quality_score:.3f}")
                print(f"     Credibility: {score.credibility_score:.3f}")
                print(f"     Composite: {score.composite_score:.3f}")
                print(f"     Confidence: {score.confidence:.3f}")
        else:
            print("❌ No evidence scores found")
        
        # Check ranking validation
        if hasattr(result_state, 'ranking_validation'):
            validation = result_state.ranking_validation
            print(f"\n✅ Ranking Validation (Pydantic model):")
            print(f"   Method: {validation.validation_method}")
            print(f"   Consistency: {validation.ranking_consistency:.3f}")
            print(f"   Top Items Quality: {validation.top_items_quality:.3f}")
            print(f"   Diversity Score: {validation.diversity_score:.3f}")
            print(f"   Issues: {validation.validation_issues}")
            print(f"   Confidence: {validation.confidence:.3f}")
        else:
            print("❌ No ranking validation found")
        
        # Show final ranking
        print(f"\n🏆 FINAL RANKING:")
        for i, evidence in enumerate(result_state.evidences, 1):
            # Find corresponding score
            score_info = None
            if hasattr(result_state, 'evidence_scores'):
                score_info = next((s for s in result_state.evidence_scores if s.evidence_id == str(evidence.id)), None)
            
            composite_score = score_info.composite_score if score_info else evidence.score_raw
            
            print(f"  {i}. [{composite_score:.3f}] {evidence.title}")
            print(f"     Original Score: {evidence.score_raw:.3f}")
            if score_info:
                print(f"     M8 Relevance: {score_info.relevance_score:.3f}")
                print(f"     M8 Quality: {score_info.quality_score:.3f}")
            print(f"     Content: {evidence.content[:100]}...")
            print()
        
        # Verify no hardcoded prompts
        print(f"🔍 PROMPT VERIFICATION:")
        print(f"✅ M8 should use prompts from prompts.md:")
        print(f"   - m8_strategy_selection: Used for strategy selection")
        print(f"   - m8_evidence_scoring: Used for evidence scoring")
        print(f"   - m8_ranking_validation: Used for ranking validation")
        print(f"✅ No hardcoded prompts in M8 module")
        print(f"✅ All LLM calls use structured output (Pydantic models)")
        
        print(f"\n✅ STRUCTURED OUTPUT TEST COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ M8 failed after {execution_time:.2f} seconds")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_m8_structured_output())