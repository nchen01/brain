"""Supported AI models configuration for QueryReactor system."""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel
from enum import Enum


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelTier(str, Enum):
    """Model performance tiers."""
    NANO = "nano"      # Fastest, lowest cost
    MINI = "mini"      # Balanced speed/cost
    STANDARD = "standard"  # Full capability
    PRO = "pro"        # Highest capability


class ReasoningEffort(str, Enum):
    """GPT-5 reasoning effort levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Verbosity(str, Enum):
    """GPT-5 verbosity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReasoningMode(str, Enum):
    """GPT-5 reasoning modes."""
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class ToolMode(str, Enum):
    """GPT-5 tool usage modes."""
    AUTO = "auto"
    REQUIRED = "required"
    NONE = "none"


class ModelCapabilities(BaseModel):
    """Model capabilities and features."""
    supports_tools: bool = False
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_verbosity: bool = False
    supports_cfg: bool = False
    max_tokens: int = 4096
    context_window: int = 8192
    supports_streaming: bool = True


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    name: str
    provider: ModelProvider
    tier: ModelTier
    capabilities: ModelCapabilities
    default_params: Dict[str, Any] = {}
    api_endpoint: str = "/v1/chat/completions"
    
    # GPT-5 specific parameters
    supports_responses_api: bool = False
    default_reasoning_effort: Optional[ReasoningEffort] = None
    default_verbosity: Optional[Verbosity] = None
    default_reasoning_mode: Optional[ReasoningMode] = None


# Supported Models Configuration
SUPPORTED_MODELS: Dict[str, ModelConfig] = {
    # GPT-5 Models (2025)
    "gpt-5": ModelConfig(
        name="gpt-5",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=True,
            max_tokens=8192,
            context_window=128000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "reasoning_effort": "medium",
            "verbosity": "medium"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.MEDIUM,
        default_verbosity=Verbosity.MEDIUM,
        default_reasoning_mode=ReasoningMode.BALANCED
    ),
    
    "gpt-5-mini": ModelConfig(
        name="gpt-5-mini",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.MINI,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=True,
            max_tokens=4096,
            context_window=64000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "reasoning_effort": "low",
            "verbosity": "medium"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.LOW,
        default_verbosity=Verbosity.MEDIUM,
        default_reasoning_mode=ReasoningMode.FAST
    ),
    
    "gpt-5-nano": ModelConfig(
        name="gpt-5-nano",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.NANO,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=False,
            max_tokens=2048,
            context_window=32000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 1024,
            "reasoning_effort": "minimal",
            "verbosity": "low"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.MINIMAL,
        default_verbosity=Verbosity.LOW,
        default_reasoning_mode=ReasoningMode.FAST
    ),
    
    # GPT-5 with date suffix (2025-08-07)
    "gpt-5-2025-08-07": ModelConfig(
        name="gpt-5-2025-08-07",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=True,
            max_tokens=8192,
            context_window=128000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "reasoning_effort": "medium",
            "verbosity": "medium"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.MEDIUM,
        default_verbosity=Verbosity.MEDIUM,
        default_reasoning_mode=ReasoningMode.BALANCED
    ),
    
    "gpt-5-mini-2025-08-07": ModelConfig(
        name="gpt-5-mini-2025-08-07",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.MINI,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=True,
            max_tokens=4096,
            context_window=64000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "reasoning_effort": "low",
            "verbosity": "medium"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.LOW,
        default_verbosity=Verbosity.MEDIUM,
        default_reasoning_mode=ReasoningMode.FAST
    ),
    
    "gpt-5-nano-2025-08-07": ModelConfig(
        name="gpt-5-nano-2025-08-07",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.NANO,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_reasoning=True,
            supports_verbosity=True,
            supports_cfg=False,
            max_tokens=2048,
            context_window=32000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_output_tokens": 1024,
            "reasoning_effort": "minimal",
            "verbosity": "low"
        },
        api_endpoint="/v1/responses",
        supports_responses_api=True,
        default_reasoning_effort=ReasoningEffort.MINIMAL,
        default_verbosity=Verbosity.LOW,
        default_reasoning_mode=ReasoningMode.FAST
    ),
    
    # GPT-4 Models (Legacy Support)
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=False,
            supports_verbosity=False,
            supports_cfg=False,
            max_tokens=4096,
            context_window=128000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_tokens": 4096
        }
    ),
    
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.MINI,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=False,
            supports_verbosity=False,
            supports_cfg=False,
            max_tokens=4096,
            context_window=128000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_tokens": 4096
        }
    ),
    
    "gpt-4-turbo": ModelConfig(
        name="gpt-4-turbo",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_reasoning=False,
            supports_verbosity=False,
            supports_cfg=False,
            max_tokens=4096,
            context_window=128000,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_tokens": 4096
        }
    ),
    
    "gpt-3.5-turbo": ModelConfig(
        name="gpt-3.5-turbo",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.MINI,
        capabilities=ModelCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_reasoning=False,
            supports_verbosity=False,
            supports_cfg=False,
            max_tokens=4096,
            context_window=16385,
            supports_streaming=True
        ),
        default_params={
            "temperature": 0.7,
            "max_tokens": 4096
        }
    )
}


