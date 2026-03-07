"""Tests for model manager functionality."""

import pytest
from src.config.model_manager import ModelManager, model_manager
from src.config.models import (
    get_model_config, 
    is_gpt5_model, 
    resolve_model_name,
    ReasoningEffort,
    Verbosity
)


class TestModelManager:
    """Test model manager functionality."""
    
    def test_model_manager_initialization(self):
        """Test model manager initializes correctly."""
        manager = ModelManager()
        assert manager.default_model is not None
        assert manager.fallback_model is not None
    
    def test_get_model_for_task(self):
        """Test getting appropriate model for different tasks."""
        manager = ModelManager()
        
        # Test different task types
        qa_model = manager.get_model_for_task('qa')
        assert qa_model is not None
        
        clarity_model = manager.get_model_for_task('clarity_assessment')
        assert clarity_model is not None
        
        answer_model = manager.get_model_for_task('answer_creation')
        assert answer_model is not None
    
    def test_is_model_supported(self):
        """Test model support checking."""
        manager = ModelManager()
        
        # Test supported models
        assert manager.is_model_supported('gpt-5-mini-2025-08-07')
        assert manager.is_model_supported('gpt-4o-mini')
        assert manager.is_model_supported('gpt5-mini')  # Alias
        
        # Test unsupported model
        assert not manager.is_model_supported('nonexistent-model')
    
    def test_prepare_api_params(self):
        """Test API parameter preparation."""
        manager = ModelManager()
        
        # Test GPT-5 model parameters
        params = manager.prepare_api_params('gpt-5-mini-2025-08-07')
        assert 'model' in params
        assert params['model'] == 'gpt-5-mini-2025-08-07'
        assert 'reasoning_effort' in params
        assert 'verbosity' in params
        
        # Test GPT-4 model parameters
        params = manager.prepare_api_params('gpt-4o-mini')
        assert 'model' in params
        assert params['model'] == 'gpt-4o-mini'
        # GPT-4 shouldn't have GPT-5 specific params
        assert 'reasoning_effort' not in params
        assert 'verbosity' not in params
    
    def test_prepare_api_params_with_custom(self):
        """Test API parameter preparation with custom parameters."""
        manager = ModelManager()
        
        custom_params = {
            'reasoning_effort': ReasoningEffort.HIGH,
            'verbosity': Verbosity.LOW,
            'temperature': 0.5
        }
        
        params = manager.prepare_api_params('gpt-5-mini-2025-08-07', custom_params)
        assert params['reasoning_effort'] == 'high'
        assert params['verbosity'] == 'low'
        assert params['temperature'] == 0.5
    
    def test_get_api_endpoint(self):
        """Test API endpoint selection."""
        manager = ModelManager()
        
        # GPT-5 should use responses API
        endpoint = manager.get_api_endpoint('gpt-5-mini-2025-08-07')
        assert endpoint == '/v1/responses'
        
        # GPT-4 should use chat completions API
        endpoint = manager.get_api_endpoint('gpt-4o-mini')
        assert endpoint == '/v1/chat/completions'
    
    def test_optimize_params_for_task(self):
        """Test task-specific parameter optimization."""
        manager = ModelManager()
        
        # Test clarity assessment optimization (should be fast/minimal)
        params = manager.optimize_params_for_task('gpt-5-mini-2025-08-07', 'clarity_assessment')
        assert params['reasoning_effort'] == 'minimal'
        assert params['verbosity'] == 'low'
        
        # Test answer creation optimization (should be thorough)
        params = manager.optimize_params_for_task('gpt-5-2025-08-07', 'answer_creation')
        assert params['reasoning_effort'] == 'high'
        assert params['verbosity'] == 'high'
    
    def test_list_available_models(self):
        """Test listing available models."""
        manager = ModelManager()
        
        models = manager.list_available_models()
        assert len(models) > 0
        assert 'gpt-5-mini-2025-08-07' in models
        assert 'gpt-4o-mini' in models
    
    def test_list_gpt5_models(self):
        """Test listing GPT-5 models."""
        manager = ModelManager()
        
        gpt5_models = manager.list_gpt5_models()
        assert len(gpt5_models) > 0
        
        for model in gpt5_models:
            assert model.startswith('gpt-5')
    
    def test_get_model_info(self):
        """Test getting model information."""
        manager = ModelManager()
        
        info = manager.get_model_info('gpt-5-mini-2025-08-07')
        assert 'name' in info
        assert 'provider' in info
        assert 'tier' in info
        assert 'capabilities' in info
        assert info['supports_gpt5_features'] is True
        
        # Test GPT-4 model
        info = manager.get_model_info('gpt-4o-mini')
        assert info['supports_gpt5_features'] is False
    
    def test_global_model_manager(self):
        """Test global model manager instance."""
        assert model_manager is not None
        assert isinstance(model_manager, ModelManager)


class TestModelUtilities:
    """Test model utility functions."""
    
    def test_is_gpt5_model(self):
        """Test GPT-5 model detection."""
        assert is_gpt5_model('gpt-5')
        assert is_gpt5_model('gpt-5-mini')
        assert is_gpt5_model('gpt-5-nano-2025-08-07')
        
        assert not is_gpt5_model('gpt-4o')
        assert not is_gpt5_model('gpt-4o-mini')
        assert not is_gpt5_model('gpt-3.5-turbo')
    
    def test_resolve_model_name(self):
        """Test model name resolution from aliases."""
        assert resolve_model_name('gpt5') == 'gpt-5'
        assert resolve_model_name('gpt5-mini') == 'gpt-5-mini'
        assert resolve_model_name('gpt4o') == 'gpt-4o'
        
        # Non-alias should return original
        assert resolve_model_name('gpt-5-mini-2025-08-07') == 'gpt-5-mini-2025-08-07'
    
    def test_get_model_config(self):
        """Test getting model configuration."""
        config = get_model_config('gpt-5-mini-2025-08-07')
        assert config is not None
        assert config.name == 'gpt-5-mini-2025-08-07'
        assert config.tier.value == 'mini'
        
        # Non-existent model
        config = get_model_config('nonexistent-model')
        assert config is None