"""Base classes for QueryReactor modules."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time
from uuid import uuid4

from ..models import ReactorState
from ..config.loader import config_loader


class BaseModule(ABC):
    """Base class for all QueryReactor modules."""
    
    def __init__(self, module_code: str):
        """Initialize base module.
        
        Args:
            module_code: Module identifier (e.g., 'M0', 'M1', etc.)
        """
        self.module_code = module_code
        self.logger = logging.getLogger(f"queryreactor.{module_code.lower()}")
        
        # Ensure configuration is loaded automatically
        self._ensure_config_loaded()
        
    @abstractmethod
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute the module logic.
        
        Args:
            state: Current reactor state
            
        Returns:
            Updated reactor state
        """
        pass
    
    def _log_execution_start(self, state: ReactorState, details: Optional[str] = None) -> None:
        """Log module execution start."""
        request_id = state.request_index or str(state.original_query.id)
        message = f"[{self.module_code}] Starting execution"
        if details:
            message += f": {details}"
        self.logger.info(f"{message} (request_id: {request_id})")
    
    def _log_execution_end(self, state: ReactorState, details: Optional[str] = None) -> None:
        """Log module execution completion."""
        request_id = state.request_index or str(state.original_query.id)
        message = f"[{self.module_code}] Execution completed"
        if details:
            message += f": {details}"
        self.logger.info(f"{message} (request_id: {request_id})")
    
    def _log_error(self, state: ReactorState, error: Exception) -> None:
        """Log module execution error."""
        request_id = state.request_index or str(state.original_query.id)
        self.logger.error(f"[{self.module_code}] Error: {str(error)} (request_id: {request_id})")
    
    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return config_loader.get_config(key, default)
    
    def _get_prompt(self, key: str, default: str = "") -> str:
        """Get prompt template."""
        return config_loader.get_prompt(key, default)
    
    def _update_state_module(self, state: ReactorState) -> None:
        """Update state with current module information."""
        state.set_current_module(self.module_code)
    
    def _ensure_config_loaded(self) -> None:
        """Ensure configuration and prompts are loaded."""
        try:
            # Ensure config is loaded (uses lazy loading)
            config_loader.ensure_loaded()
            
            # Validate critical prompts for this module if it's an LLM module
            if hasattr(self, 'model_config_key'):
                self._validate_module_prompts()
                
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Failed to load configuration: {e}")
            # Continue execution - modules should handle missing config gracefully
    
    def _coerce_ainvoke_result(self, result, fallback_state: "ReactorState") -> "ReactorState":
        """Coerce LangGraph ainvoke result back to ReactorState (LG 1.x returns dicts)."""
        if isinstance(result, ReactorState):
            return result
        if isinstance(result, dict):
            try:
                return ReactorState.model_validate(result)
            except Exception:
                pass
        return fallback_state

    def _validate_module_prompts(self) -> None:
        """Validate that required prompts are loaded for this module."""
        # Define required prompts per module
        required_prompts = {
            "M0": ["m0_clarity_assessment", "m0_followup_question"],
            "M1_LG": ["m1_normalization", "m1_reference_resolution", "m1_decomposition"],
            "M2": ["m2_routing"],
            "M10": ["m10_answer_creation"],
            "M11": ["m11_answer_verification"]
        }
        
        module_prompts = required_prompts.get(self.module_code, [])
        missing_prompts = []
        
        for prompt_key in module_prompts:
            if not config_loader.prompts.get(prompt_key):
                missing_prompts.append(prompt_key)
        
        if missing_prompts:
            self.logger.warning(f"[{self.module_code}] Missing prompts: {missing_prompts}")
        else:
            self.logger.debug(f"[{self.module_code}] All required prompts loaded")


