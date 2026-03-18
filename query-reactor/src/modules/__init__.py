"""Processing modules (M0-M12) for QueryReactor - Enhanced LangGraph + Pydantic versions."""

# Import enhanced LangGraph + Pydantic versions (Primary modules)
from .m0_qa_human_langgraph import qa_with_human_lg
from .m1_query_preprocessor_langgraph import query_preprocessor_lg
from .m2_query_router_langgraph import query_router_lg
from .m3_simple_retrieval_langgraph import simple_retrieval_lg
from .m4_retrieval_quality_check_langgraph import m4_quality_check
from .m5_internet_retrieval_langgraph import m5_internet_retrieval
from .m6_multihop_orchestrator_langgraph import multihop_orchestrator_lg
from .m7_evidence_aggregator_langgraph import evidence_aggregator_lg
from .m8_reranker_langgraph import reranker_lg
from .m9_smart_retrieval_controller_langgraph import smart_retrieval_controller_lg
from .m10_answer_creator_langgraph import answer_creator_lg
from .m11_answer_check_langgraph import answer_check_lg
from .m12_interaction_answer_langgraph import interaction_answer_lg

# Import enhanced module instances
from .m0_qa_human_langgraph import qa_with_human_langgraph
from .m1_query_preprocessor_langgraph import query_preprocessor_langgraph
from .m2_query_router_langgraph import query_router_langgraph
from .m3_simple_retrieval_langgraph import simple_retrieval_langgraph
from .m4_retrieval_quality_check_langgraph import m4_quality_check as retrieval_quality_check_langgraph
from .m5_internet_retrieval_langgraph import m5_internet_retrieval as internet_retrieval_langgraph
from .m6_multihop_orchestrator_langgraph import multihop_orchestrator_langgraph
from .m7_evidence_aggregator_langgraph import evidence_aggregator_langgraph
from .m8_reranker_langgraph import reranker_langgraph
from .m9_smart_retrieval_controller_langgraph import smart_retrieval_controller_langgraph
from .m10_answer_creator_langgraph import answer_creator_langgraph
from .m11_answer_check_langgraph import answer_check_langgraph
from .m12_interaction_answer_langgraph import interaction_answer_langgraph

# Backward compatibility aliases (map old names to enhanced versions)
qa_with_human = qa_with_human_lg
query_preprocessor = query_preprocessor_lg
query_router = query_router_lg
simple_retrieval = simple_retrieval_lg
retrieval_quality_check = m4_quality_check
internet_retrieval = m5_internet_retrieval
multihop_orchestrator = multihop_orchestrator_lg
evidence_aggregator = evidence_aggregator_lg
reranker = reranker_lg
smart_retrieval_controller = smart_retrieval_controller_lg
answer_creator = answer_creator_lg
answer_check = answer_check_lg
interaction_answer = interaction_answer_lg

__all__ = [
    # Primary enhanced LangGraph + Pydantic node functions
    "qa_with_human_lg",
    "query_preprocessor_lg",
    "query_router_lg",
    "simple_retrieval_lg",
    "m4_quality_check",
    "m5_internet_retrieval",
    "multihop_orchestrator_lg",
    "evidence_aggregator_lg",
    "reranker_lg",
    "smart_retrieval_controller_lg",
    "answer_creator_lg",
    "answer_check_lg",
    "interaction_answer_lg",
    
    # Backward compatibility aliases (point to enhanced versions)
    "qa_with_human",
    "query_preprocessor", 
    "query_router",
    "simple_retrieval",
    "retrieval_quality_check",
    "internet_retrieval",
    "multihop_orchestrator",
    "evidence_aggregator",
    "reranker",
    "smart_retrieval_controller",
    "answer_creator",
    "answer_check",
    "interaction_answer",
    
    # Enhanced module instances
    "qa_with_human_langgraph",
    "query_preprocessor_langgraph",
    "query_router_langgraph",
    "simple_retrieval_langgraph",
    "retrieval_quality_check_langgraph",
    "internet_retrieval_langgraph",
    "multihop_orchestrator_langgraph",
    "evidence_aggregator_langgraph",
    "reranker_langgraph",
    "smart_retrieval_controller_langgraph",
    "answer_creator_langgraph",
    "answer_check_langgraph",
    "interaction_answer_langgraph"
]