"""Test GPT-5-Nano compatibility in QueryReactor modules."""

import pytest
from src.modules.m0_qa_human import QAWithHuman
from src.models.state import ReactorState
from src.models.core import UserQuery
from uuid import uuid4
from datetime import datetime


class TestGPT5NanoCompatibility:
    """Test GPT-5-Nano compatibility."""
    
    @pytest.mark.asyncio
    async def test_gpt5_nano_compatibility(self):
        """Test that modules work with GPT-5-Nano configuration."""
        # Create test data
        user_query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            id=uuid4(),
            text="What is Python programming?",
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        state = ReactorState(original_query=user_query)
        
        # Test M0 module (uses LLMModule base)
        m0_module = QAWithHuman()
        
        # Verify module initialization
        assert m0_module.module_code == "M0"
        assert m0_module.model_config_key == "qa.model"
        
        # Test model name retrieval
        model_name = m0_module._get_model_name()
        assert model_name is not None
        assert isinstance(model_name, str)
        
        # Test LLM call (should use placeholder in V1.0 mode)
        response = await m0_module._call_llm("Test prompt for GPT-5-Nano")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Test module execution
        result_state = await m0_module.execute(state)
        assert result_state is not None
        assert isinstance(result_state, ReactorState)
        
        # Should have created a clarified query
        assert result_state.clarified_query is not None