class GPT5Parameters(BaseModel):
    """GPT-5 specific parameters for API calls."""
    
    # Core parameters (inherited from GPT-4)
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    max_output_tokens: Optional[int] = None  # Renamed from max_tokens
    
    # GPT-5 new parameters
    verbosity: Optional[Verbosity] = None
    reasoning_effort: Optional[ReasoningEffort] = None
    reasoning_mode: Optional[ReasoningMode] = None
    
    # Tool control
    allowed_tools: Optional[List[str]] = None
    tool_mode: Optional[ToolMode] = None
    
    # Advanced features
    context_free_grammar: Optional[bool] = None
    cfg_rules: Optional[str] = None
    preamble: Optional[str] = None
    
    def to_api_params(self) -> Dict[str, Any]:
        """Convert to API parameters dictionary."""
        params = {}
        
        # Add non-None parameters
        for field_name, field_value in self.model_dump(exclude_none=True).items():
            if field_value is not None:
                # Convert enum values to strings
                if isinstance(field_value, Enum):
                    params[field_name] = field_value.value
                else:
                    params[field_name] = field_value
        
        return params


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model."""
    return SUPPORTED_MODELS.get(model_name)


def get_models_by_provider(provider: ModelProvider) -> List[ModelConfig]:
    """Get all models for a specific provider."""
    return [config for config in SUPPORTED_MODELS.values() if config.provider == provider]


def get_models_by_tier(tier: ModelTier) -> List[ModelConfig]:
    """Get all models for a specific tier."""
    return [config for config in SUPPORTED_MODELS.values() if config.tier == tier]


def is_gpt5_model(model_name: str) -> bool:
    """Check if a model is a GPT-5 variant."""
    return model_name.startswith("gpt-5")


def get_default_gpt5_params(model_name: str) -> GPT5Parameters:
    """Get default GPT-5 parameters for a model."""
    config = get_model_config(model_name)
    if not config or not is_gpt5_model(model_name):
        return GPT5Parameters()
    
    return GPT5Parameters(
        reasoning_effort=config.default_reasoning_effort,
        verbosity=config.default_verbosity,
        reasoning_mode=config.default_reasoning_mode,
        max_output_tokens=config.default_params.get("max_output_tokens"),
        temperature=config.default_params.get("temperature", 0.7)
    )


# Model aliases for convenience
MODEL_ALIASES = {
    "gpt5": "gpt-5",
    "gpt5-mini": "gpt-5-mini", 
    "gpt5-nano": "gpt-5-nano",
    "gpt4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini",
    "gpt4-turbo": "gpt-4-turbo",
    "gpt35-turbo": "gpt-3.5-turbo"
}


def resolve_model_name(model_name: str) -> str:
    """Resolve model name from alias or return original name."""
    return MODEL_ALIASES.get(model_name, model_name)


def list_all_models() -> List[str]:
    """List all supported model names."""
    return list(SUPPORTED_MODELS.keys())


def list_gpt5_models() -> List[str]:
    """List all GPT-5 model variants."""
    return [name for name in SUPPORTED_MODELS.keys() if is_gpt5_model(name)]