class LLMModule(BaseModule):
    """Base class for modules that use LLM capabilities."""
    
    def __init__(self, module_code: str, model_config_key: str):
        """Initialize LLM module.
        
        Args:
            module_code: Module identifier
            model_config_key: Configuration key for model selection
        """
        super().__init__(module_code)
        self.model_config_key = model_config_key
    
    def _get_model_name(self) -> str:
        """Get the configured model name."""
        from ..config.model_manager import model_manager
        
        # Get task type from module code
        task_type_map = {
            "M0": "qa",
            "M1": "query_preprocessing", 
            "M2": "query_routing",
            "M4": "retrieval_quality",
            "M10": "answer_creation",
            "M11": "answer_checking",
            "M6": "multihop"
        }
        
        task_type = task_type_map.get(self.module_code, "qa")
        return model_manager.get_model_for_task(task_type, self.model_config_key)
    
    async def _call_llm(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Call LLM with prompt and context.
        
        Args:
            prompt: The prompt to send to the LLM
            context: Additional context for the prompt
            
        Returns:
            LLM response text
        """
        model_name = self._get_model_name()
        self.logger.debug(f"[{self.module_code}] Calling {model_name} with prompt length: {len(prompt)}")
        
        # Check if we should use actual LLM or placeholder (V1.0 vs V1.1)
        use_actual_llm = self._get_config("llm.use_actual_calls", False)
        
        if use_actual_llm:
            return await self._call_actual_llm(prompt, context)
        else:
            # V1.0 placeholder implementation
            await self._simulate_processing_time()
            return self._generate_placeholder_response(prompt, context)
    
    async def _call_actual_llm(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Call actual LLM API with optimized parameters for the model and task."""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            from ..config.model_manager import model_manager
            
            model_name = self._get_model_name()
            
            # Get task type for optimization
            task_type_map = {
                "M0": "qa",
                "M1": "query_preprocessing", 
                "M2": "query_routing",
                "M4": "retrieval_quality",
                "M10": "answer_creation",
                "M11": "answer_checking",
                "M6": "multihop"
            }
            task_type = task_type_map.get(self.module_code, "qa")
            
            # Get optimized parameters for this model and task
            api_params = model_manager.optimize_params_for_task(model_name, task_type)
            
            # Extract model name and prepare LangChain parameters
            langchain_params = {
                "model": api_params.pop("model"),
            }
            
            # Map API parameters to LangChain parameters
            param_mapping = {
                "max_output_tokens": "max_tokens",  # LangChain still uses max_tokens
                "max_completion_tokens": "max_tokens",
                "temperature": "temperature",
                "top_p": "top_p",
                "presence_penalty": "presence_penalty",
                "frequency_penalty": "frequency_penalty"
            }
            
            for api_param, langchain_param in param_mapping.items():
                if api_param in api_params:
                    langchain_params[langchain_param] = api_params[api_param]
            
            # Create LLM instance with optimized parameters
            llm = ChatOpenAI(**langchain_params)
            
            # Prepare messages
            messages = []
            
            # Add system message if context provided
            if context and context.get("system_prompt"):
                messages.append(SystemMessage(content=context["system_prompt"]))
            
            # Add the main prompt
            messages.append(HumanMessage(content=prompt))
            
            # Call the LLM
            response = await llm.ainvoke(messages)
            return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] LLM call failed: {str(e)}")
            print(f"🔄 FALLBACK TRIGGERED: {self.module_code} LLM Call - {e}")
            print(f"   → Using placeholder response")
            # Fallback to placeholder response
            return self._generate_placeholder_response(prompt, context)
    
    async def _simulate_processing_time(self) -> None:
        """Simulate LLM processing time for V1.0."""
        import asyncio
        # Simulate 100-500ms processing time
        await asyncio.sleep(0.1 + (hash(self.module_code) % 400) / 1000)
    
    def _generate_placeholder_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate placeholder response for V1.0 implementation."""
        return f"[{self.module_code}] Placeholder response for prompt: {prompt[:50]}..."


class RetrievalModule(BaseModule):
    """Base class for retrieval modules."""
    
    def __init__(self, module_code: str, path_id: str):
        """Initialize retrieval module.
        
        Args:
            module_code: Module identifier
            path_id: Retrieval path identifier (P1, P2, P3)
        """
        super().__init__(module_code)
        self.path_id = path_id
    
    def _create_dummy_evidence(self, workunit_id: str, user_id: str, conversation_id: str, 
                              router_decision_id: str, content: str, source_id: str) -> Dict[str, Any]:
        """Create dummy evidence item for V1.0 implementation."""
        from ..models import EvidenceItem, Provenance, SourceType
        from uuid import UUID
        
        # Convert string UUIDs to UUID objects
        workunit_uuid = UUID(workunit_id) if isinstance(workunit_id, str) else workunit_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        conversation_uuid = UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
        router_decision_uuid = UUID(router_decision_id) if isinstance(router_decision_id, str) else router_decision_id
        
        # Determine source type based on path
        source_type_map = {
            "P1": SourceType.db,
            "P2": SourceType.web,
            "P3": SourceType.api
        }
        
        provenance = Provenance(
            source_type=source_type_map.get(self.path_id, SourceType.db),
            source_id=source_id,
            retrieval_path=self.path_id,
            router_decision_id=router_decision_uuid
        )
        
        evidence = EvidenceItem(
            workunit_id=workunit_uuid,
            user_id=user_uuid,
            conversation_id=conversation_uuid,
            content=content,
            score_raw=0.8,  # Dummy score
            provenance=provenance
        )
        
        return evidence