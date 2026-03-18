# QueryReactor Configuration

## Model Configuration
ac.model = "gpt-5-nano"
qa.model = "gpt-5-nano"
qp.model = "gpt-5-nano"
qr.model = "gpt-5-nano"
rr.model_name = "simple_heuristic"

## LLM Configuration (GPT-5-Nano Compatible)
llm.use_actual_calls = true
llm.max_completion_tokens = 1000

## Confidence and Quality Thresholds
qa.min_conf = 0.8
smr.min_confidence = 0.7
rqc.min_score = 0.3
rqc.quality_threshold = 0.5
ea.dedup_threshold = 0.8

## Loop Limits
loop.max.smartretrieval_to_qp = 2
loop.max.answercheck_to_ac = 3
loop.max.answercheck_to_qp = 1
qp.max_rounds = 3
qa.max_turns = 3

## Memory Configuration
memory.enable_in_m0 = true
memory.enable_in_m1 = true
memory.last_n = 5

## Query Processing
qp.enable_decomposition = true
ac.allow_partial_answer = true

## Retrieval Configuration
router.max_parallel_paths = 3
router.timeout_ms = 30000
sr.max_sources = 2
sr.top_n = 5
ir.top_n = 5
ir.max_age_days = 30
mho.max_hops = 3
mho.branching_factor = 1
mho.timeout_ms = 60000

## M5 Internet Retrieval Configuration (Perplexity API)
m5.model = "sonar"
m5.max_results = 10
m5.rate_limit_delay = 1.0
m5.timeout_seconds = 30

## M4 Quality Check Configuration
m4.model = "gpt-5-nano-2025-08-07"
m4.quality_threshold = 0.6
m4.batch_size = 5
m4.timeout_seconds = 10

## ReRanker Configuration
rr.top_k = 10

## Evidence Aggregation
ea.merge_strategy = "prefer_internal"

## Interaction and Feedback
ia.enable_feedback = false
ia.log_level = "INFO"

## API Configuration
api.host = "0.0.0.0"
api.port = 8000
api.workers = 4