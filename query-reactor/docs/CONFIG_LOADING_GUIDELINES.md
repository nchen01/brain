# Configuration Loading Guidelines

## Problem Statement

The QueryReactor system relies on configuration files (`config.md`) and prompts (`prompts.md`) being loaded before modules can function correctly. Previously, this caused recurring issues where:

1. Modules would use default/fallback prompts instead of the actual prompts from `prompts.md`
2. Tests would pass with mocked data but fail in real usage
3. The `<history>` sections and other prompt features wouldn't work as expected

## Solution: Automatic Configuration Loading

### How It Works

1. **Base Module Auto-Loading**: All modules inherit from `BaseModule`, which automatically calls `_ensure_config_loaded()` during initialization.

2. **Lazy Loading**: The `ConfigLoader` uses lazy loading - it only loads files when first accessed, and caches the results.

3. **Resilient Loading**: If config files are missing, the system logs warnings but continues to function with defaults.

4. **Validation**: Modules validate that their required prompts are loaded and log warnings for missing ones.

### For Developers

#### ✅ **DO**

- **Inherit from BaseModule/LLMModule**: All new modules should inherit from these base classes to get automatic config loading.

```python
class MyNewModule(LLMModule):
    def __init__(self):
        super().__init__("M99", "my.model.key")  # Config loading happens automatically
```

- **Use `self._get_prompt()` and `self._get_config()`**: These methods ensure config is loaded before accessing.

```python
prompt = self._get_prompt("my_prompt_key", "fallback prompt")
config_value = self._get_config("my.config.key", default_value)
```

- **Test with real config**: Write tests that verify actual prompts are loaded, not just mocked responses.

#### ❌ **DON'T**

- **Manual config loading**: Don't call `config_loader.load_all()` manually in module constructors - it's handled automatically.

```python
# DON'T DO THIS
def __init__(self):
    super().__init__("M99", "my.model.key")
    config_loader.load_all()  # ❌ Unnecessary and can cause issues
```

- **Direct config_loader access**: Avoid accessing `config_loader` directly in modules - use the base class methods.

```python
# DON'T DO THIS
from ..config.loader import config_loader
prompt = config_loader.get_prompt("my_prompt")  # ❌ Bypasses validation

# DO THIS INSTEAD
prompt = self._get_prompt("my_prompt", "fallback")  # ✅ Uses base class method
```

### Testing Guidelines

#### Integration Tests
```python
def test_module_uses_real_prompts(self):
    """Test that module uses actual prompts from prompts.md"""
    module = MyModule()
    
    # Verify specific prompt content is used
    result = module.some_method()
    assert "expected prompt content" in str(result)
```

#### Config Loading Tests
```python
def test_config_loading_resilience(self):
    """Test module handles missing config gracefully"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with missing config files
        loader = ConfigLoader(Path(temp_dir))
        # Should not raise exceptions
        loader.ensure_loaded()
```

### Debugging Config Issues

If you suspect config loading issues:

1. **Check logs**: Look for config loading debug/warning messages
2. **Verify prompt content**: Add logging to check actual prompt content being used
3. **Test config loading**: Run the config loading tests to verify the system works

```python
# Debug prompt loading
logger.info(f"Using prompt: {self._get_prompt('my_prompt')[:100]}...")
```

### File Structure

```
project/
├── config.md              # Configuration values
├── prompts.md             # LLM prompts (## section_name format)
├── src/
│   ├── config/
│   │   └── loader.py      # ConfigLoader with lazy loading
│   └── modules/
│       ├── base.py        # BaseModule with auto config loading
│       └── m1_*.py        # Modules inherit from BaseModule
└── tests/
    └── config/
        └── test_config_loading.py  # Config loading tests
```

### Migration Checklist

When working on existing modules:

- [ ] Remove manual `config_loader.load_all()` calls
- [ ] Ensure module inherits from `BaseModule` or `LLMModule`
- [ ] Use `self._get_prompt()` instead of direct config_loader access
- [ ] Add tests that verify real prompts are loaded
- [ ] Check logs for config loading warnings

This system ensures that configuration loading "just works" without developers having to remember to call `load_all()` manually.