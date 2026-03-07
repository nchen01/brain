"""Tests for configuration loading reliability."""

import pytest
from pathlib import Path
import tempfile
import os

from src.config.loader import ConfigLoader
from src.modules.m1_query_preprocessor_langgraph import QueryPreprocessorLangGraph


class TestConfigLoading:
    """Test configuration loading in various scenarios."""
    
    def test_config_loader_lazy_loading(self):
        """Test that config loader loads prompts lazily."""
        # Create a temporary config directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test prompts.md file
            prompts_file = temp_path / "prompts.md"
            prompts_file.write_text("""
## test_prompt
This is a test prompt for validation.

## m1_decomposition
Test decomposition prompt with required fields.
""")
            
            # Create config loader with temp directory
            loader = ConfigLoader(temp_path)
            
            # Initially, prompts should not be loaded
            assert not loader._prompts_loaded
            assert len(loader.prompts) == 0
            
            # Getting a prompt should trigger loading
            prompt = loader.get_prompt("test_prompt", "default")
            
            # Now prompts should be loaded
            assert loader._prompts_loaded
            assert len(loader.prompts) > 0
            assert "This is a test prompt" in prompt
    
    def test_module_initialization_loads_config(self):
        """Test that module initialization automatically loads config."""
        # This should not raise an exception and should load prompts
        m1 = QueryPreprocessorLangGraph()
        
        # Verify that prompts are loaded
        from src.config.loader import config_loader
        assert config_loader._prompts_loaded
        assert len(config_loader.prompts) > 0
        
        # Verify specific M1 prompts are loaded
        decomp_prompt = config_loader.get_prompt("m1_decomposition", "NOT_FOUND")
        assert decomp_prompt != "NOT_FOUND"
        assert "DECOMPOSITION EXAMPLES" in decomp_prompt
    
    def test_config_loading_resilience(self):
        """Test that config loading handles missing files gracefully."""
        # Create a temporary directory without config files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create config loader with empty directory
            loader = ConfigLoader(temp_path)
            
            # Should not raise exception
            loader.load_all()
            
            # Should be marked as loaded even with missing files
            assert loader._config_loaded
            assert loader._prompts_loaded
            
            # Should return defaults for missing prompts
            prompt = loader.get_prompt("missing_prompt", "default_value")
            assert prompt == "default_value"
    
    def test_multiple_module_initialization(self):
        """Test that multiple modules can be initialized without conflicts."""
        # Initialize multiple modules
        m1_1 = QueryPreprocessorLangGraph()
        m1_2 = QueryPreprocessorLangGraph()
        
        # Both should work without issues
        assert m1_1.module_code == "M1_LG"
        assert m1_2.module_code == "M1_LG"
        
        # Config should only be loaded once
        from src.config.loader import config_loader
        assert config_loader._prompts_loaded
    
    def test_prompt_validation(self):
        """Test that prompt validation works correctly."""
        m1 = QueryPreprocessorLangGraph()
        
        # Should have loaded all required M1 prompts
        from src.config.loader import config_loader
        
        required_prompts = ["m1_normalization", "m1_reference_resolution", "m1_decomposition"]
        for prompt_key in required_prompts:
            prompt = config_loader.get_prompt(prompt_key, "MISSING")
            assert prompt != "MISSING", f"Required prompt {prompt_key} is missing"
            assert len(prompt) > 50, f"Prompt {prompt_key} seems too short: {len(prompt)} chars"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])