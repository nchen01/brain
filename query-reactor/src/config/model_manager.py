"""Model management utilities for QueryReactor system."""

import logging
from typing import Dict, Any, Optional, List
from .models import (
    SUPPORTED_MODELS, 
    ModelConfig, 
    GPT5Parameters, 
    get_model_config,
    is_gpt5_model,
    get_default_gpt5_params,
    resolve_model_name,
    ReasoningEffort,
    Verbosity,
    ToolMode
)
from .settings import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model selection and parameter configuration."""
    
    def __init__(self):
        self.default_model = settings.default_model
        self.fallback_model = getattr(settings, 'fallback_model', 'gpt-4o-mini')
    
    def get_model_for_task(self, task_type: str, config_key: Optional[str] = None) -> str:
        """Get the appropriate model for a specific task.
        
        Args:
            task_type: Type of task (e.g., 'qa', 'retrieval', 'answer_creation')
            config_key: Optional config key to override default model
            
        Returns:
            Model name to use
        """
        # Try to get model from config key first
        if config_key:
            from .loader import config_loader
            configured_model = config_loader.get_config(config_key, None)
            if configured_model and self.is_model_supported(configured_model):
                return resolve_model_name(configured_model)
        
        # Task-specific model selection
        task_models = {
            'qa': self.default_model,
            'clarity_assessment': 'gpt-5-nano-2025-08-07',   # Use nano model for LLM-based assessment
            'query_preprocessing': 'gpt-5-mini-2025-08-07',  # Balanced for text processing
            'retrieval_quality': 'gpt-5-nano-2025-08-07',   # Fast for scoring
            'answer_creation': 'gpt-5-2025-08-07',           # Full model for complex generation
            'answer_checking': 'gpt-5-mini-2025-08-07',     # Balanced for validation
            'multihop': 'gpt-5-2025-08-07',                 # Full model for complex reasoning
        }
        
        selected_model = task_models.get(task_type, self.default_model)
        
        # Validate model is supported
        if not self.is_model_supported(selected_model):
            logger.warning(f"Model {selected_model} not supported, falling back to {self.fallback_model}")
            return self.fallback_model
        
        return resolve_model_name(selected_model)
    
    def is_model_supported(self, model_name: str) -> bool:
        """Check if a model is supported."""
        resolved_name = resolve_model_name(model_name)
        return resolved_name in SUPPORTED_MODELS
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a model."""
        resolved_name = resolve_model_name(model_name)
        return get_model_config(resolved_name)
    
    def prepare_api_params(self, model_name: str, custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare API parameters for a model call.
        
        Args:
            model_name: Name of the model to use
            custom_params: Custom parameters to override defaults
            
        Returns:
            Dictionary of API parameters
        """
        resolved_name = resolve_model_name(model_name)
        config = self.get_model_config(resolved_name)
        
        if not config:
            logger.error(f"No configuration found for model: {resolved_name}")
            return {"model": resolved_name}
        
        # Start with default parameters
        params = {"model": resolved_name}
        params.update(config.default_params)
        
        # Handle GPT-5 specific parameters
        if is_gpt5_model(resolved_name):
            gpt5_params = get_default_gpt5_params(resolved_name)
            
            # Apply custom GPT-5 parameters if provided
            if custom_params:
                gpt5_custom = GPT5Parameters(**{k: v for k, v in custom_params.items() 
                                               if k in GPT5Parameters.model_fields})
                # Merge with defaults
                for field_name, field_value in gpt5_custom.model_dump(exclude_none=True).items():
                    setattr(gpt5_params, field_name, field_value)
            
            # Convert to API parameters
            params.update(gpt5_params.to_api_params())
        
        # Apply any remaining custom parameters
        if custom_params:
            non_gpt5_params = {k: v for k, v in custom_params.items() 
                             if k not in GPT5Parameters.model_fields}
            params.update(non_gpt5_params)
        
        return params
    
    def get_api_endpoint(self, model_name: str) -> str:
        """Get the appropriate API endpoint for a model."""
        resolved_name = resolve_model_name(model_name)
        config = self.get_model_config(resolved_name)
        
        if config and config.supports_responses_api:
            return config.api_endpoint
        
        return "/v1/chat/completions"  # Default endpoint
    
    def optimize_params_for_task(self, model_name: str, task_type: str) -> Dict[str, Any]:
        """Get optimized parameters for a specific task type.
        
        Args:
            model_name: Name of the model
            task_type: Type of task to optimize for
            
        Returns:
            Optimized parameters dictionary
        """
        resolved_name = resolve_model_name(model_name)
        
        # Task-specific optimizations for GPT-5
        if is_gpt5_model(resolved_name):
            task_optimizations = {
                'qa': {
                    'reasoning_effort': ReasoningEffort.MEDIUM,
                    'verbosity': Verbosity.MEDIUM,
                    'temperature': 0.7
                },
                'clarity_assessment': {
                    'reasoning_effort': ReasoningEffort.MEDIUM,  # Increased for better language understanding
                    'verbosity': Verbosity.MEDIUM,               # More detailed analysis
                    'temperature': 0.5,                         # Slightly higher for nuanced judgment
                    'max_output_tokens': 200                    # More space for reasoning
                },
                'query_preprocessing': {
                    'reasoning_effort': ReasoningEffort.LOW,
                    'verbosity': Verbosity.MEDIUM,
                    'temperature': 0.5
                },
                'retrieval_quality': {
                    'reasoning_effort': ReasoningEffort.LOW,
                    'verbosity': Verbosity.LOW,
                    'temperature': 0.2,
                    'max_output_tokens': 200
                },
                'answer_creation': {
                    'reasoning_effort': ReasoningEffort.HIGH,
                    'verbosity': Verbosity.HIGH,
                    'temperature': 0.7,
                    'max_output_tokens': 4096
                },
                'answer_checking': {
                    'reasoning_effort': ReasoningEffort.MEDIUM,
                    'verbosity': Verbosity.MEDIUM,
                    'temperature': 0.3
                },
                'multihop': {
                    'reasoning_effort': ReasoningEffort.HIGH,
                    'verbosity': Verbosity.HIGH,
                    'temperature': 0.6,
                    'max_output_tokens': 6144
                }
            }
            
            optimization = task_optimizations.get(task_type, {})
            return self.prepare_api_params(resolved_name, optimization)
        
        # Default parameters for non-GPT-5 models
        return self.prepare_api_params(resolved_name)
    
    def list_available_models(self) -> List[str]:
        """List all available models."""
        return list(SUPPORTED_MODELS.keys())
    
    def list_gpt5_models(self) -> List[str]:
        """List available GPT-5 models."""
        return [name for name in SUPPORTED_MODELS.keys() if is_gpt5_model(name)]
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        resolved_name = resolve_model_name(model_name)
        config = self.get_model_config(resolved_name)
        
        if not config:
            return {"error": f"Model {resolved_name} not found"}
        
        return {
            "name": config.name,
            "provider": config.provider.value,
            "tier": config.tier.value,
            "capabilities": config.capabilities.model_dump(),
            "supports_gpt5_features": is_gpt5_model(resolved_name),
            "api_endpoint": config.api_endpoint,
            "default_params": config.default_params
        }


# Global model manager instance
model_manager = ModelManager()