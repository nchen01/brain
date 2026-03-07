# Supported AI Models in QueryReactor

This document lists all supported AI models and their configurations in the QueryReactor system.

## GPT-5 Models (2025) - Recommended

### GPT-5 Standard Models

#### `gpt-5` / `gpt-5-2025-08-07`
- **Tier**: Standard (Full capability)
- **Context Window**: 128,000 tokens
- **Max Output**: 8,192 tokens
- **Features**: Full reasoning, vision, tools, CFG
- **Best For**: Complex reasoning, comprehensive answers, multi-hop queries
- **Default Parameters**:
  - `reasoning_effort`: medium
  - `verbosity`: medium
  - `temperature`: 0.7
  - `max_output_tokens`: 4096

#### `gpt-5-mini` / `gpt-5-mini-2025-08-07`
- **Tier**: Mini (Balanced speed/cost)
- **Context Window**: 64,000 tokens
- **Max Output**: 4,096 tokens
- **Features**: Reasoning, vision, tools, CFG
- **Best For**: General queries, balanced performance
- **Default Parameters**:
  - `reasoning_effort`: low
  - `verbosity`: medium
  - `temperature`: 0.7
  - `max_output_tokens`: 2048

#### `gpt-5-nano` / `gpt-5-nano-2025-08-07`
- **Tier**: Nano (Fastest, lowest cost)
- **Context Window**: 32,000 tokens
- **Max Output**: 2,048 tokens
- **Features**: Basic reasoning, tools (no vision, no CFG)
- **Best For**: Simple tasks, quick responses, scoring
- **Default Parameters**:
  - `reasoning_effort`: minimal
  - `verbosity`: low
  - `temperature`: 0.7
  - `max_output_tokens`: 1024

## GPT-5 Advanced Parameters

GPT-5 models support advanced parameters for fine-grained control:

### Reasoning Control
- **`reasoning_effort`**: `minimal` | `low` | `medium` | `high`
  - Controls thinking depth and processing time
  - Higher effort = better accuracy but slower response

- **`reasoning_mode`**: `fast` | `balanced` | `deep`
  - Controls reasoning approach
  - `deep` mode provides most thorough analysis

### Response Control
- **`verbosity`**: `low` | `medium` | `high`
  - Controls response detail level
  - Replaces some temperature control functionality

### Tool Control
- **`allowed_tools`**: List of allowed tool names
- **`tool_mode`**: `auto` | `required` | `none`
  - Fine-grained control over tool usage

### Advanced Features
- **`context_free_grammar`**: Enable CFG constraints
- **`cfg_rules`**: Custom grammar rules
- **`preamble`**: Pre-execution explanation

## GPT-4 Models (Legacy Support)

### `gpt-4o`
- **Tier**: Standard
- **Context Window**: 128,000 tokens
- **Max Output**: 4,096 tokens
- **Features**: Tools, vision
- **Best For**: Legacy compatibility

### `gpt-4o-mini`
- **Tier**: Mini
- **Context Window**: 128,000 tokens
- **Max Output**: 4,096 tokens
- **Features**: Tools, vision
- **Best For**: Cost-effective legacy option

### `gpt-4-turbo`
- **Tier**: Standard
- **Context Window**: 128,000 tokens
- **Max Output**: 4,096 tokens
- **Features**: Tools, vision
- **Best For**: Legacy high-performance tasks

### `gpt-3.5-turbo`
- **Tier**: Mini
- **Context Window**: 16,385 tokens
- **Max Output**: 4,096 tokens
- **Features**: Basic tools (no vision)
- **Best For**: Simple legacy tasks

## Task-Specific Model Recommendations

### Query Clarity Assessment (M0)
- **Recommended**: `gpt-5-nano-2025-08-07`
- **Reasoning**: Fast, simple scoring task
- **Parameters**: `reasoning_effort: minimal`, `verbosity: low`

### Query Preprocessing (M1)
- **Recommended**: `gpt-5-mini-2025-08-07`
- **Reasoning**: Balanced text processing
- **Parameters**: `reasoning_effort: low`, `verbosity: medium`

### Retrieval Quality Check (M4)
- **Recommended**: `gpt-5-nano-2025-08-07`
- **Reasoning**: Fast scoring and validation
- **Parameters**: `reasoning_effort: low`, `verbosity: low`

### Answer Creation (M10)
- **Recommended**: `gpt-5-2025-08-07`
- **Reasoning**: Complex generation requiring full capabilities
- **Parameters**: `reasoning_effort: high`, `verbosity: high`

### Answer Checking (M11)
- **Recommended**: `gpt-5-mini-2025-08-07`
- **Reasoning**: Balanced validation task
- **Parameters**: `reasoning_effort: medium`, `verbosity: medium`

### Multi-hop Orchestration (M6)
- **Recommended**: `gpt-5-2025-08-07`
- **Reasoning**: Complex reasoning across multiple steps
- **Parameters**: `reasoning_effort: high`, `verbosity: high`

## Model Aliases

For convenience, the following aliases are supported:

- `gpt5` → `gpt-5`
- `gpt5-mini` → `gpt-5-mini`
- `gpt5-nano` → `gpt-5-nano`
- `gpt4o` → `gpt-4o`
- `gpt4o-mini` → `gpt-4o-mini`
- `gpt4-turbo` → `gpt-4-turbo`
- `gpt35-turbo` → `gpt-3.5-turbo`

## Configuration

### Environment Variables
Set your preferred default model in `.env`:
```bash
# Use latest GPT-5 mini as default
DEFAULT_MODEL=gpt-5-mini-2025-08-07

# Fallback to GPT-4o-mini if GPT-5 unavailable
FALLBACK_MODEL=gpt-4o-mini
```

### Module-Specific Configuration
Override models for specific modules in `config.md`:
```
# Use GPT-5 standard for answer creation
ac.model = gpt-5-2025-08-07

# Use GPT-5 nano for quick assessments
qa.model = gpt-5-nano-2025-08-07
```

### Programmatic Usage
```python
from src.config.model_manager import model_manager

# Get optimized model for task
model = model_manager.get_model_for_task('answer_creation')

# Get optimized parameters
params = model_manager.optimize_params_for_task(model, 'answer_creation')

# Check model capabilities
info = model_manager.get_model_info('gpt-5-mini-2025-08-07')
```

## API Endpoints

- **GPT-5 Models**: Use `/v1/responses` endpoint (new Responses API)
- **GPT-4 Models**: Use `/v1/chat/completions` endpoint (legacy)

The system automatically selects the correct endpoint based on the model.

## Cost Optimization

### By Task Complexity
- **Simple tasks** (scoring, validation): Use `gpt-5-nano`
- **Medium tasks** (text processing): Use `gpt-5-mini`
- **Complex tasks** (reasoning, generation): Use `gpt-5`

### By Speed Requirements
- **Fastest**: `gpt-5-nano` with `reasoning_effort: minimal`
- **Balanced**: `gpt-5-mini` with `reasoning_effort: low`
- **Most Accurate**: `gpt-5` with `reasoning_effort: high`

## Migration from GPT-4

1. **Update model names** in configuration files
2. **Test with GPT-5 mini** first for compatibility
3. **Optimize parameters** using new GPT-5 features
4. **Monitor performance** and adjust reasoning effort as needed

## Future Model Support

The system is designed to easily add new models. To add support for new models:

1. Update `src/config/models.py` with model configuration
2. Add any new parameters to `GPT5Parameters` class
3. Update task-specific optimizations in `ModelManager`
4. Add integration tests for the new model