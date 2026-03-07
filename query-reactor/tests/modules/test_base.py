"""Tests for base module classes based on specification requirements."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.modules.base import BaseModule, LLMModule, RetrievalModule
from src.models.state import ReactorState
from src.models.core import UserQuery


class ConcreteBaseModule(BaseModule):
    """Concrete implementation of BaseModule for testing."""
    
    async def execute(self, state: ReactorState) -> ReactorState:
        return state


class ConcreteLLMModule(LLMModule):
    """Concrete implementation of LLMModule for testing."""
    
    async def execute(self, state: ReactorState) -> ReactorState:
        return state


class ConcreteRetrievalModule(RetrievalModule):
    """Concrete implementation of RetrievalModule for testing."""
    
    async def execute(self, state: ReactorState) -> ReactorState:
        return state


class TestBaseModule:
    """Test BaseModule functionality per Requirements 8.1, 8.2 - logging and observability."""
    
    def test_base_module_initialization_spec_8_2(self):
        """Test BaseModule initialization with module code per Requirement 8.2."""
        module = ConcreteBaseModule("M1")
        
        assert module.module_code == "M1"
        assert module.logger is not None
        assert module.logger.name == "queryreactor.m1"
    
    def test_base_module_logging_execution_start_spec_8_1(self, sample_reactor_state):
        """Test execution start logging per Requirement 8.1."""
        module = ConcreteBaseModule("M1")
        
        with patch.object(module.logger, 'info') as mock_log:
            module._log_execution_start(sample_reactor_state, "Processing query")
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "[M1]" in call_args
            assert "Starting execution" in call_args
            assert "Processing query" in call_args
    
    def test_base_module_logging_execution_end_spec_8_1(self, sample_reactor_state):
        """Test execution end logging per Requirement 8.1."""
        module = ConcreteBaseModule("M1")
        
        with patch.object(module.logger, 'info') as mock_log:
            module._log_execution_end(sample_reactor_state, "Completed successfully")
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "[M1]" in call_args
            assert "Execution completed" in call_args
            assert "Completed successfully" in call_args
    
    def test_base_module_logging_error_spec_8_1(self, sample_reactor_state):
        """Test error logging per Requirement 8.1."""
        module = ConcreteBaseModule("M1")
        error = Exception("Test error")
        
        with patch.object(module.logger, 'error') as mock_log:
            module._log_error(sample_reactor_state, error)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "[M1]" in call_args
            assert "Error" in call_args
            assert "Test error" in call_args
    
    def test_base_module_get_config_spec_7_1(self):
        """Test configuration retrieval per Requirement 7.1."""
        module = ConcreteBaseModule("M1")
        
        with patch('src.modules.base.config_loader') as mock_loader:
            mock_loader.get_config.return_value = "test_value"
            
            result = module._get_config("test.key", "default")
            
            mock_loader.get_config.assert_called_once_with("test.key", "default")
            assert result == "test_value"
    
    def test_base_module_get_prompt_spec_7_3(self):
        """Test prompt retrieval per Requirement 7.3."""
        module = ConcreteBaseModule("M1")
        
        with patch('src.modules.base.config_loader') as mock_loader:
            mock_loader.get_prompt.return_value = "test prompt"
            
            result = module._get_prompt("test_prompt", "default")
            
            mock_loader.get_prompt.assert_called_once_with("test_prompt", "default")
            assert result == "test prompt"
    
    def test_base_module_update_state_module_spec_8_2(self, sample_reactor_state):
        """Test state module update per Requirement 8.2."""
        module = ConcreteBaseModule("M1")
        
        module._update_state_module(sample_reactor_state)
        
        assert sample_reactor_state.current_module == "M1"


class TestLLMModule:
    """Test LLMModule functionality for LLM-based modules."""
    
    def test_llm_module_initialization_spec_7_1(self):
        """Test LLMModule initialization with model config key."""
        module = ConcreteLLMModule("M1", "qa.model")
        
        assert module.module_code == "M1"
        assert module.model_config_key == "qa.model"
    
    def test_llm_module_get_model_name_spec_7_1(self):
        """Test model name retrieval from configuration."""
        module = ConcreteLLMModule("M1", "qa.model")
        
        # Test that model manager is used for model selection
        model_name = module._get_model_name()
        
        # Should return a valid model name (could be any supported model)
        assert model_name is not None
        assert isinstance(model_name, str)
        assert len(model_name) > 0
        
        # Should be a supported model
        from src.config.model_manager import model_manager
        assert model_manager.is_model_supported(model_name)
    
    @pytest.mark.asyncio
    async def test_llm_module_call_llm_placeholder_spec_v1_0(self):
        """Test LLM call placeholder implementation for V1.0."""
        module = ConcreteLLMModule("M1", "qa.model")
        
        with patch.object(module, '_get_model_name', return_value="gpt-5-nano"), \
             patch.object(module, '_simulate_processing_time', new_callable=AsyncMock), \
             patch.object(module.logger, 'debug'):
            
            result = await module._call_llm("Test prompt", {"key": "value"})
            
            assert isinstance(result, str)
            assert "[M1]" in result
            assert "Placeholder response" in result
    
    @pytest.mark.asyncio
    async def test_llm_module_simulate_processing_time(self):
        """Test LLM processing time simulation."""
        module = ConcreteLLMModule("M1", "qa.model")
        
        import time
        start_time = time.time()
        await module._simulate_processing_time()
        end_time = time.time()
        
        # Should take at least 100ms (0.1 seconds)
        assert (end_time - start_time) >= 0.1
    
    def test_llm_module_generate_placeholder_response(self):
        """Test placeholder response generation."""
        module = ConcreteLLMModule("M1", "qa.model")
        
        result = module._generate_placeholder_response("Test prompt", {"key": "value"})
        
        assert "[M1]" in result
        assert "Placeholder response" in result
        assert "Test prompt" in result


class TestRetrievalModule:
    """Test RetrievalModule functionality for retrieval paths."""
    
    def test_retrieval_module_initialization(self):
        """Test RetrievalModule initialization with path ID."""
        module = ConcreteRetrievalModule("M3", "P1")
        
        assert module.module_code == "M3"
        assert module.path_id == "P1"
    
    def test_retrieval_module_create_dummy_evidence_spec_v1_0(self):
        """Test dummy evidence creation for V1.0 implementation."""
        module = ConcreteRetrievalModule("M3", "P1")
        
        workunit_id = str(uuid4())
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        router_decision_id = str(uuid4())
        
        evidence = module._create_dummy_evidence(
            workunit_id=workunit_id,
            user_id=user_id,
            conversation_id=conversation_id,
            router_decision_id=router_decision_id,
            content="Test evidence content",
            source_id="test_source"
        )
        
        assert str(evidence.workunit_id) == workunit_id
        assert str(evidence.user_id) == user_id
        assert str(evidence.conversation_id) == conversation_id
        assert evidence.content == "Test evidence content"
        assert evidence.score_raw == 0.8  # Dummy score
        assert evidence.provenance.source_id == "test_source"
        assert evidence.provenance.retrieval_path == "P1"
        assert str(evidence.provenance.router_decision_id) == router_decision_id
    
    def test_retrieval_module_source_type_mapping(self):
        """Test source type mapping for different paths."""
        from src.models.core import SourceType
        
        # Test P1 (Simple Retrieval) -> db
        module_p1 = ConcreteRetrievalModule("M3", "P1")
        evidence_p1 = module_p1._create_dummy_evidence(
            workunit_id=str(uuid4()),
            user_id=str(uuid4()),
            conversation_id=str(uuid4()),
            router_decision_id=str(uuid4()),
            content="Test content",
            source_id="test_source"
        )
        assert evidence_p1.provenance.source_type == SourceType.db
        
        # Test P2 (Internet Retrieval) -> web
        module_p2 = ConcreteRetrievalModule("M5", "P2")
        evidence_p2 = module_p2._create_dummy_evidence(
            workunit_id=str(uuid4()),
            user_id=str(uuid4()),
            conversation_id=str(uuid4()),
            router_decision_id=str(uuid4()),
            content="Test content",
            source_id="test_source"
        )
        assert evidence_p2.provenance.source_type == SourceType.web
        
        # Test P3 (Multi-hop Retrieval) -> api
        module_p3 = ConcreteRetrievalModule("M6", "P3")
        evidence_p3 = module_p3._create_dummy_evidence(
            workunit_id=str(uuid4()),
            user_id=str(uuid4()),
            conversation_id=str(uuid4()),
            router_decision_id=str(uuid4()),
            content="Test content",
            source_id="test_source"
        )
        assert evidence_p3.provenance.source_type == SourceType.api