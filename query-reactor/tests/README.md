# QueryReactor Test Suite

This directory contains comprehensive tests for the QueryReactor system based on the specification requirements.

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── pytest.ini              # Pytest configuration
├── models/                  # Tests for data models
│   ├── test_core.py        # Core data model tests
│   └── test_state.py       # ReactorState model tests
├── config/                  # Tests for configuration system
│   └── test_loader.py      # Configuration loader tests
└── modules/                 # Tests for processing modules
    ├── test_base.py        # Base module class tests
    ├── test_m0_qa_human.py # M0 - QA with Human tests
    ├── test_m1_query_preprocessor.py # M1 - Query Preprocessor tests
    ├── test_m2_query_router.py # M2 - Query Router tests
    └── test_m4_retrieval_quality_check.py # M4 - Quality Check tests
```

## Running Tests

### Run All Tests
```bash
pytest --junitxml=reports/junit.xml
```

### Run Specific Test Categories
```bash
# Test data models only
pytest tests/models/

# Test configuration system only
pytest tests/config/

# Test specific module
pytest tests/modules/test_m0_qa_human.py
```

### Run with Coverage
```bash
coverage run -m pytest --junitxml=reports/junit.xml
coverage xml -o reports/coverage.xml
coverage html -d reports/coverage
```

## Test Reports

After running tests, reports are generated in the `reports/` directory:

- `reports/errors.log` - Human-readable failure summary
- `reports/junit.xml` - Machine-readable test results for CI
- `reports/coverage/` - HTML coverage report (if coverage enabled)
- `reports/coverage.xml` - XML coverage report (if coverage enabled)

## Test Categories

### Specification-Based Tests

All tests are derived from the QueryReactor specification files:
- `.kiro/specs/query-reactor/requirements.md`
- `.kiro/specs/query-reactor/design.md`
- `.kiro/specs/query-reactor/tasks.md`

### Test Types

1. **Unit Tests**: Test individual modules and functions in isolation
2. **Integration Tests**: Test module interactions and data flow
3. **Validation Tests**: Test data model validation and constraints
4. **Error Handling Tests**: Test graceful error handling and fallbacks

### Requirement Coverage

Tests are mapped to specific requirements:

- **Requirement 1**: Multi-User Query Processing
- **Requirement 2**: Intelligent Query Processing and Decomposition  
- **Requirement 3**: Multi-Path Evidence Retrieval
- **Requirement 4**: Evidence Aggregation and Ranking
- **Requirement 5**: Smart Answer Generation with Verification
- **Requirement 6**: Adaptive Control Flow and Loop Management
- **Requirement 7**: Configuration and Credential Management
- **Requirement 8**: Comprehensive Logging and Observability

## Test Fixtures

Common test fixtures are provided in `conftest.py`:

- `sample_user_query`: Sample UserQuery for testing
- `sample_workunit`: Sample WorkUnit for testing
- `sample_evidence_item`: Sample EvidenceItem for testing
- `sample_reactor_state`: Sample ReactorState for testing

## Mocking Strategy

Tests use mocking to isolate units under test:
- Configuration values are mocked for consistent test behavior
- External dependencies (LLM calls, databases) are mocked
- Time-dependent operations use fixed timestamps
- Network calls are stubbed with predictable responses

## Test Naming Convention

Test methods follow the pattern:
```
test_<functionality>_spec_<requirement_id>
```

Example: `test_user_query_creation_with_required_fields_spec_1_2`

This links each test to specific specification requirements for traceability.

## Async Testing

Many modules use async operations. Tests use `pytest-asyncio` for async test support:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Error Reporting

Test failures are captured in multiple formats:
- Console output during test execution
- `reports/errors.log` for human review
- `reports/junit.xml` for CI integration

The error log includes:
- Test name and location
- Failure reason and stack trace
- Truncated output for very long traces