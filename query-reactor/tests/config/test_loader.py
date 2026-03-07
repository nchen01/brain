"""Tests for configuration loader based on specification requirements."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.loader import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader per Requirement 7 - configuration and credential management."""
    
    def test_config_loader_initialization_spec_7_1(self):
        """Test ConfigLoader initialization per Requirement 7.1."""
        loader = ConfigLoader()
        
        assert loader.config == {}
        assert loader.prompts == {}
        assert loader.config_dir is not None
    
    def test_config_loader_custom_directory_spec_7_1(self):
        """Test ConfigLoader with custom config directory."""
        custom_dir = Path("/tmp/test_config")
        loader = ConfigLoader(config_dir=custom_dir)
        
        assert loader.config_dir == custom_dir
    
    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_env_spec_7_2(self):
        """Test environment variable retrieval per Requirement 7.2."""
        loader = ConfigLoader()
        
        # Test existing environment variable
        value = loader.get_env("TEST_VAR")
        assert value == "test_value"
        
        # Test non-existing with default
        value = loader.get_env("NON_EXISTING", "default")
        assert value == "default"
        
        # Test non-existing without default
        value = loader.get_env("NON_EXISTING")
        assert value is None
    
    @patch("builtins.open", mock_open(read_data="""
# Test configuration file
model.name = "gpt-4"
qa.min_conf = 0.8
qa.max_turns = 3
debug = true
timeout = 30
temperature = 0.7
"""))
    def test_load_config_spec_7_1(self):
        """Test configuration loading from config.md per Requirement 7.1."""
        loader = ConfigLoader()
        
        with patch.object(Path, 'exists', return_value=True):
            loader.load_config()
        
        # Test nested configuration
        assert loader.get_config("model.name") == "gpt-4"
        assert loader.get_config("qa.min_conf") == 0.8
        assert loader.get_config("qa.max_turns") == 3
        
        # Test boolean conversion
        assert loader.get_config("debug") is True
        
        # Test numeric conversion
        assert loader.get_config("timeout") == 30
        assert loader.get_config("temperature") == 0.7
    
    @patch("builtins.open", mock_open(read_data="""
## m0_clarity_assessment
Assess the clarity of this query on a scale of 0.0 to 1.0.
Consider ambiguity, missing context, and specificity.

## m1_decomposition
Break down this complex query into simpler, standalone sub-questions.

## m10_answer_generation
Generate a comprehensive answer based on the provided evidence.
Include proper citations and maintain factual accuracy.
"""))
    def test_load_prompts_spec_7_3(self):
        """Test prompt loading from prompts.md per Requirement 7.3."""
        loader = ConfigLoader()
        
        with patch.object(Path, 'exists', return_value=True):
            loader.load_prompts()
        
        # Test prompt retrieval
        clarity_prompt = loader.get_prompt("m0_clarity_assessment")
        assert "Assess the clarity" in clarity_prompt
        assert "0.0 to 1.0" in clarity_prompt
        
        decomp_prompt = loader.get_prompt("m1_decomposition")
        assert "Break down this complex query" in decomp_prompt
        
        answer_prompt = loader.get_prompt("m10_answer_generation")
        assert "Generate a comprehensive answer" in answer_prompt
        assert "citations" in answer_prompt
    
    def test_get_config_with_default_spec_7_1(self):
        """Test configuration retrieval with default values."""
        loader = ConfigLoader()
        
        # Test non-existing key with default
        value = loader.get_config("non.existing.key", "default_value")
        assert value == "default_value"
        
        # Test non-existing key without default
        value = loader.get_config("non.existing.key")
        assert value is None
    
    def test_get_prompt_with_default_spec_7_3(self):
        """Test prompt retrieval with default values."""
        loader = ConfigLoader()
        
        # Test non-existing prompt with default
        prompt = loader.get_prompt("non_existing_prompt", "default prompt")
        assert prompt == "default prompt"
        
        # Test non-existing prompt without default
        prompt = loader.get_prompt("non_existing_prompt")
        assert prompt == ""
    
    def test_langsmith_tracing_setup_spec_8_4(self):
        """Test LangSmith tracing setup per Requirement 8.4."""
        loader = ConfigLoader()
        
        # Verify LangSmith environment variables are properly loaded
        # (The actual values come from .env file)
        langchain_tracing = os.getenv("LANGCHAIN_TRACING_V2")
        langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
        langchain_project = os.getenv("LANGCHAIN_PROJECT")
        
        # Test that the configuration loader can access these values
        assert langchain_tracing is not None
        assert langchain_api_key is not None
        assert langchain_project is not None
        
        # Test the get_env method (handle case differences)
        assert loader.get_env("LANGCHAIN_TRACING_V2").lower() == langchain_tracing.lower()
        assert loader.get_env("LANGCHAIN_API_KEY") == langchain_api_key
        assert loader.get_env("LANGCHAIN_PROJECT") == langchain_project
    
    @patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "false"})
    def test_langsmith_tracing_disabled_spec_8_4(self):
        """Test LangSmith tracing when disabled."""
        loader = ConfigLoader()
        
        # Should not raise any errors when tracing is disabled
        assert loader is not None
    
    def test_nested_config_setting(self):
        """Test setting nested configuration values."""
        loader = ConfigLoader()
        
        # Test setting nested values
        loader._set_nested_config("level1.level2.key", "value")
        
        assert loader.config["level1"]["level2"]["key"] == "value"
        assert loader.get_config("level1.level2.key") == "value"
    
    def test_is_float_validation(self):
        """Test float validation helper method."""
        loader = ConfigLoader()
        
        assert loader._is_float("3.14") is True
        assert loader._is_float("42") is True
        assert loader._is_float("not_a_number") is False
        assert loader._is_float("") is False
    
    @patch("builtins.open", mock_open(read_data="""
# Configuration with various types
string_value = "hello world"
quoted_string = "quoted value"
integer_value = 42
float_value = 3.14
boolean_true = true
boolean_false = false
"""))
    def test_config_type_conversion_spec_7_1(self):
        """Test configuration value type conversion."""
        loader = ConfigLoader()
        
        with patch.object(Path, 'exists', return_value=True):
            loader.load_config()
        
        # Test string values
        assert loader.get_config("string_value") == "hello world"
        assert loader.get_config("quoted_string") == "quoted value"
        
        # Test numeric values
        assert loader.get_config("integer_value") == 42
        assert loader.get_config("float_value") == 3.14
        
        # Test boolean values
        assert loader.get_config("boolean_true") is True
        assert loader.get_config("boolean_false") is False
    
    def test_load_all_configuration_spec_7_1(self):
        """Test loading all configuration files at once."""
        loader = ConfigLoader()
        
        with patch.object(loader, 'load_config') as mock_config, \
             patch.object(loader, 'load_prompts') as mock_prompts:
            
            loader.load_all()
            
            mock_config.assert_called_once()
            mock_prompts.assert_called_once()
    
    def test_missing_config_file_handling_spec_7_1(self):
        """Test graceful handling of missing configuration files."""
        loader = ConfigLoader()
        
        with patch.object(Path, 'exists', return_value=False):
            # Should not raise exception for missing files
            loader.load_config()
            loader.load_prompts()
        
        # Config should remain empty but loader should be functional
        assert loader.config == {}
        assert loader.prompts == {}