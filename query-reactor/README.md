# QueryReactor v1.0.0

A production-ready, modular smart query and question-answering (QA) system that routes user questions across multiple retrieval paths, aggregates evidence with provenance, and generates verifiable answers.

## Features

- **Multi-Path Retrieval**: Intelligent routing across internal databases, web search, and multi-hop reasoning
- **Evidence-Based Answers**: All responses are grounded in retrieved evidence with full citation support
- **Quality Assurance**: Built-in verification and quality checking at every stage
- **Multi-User Support**: Concurrent processing with proper user isolation and session management
- **Observability**: Comprehensive logging, metrics, and OpenTelemetry tracing
- **Configurable**: External configuration files for easy tuning without code changes
- **Centralized Prompt Management**: All prompts loaded from `prompts.md` with no hardcoded prompts
- **Robust Fallback System**: Comprehensive fallback logging with user feedback and developer debugging
- **Production Ready**: Enhanced error handling, monitoring, and reliability features

## Architecture

QueryReactor uses a graph-based workflow orchestrated by LangGraph with 13 specialized modules:

- **M0**: QA with Human (Interactive clarification)
- **M1**: Query Preprocessor (Normalization and decomposition)
- **M2**: Query Router (Path selection)
- **M3**: Simple Retrieval (Internal knowledge bases)
- **M4**: Quality Check (Evidence validation)
- **M5**: Internet Retrieval (Web search via Perplexity API)
- **M6**: Multihop Orchestrator (Multi-step reasoning)
- **M7**: Evidence Aggregator (Merge and deduplicate)
- **M8**: ReRanker (Relevance scoring with adaptive strategies)
- **M9**: Smart Controller (Intelligent flow decisions with feedback loops)
- **M10**: Answer Creator (Retrieval-only response generation)
- **M11**: Answer Check (Gatekeeper verification with quality assurance)
- **M12**: Interaction Answer (Context-aware user delivery)

### Key Architectural Improvements

- **Enhanced Fallback System**: All modules have comprehensive fallback logging with both user feedback and developer debugging
- **Centralized Prompt Management**: All 33 prompts loaded from `prompts.md` with no hardcoded prompts
- **Intelligent Flow Control**: M9 Smart Controller with WorkUnit feedback and adaptive decision making
- **Quality Gatekeeper**: M11 Answer Check with strict retrieval compliance and multi-attempt validation
- **Context-Aware Delivery**: M12 adapts responses based on routing context and quality indicators

## Quick Start

### Prerequisites

- Python 3.13+
- uv (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd QueryReactor
```

2. Set up the virtual environment:
```bash
uv init --python 3.13
```

3. Install dependencies:
```bash
uv add langgraph pydantic-ai fastapi uvicorn opentelemetry-api opentelemetry-sdk python-dotenv langsmith
```

4. Install LangGraph CLI for development (optional):
```bash
uv add --dev langgraph-cli
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the System

1. **Start the API server**:
```bash
python main.py server
```

2. **Run a test query**:
```bash
python main.py test
```

3. **Check system health**:
```bash
python main.py health
```

4. **View configuration**:
```bash
python main.py config
```

## Configuration

### Configuration Files

- **config.md**: Model assignments, thresholds, and system parameters
- **prompts.md**: Centralized prompt management - 33 prompts for all M0-M12 modules
- **.env**: Sensitive credentials and API keys (not in version control)

### Prompt Management System

QueryReactor uses a centralized prompt management system:

- **No Hardcoded Prompts**: All modules load prompts via `_get_prompt()` method
- **Single Source of Truth**: All 33 prompts stored in `prompts.md`
- **Fallback Support**: Graceful degradation when prompts fail to load
- **Version Control**: Track prompt changes through git
- **Easy Updates**: Modify prompts without code changes

### Key Configuration Options

```markdown
# Model Configuration
ac.model = "gpt-4"
qa.min_conf = 0.8
smr.min_confidence = 0.7

# Loop Limits
loop.max.smartretrieval_to_qp = 2
loop.max.answercheck_to_ac = 3

# Retrieval Configuration
qp.enable_decomposition = true
ac.allow_partial_answer = true
rr.top_k = 10
```

## API Usage

### Process a Query

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is Python programming language?",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "locale": "en-US"
  }'
