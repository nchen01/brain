"""Configuration loader for QueryReactor system."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import logging

from .settings import settings

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Central configuration loader for QueryReactor system."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing config files. Defaults to project root.
        """
        self.config_dir = config_dir or Path.cwd()
        self.config: Dict[str, Any] = {}
        self.prompts: Dict[str, str] = {}
        self._config_loaded = False
        self._prompts_loaded = False
        
        # Load environment variables
        load_dotenv(self.config_dir / ".env")
        
        # Setup LangSmith tracing if configured
        self._setup_langsmith_tracing()
        
    def load_all(self) -> None:
        """Load all configuration files."""
        self.load_config()
        self.load_prompts()
    
    def ensure_loaded(self) -> None:
        """Ensure configuration is loaded (lazy loading)."""
        if not self._config_loaded or not self._prompts_loaded:
            self.load_all()
        
    def load_config(self) -> None:
        """Load configuration from config.md file."""
        if self._config_loaded:
            return
            
        config_file = self.config_dir / "config.md"
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            self._config_loaded = True  # Mark as loaded even if file doesn't exist
            return
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse config entries (format: key = value)
            for line in content.split('\n'):
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Convert value to appropriate type
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif self._is_float(value):
                        value = float(value)
                    elif value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]  # Remove quotes
                        
                    self._set_nested_config(key, value)
            
            self._config_loaded = True
            logger.debug(f"Configuration loaded from {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
            self._config_loaded = True  # Mark as loaded to prevent retry loops
                
    def load_prompts(self) -> None:
        """Load prompts from prompts.md file."""
        if self._prompts_loaded:
            return
            
        prompts_file = self.config_dir / "prompts.md"
        if not prompts_file.exists():
            logger.warning(f"Prompts file not found: {prompts_file}")
            self._prompts_loaded = True  # Mark as loaded even if file doesn't exist
            return
            
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse prompts (format: ## prompt_key followed by content)
            current_key = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('## '):
                    if current_key:
                        self.prompts[current_key] = '\n'.join(current_content).strip()
                    current_key = line[3:].strip()
                    current_content = []
                elif current_key:
                    current_content.append(line)
                    
            # Add the last prompt
            if current_key:
                self.prompts[current_key] = '\n'.join(current_content).strip()
            
            self._prompts_loaded = True
            logger.debug(f"Loaded {len(self.prompts)} prompts from {prompts_file}")
            
        except Exception as e:
            logger.error(f"Failed to load prompts from {prompts_file}: {e}")
            self._prompts_loaded = True  # Mark as loaded to prevent retry loops
            
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'ac.model')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Ensure config is loaded before accessing
        self.ensure_loaded()
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def get_prompt(self, key: str, default: str = "") -> str:
        """Get prompt by key.
        
        Args:
            key: Prompt key
            default: Default prompt if key not found
            
        Returns:
            Prompt text or default
        """
        # Ensure prompts are loaded before accessing
        self.ensure_loaded()
        return self.prompts.get(key, default)
        
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        # First try to get from pydantic settings
        key_lower = key.lower()
        if hasattr(settings, key_lower):
            value = getattr(settings, key_lower)
            if value is not None:
                return str(value)
        
        # Fall back to os.getenv
        return os.getenv(key, default)
    
    def _setup_langsmith_tracing(self) -> None:
        """Setup LangSmith tracing if configured."""
        langsmith_enabled = self.get_env("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        
        if langsmith_enabled:
            langsmith_api_key = self.get_env("LANGCHAIN_API_KEY")
            langsmith_project = self.get_env("LANGCHAIN_PROJECT", "queryreactor")
            
            if langsmith_api_key:
                # Set environment variables for LangSmith
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
                os.environ["LANGCHAIN_PROJECT"] = langsmith_project
                
                logger.info(f"LangSmith tracing enabled - Project: {langsmith_project}")
            else:
                logger.warning("LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY not provided")
        else:
            logger.info("LangSmith tracing disabled")
        
    def _set_nested_config(self, key: str, value: Any) -> None:
        """Set nested configuration value using dot notation."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def _is_float(self, value: str) -> bool:
        """Check if string represents a float."""
        try:
            float(value)
            return True
        except ValueError:
            return False


# Global configuration instance
config_loader = ConfigLoader()