```

### Response Format

```json
{
  "query_id": "uuid",
  "answer": "Python is a high-level programming language...",
  "confidence": 0.85,
  "citations": [
    {
      "id": 1,
      "title": "Python Documentation",
      "source": "internal_kb",
      "content_preview": "Python is an interpreted..."
    }
  ],
  "limitations": [],
  "metadata": {
    "workunits_processed": 1,
    "evidence_items_found": 5,
    "retrieval_paths_used": ["P1", "P2"],
    "processing_time_ms": 1250
  }
}
```

### Other Endpoints

- `GET /api/health` - Health check
- `GET /api/metrics` - Performance metrics
- `POST /api/feedback` - Submit feedback
- `GET /api/query/{query_id}/status` - Query status

## Development

### Project Structure

```
QueryReactor/
├── src/
│   ├── api/           # FastAPI service layer
│   ├── config/        # Configuration management
│   ├── logging/       # Logging setup
│   ├── models/        # Pydantic data models
│   ├── modules/       # Processing modules (M0-M12)
│   ├── observability/ # Metrics and tracing
│   ├── services/      # Business logic services
│   └── workflow/      # LangGraph orchestration
├── config.md          # System configuration
├── prompts.md         # Agent prompts
├── .env.example       # Environment template
├── main.py           # Application entry point
└── README.md         # This file
```

### Running Tests

```bash
# Run a simple test query
python main.py test

# Check system health
python main.py health
```

### Adding New Modules

1. Create module in `src/modules/`
2. Implement `BaseModule` or `LLMModule` interface
3. Add to workflow graph in `src/workflow/graph.py`
4. Update module imports in `src/modules/__init__.py`

## Version History

**Version 1.0 (Current)**:
- ✅ Complete modular architecture with 13 specialized modules
- ✅ Centralized prompt management system (33 prompts in prompts.md)
- ✅ Comprehensive fallback logging across all modules
- ✅ Enhanced M9 Smart Controller with WorkUnit feedback
- ✅ M11 Gatekeeper with strict retrieval compliance
- ✅ M12 context-aware user delivery
- ✅ Production-ready error handling and monitoring
- ✅ Real Perplexity API integration for web search
- ✅ LangGraph workflow orchestration with proper state management

**Version 1.1 (Planned)**:
- Full retrieval integration with additional data sources
- ML-based reranking models
- Advanced multi-hop reasoning capabilities
- Enhanced authentication and authorization
- Performance optimizations and caching

## Monitoring and Observability

### Enhanced Fallback Logging

All modules (M0-M12) have comprehensive fallback logging:

- **User Feedback**: Clear terminal messages when fallbacks are triggered
- **Developer Debugging**: Detailed logs for troubleshooting
- **Consistent Patterns**: Standardized fallback messaging across all modules
- **Production Ready**: Proper logging and monitoring for production deployment

```bash
# Example fallback messages
🔄 FALLBACK TRIGGERED: M8 Strategy Selection - Connection timeout
   → Using fallback adaptive strategy

🔄 EXECUTING FALLBACK: M11 Retrieval Validation - Using heuristic validation
```

### Logging

Structured JSON logging with request correlation:

```bash
# View logs
tail -f logs/queryreactor.log

# Set log level
export LOG_LEVEL=DEBUG
```

### Metrics

Built-in performance monitoring:

```bash
curl http://localhost:8000/api/metrics
```

### Tracing and Debugging

**LangSmith** (Recommended for LangGraph workflows):

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your_langsmith_api_key
export LANGCHAIN_PROJECT=queryreactor
```

**LangGraph Studio** (Local development):

```bash
# Install LangGraph CLI
pip install langgraph-cli

# Start LangGraph Studio
langgraph dev

# Access at http://localhost:8123
```

**OpenTelemetry** (General observability):

```bash
export OTEL_SERVICE_NAME=queryreactor
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Security

- Environment-based credential management
- JWT-based authentication (optional)
- Rate limiting per user
- Input validation and sanitization
- CORS configuration

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000
CMD ["python", "main.py", "server"]
```

### Environment Variables

Required for production:

```bash
# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Security
SECRET_KEY=your_secret_key

# Monitoring
OTEL_SERVICE_NAME=queryreactor
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Logging
LOG_LEVEL=INFO
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Your License Here]

## Support

For questions and support:
- Check the health endpoint: `GET /api/health`
- Review logs in `logs/queryreactor.log`
- Monitor metrics: `GET /api/metrics`