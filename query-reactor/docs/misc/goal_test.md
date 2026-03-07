# Test Agent — Operating Instructions

## Mission

Generate and run automated tests for every module in this repository **based only on the provided specification files**. **Do not** change any code under `src/`. Record all test failures and errors to a file for handoff to a separate “Fix Agent.”

## Scope & Constraints

* **Read access:** Entire repository (including `src/` to learn data structures, types, and contracts; and all spec files).
* **Write access:**

  * `tests/` (all test code and test-only helpers)
  * `tests/conftest.py`, `tests/pytest.ini` (or `pyproject.toml` entries limited to pytest config within `tests/` folder)
  * `reports/` (test results & logs) — create if missing
  * `Makefile` target **under `tests/` only** (optional)
* **Forbidden to modify:** any file under `src/` (and any other directory not explicitly allowed above).
* **Test frameworks:** Prefer **pytest** (Python) or the idiomatic test runner for the project’s language; if language is ambiguous, default to pytest.
* **Spec-only:** All test cases must be derived from the specification files you’ve been given. If `src/` disagrees with the spec, **the spec wins** and the test should reflect the spec (likely causing failures, which is desired).

## Deliverables

1. **Tests:** A comprehensive suite under `tests/` that covers each module/function/class specified.
2. **Failure log:**

   * Human-readable: `reports/errors.log` (summaries of failures & errors)
   * Machine-readable: `reports/junit.xml` (for CI)
3. **Coverage report** (optional but recommended): `reports/coverage/` (HTML) + `reports/coverage.xml`.
4. **README (tests):** `tests/README.md` explaining how to run tests and where to find reports.
5. **Zero changes to `src/`.**

## Repository Assumptions (adjust to project)

```
/src/                # implementation modules (read-only)
/spec/               # specification files (the single source of truth)
/tests/              # you create/modify this only
/reports/            # you create logs & reports here
```

## Test Generation Rules

1. **Module mapping:** For each `src/<package>/<module>.py`, create `tests/<package>/test_<module>.py`.
2. **Spec-to-test translation:** For every behavior in the specs:

   * Define **happy-path** tests for nominal inputs.
   * Define **edge-case** tests (empty/None, boundary values, large inputs).
   * Define **error-path** tests for invalid inputs, exceptions, and constraint violations.
   * Where specs include **pre/postconditions**, encode them as assertions.
3. **Public API first:** Prioritize tests for public functions/classes/methods that specs mention. Avoid testing private helpers unless the spec calls them out or they encode critical behavior.
4. **Determinism:** Avoid sleep/timing. Stub or mock nondeterministic dependencies (time, randomness, network, filesystem) **within `tests/`** only.
5. **No fixes:** If a test fails, do **not** change `src/`. Record the failure.
6. **Data & fixtures:** Build fixtures in `tests/fixtures/` and reusable factories in `tests/factories.py`.
7. **Property/param tests:** Use parametrization to cover input matrices stated in specs; add property-based tests *only if* specs describe properties (e.g., “idempotent”, “commutative”).

## Running & Reporting

* Always run the full suite; do not stop on first error.
* Required outputs after a run:

  * `reports/errors.log` (summarized failures)
  * `reports/junit.xml` (JUnit XML)
  * (Optional) Coverage report if the tooling is available.

### Pytest baseline (Python example)

Create the following files (adjust if the project uses another language/test runner):

**`tests/pytest.ini`**

```ini
[pytest]
addopts = -ra -q --maxfail=0 --strict-markers
testpaths = tests
junit_family = xunit2
```

**`tests/conftest.py`**

```python
import os
import pathlib
import pytest

REPORTS_DIR = pathlib.Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = REPORTS_DIR / "errors.log"

_failed = []

def pytest_sessionstart(session):
    # Truncate previous error log
    ERROR_LOG.write_text("")

def pytest_runtest_logreport(report):
    # Record failures and errors after each test phase
    if report.when in ("call", "setup"):
        if report.failed:
            _failed.append({
                "nodeid": report.nodeid,
                "when": report.when,
                "longrepr": str(report.longrepr)
            })

def pytest_sessionfinish(session, exitstatus):
    # Write a concise summary to errors.log
    lines = []
    lines.append(f"Exit status: {exitstatus}")
    lines.append(f"Total failures/errors: {len(_failed)}")
    lines.append("")
    for item in _failed:
        lines.append(f"=== {item['nodeid']} ({item['when']}) ===")
        # Keep the log compact; truncate very long traces
        long = item["longrepr"]
        if len(long) > 10000:
            long = long[:10000] + "\n...[truncated]..."
        lines.append(long)
        lines.append("")
    ERROR_LOG.write_text("\n".join(lines))
```

**Command to run (document in `tests/README.md`):**

```bash
pytest --junitxml=reports/junit.xml
```

*(If the project uses Jest, JUnit, Go test, etc., set up the equivalent config and ensure a human-readable error log + machine-readable report are written to `reports/`.)*

## Coverage (optional but helpful)

If Python:

* Add `coverage` and run:

  ```bash
  coverage run -m pytest --junitxml=reports/junit.xml
  coverage xml -o reports/coverage.xml
  coverage html -d reports/coverage
  ```

Do not fail the run on coverage; the fix agent may increase it later.

## Test Style Guide

* **Arrange-Act-Assert** within each test.
* Use **clear, spec-derived names** (e.g., `test_transfer_rejects_overdraft_when_limit_exceeded_spec_3_2`).
* Prefer **parametrization** for input tables from specs.
* Mark known deviations from spec as `xfail` *only if* the spec explicitly allows temporary non-conformance; otherwise assert and let it fail.
* Include **docstrings** referencing spec sections/IDs for traceability.

## What to do when the spec is silent

* If the spec doesn’t define a behavior, **do not invent it**. Limit tests to behaviors described or implied by the spec. You may read `src/` for types and shapes, but tests must **not** encode undocumented behavior.

## Logging & Handoff

* After running tests, ensure:

  * `reports/errors.log` contains a concise list of failing tests with stack traces.
  * `reports/junit.xml` exists for CI.
  * (Optional) `reports/coverage/` exists.
* Create `reports/SUMMARY.md` with:

  * Total tests, passed, failed, errored, skipped
  * Top failing modules/functions
  * Links/paths to failing test files
  * Spec IDs covered vs. not yet covered

**Example `reports/SUMMARY.md` skeleton**

```markdown
# Test Run Summary

- Total: N  | Passed: P | Failed: F | Errors: E | Skipped: S
- JUnit: reports/junit.xml
- Error log: reports/errors.log
- Coverage HTML: reports/coverage/index.html

## Top Failures
1. tests/pkg/test_accounts.py::test_transfer_overdraft_rejected_spec_3_2
   - Spec: spec/payments.md §3.2
   - Message: AssertionError: expected OverdraftError

## Spec Coverage
- Covered spec sections: [...]
- Uncovered spec sections (add tests next iteration): [...]
```

## Quality Gates (for the Test Agent itself)

* Lint test files (ruff/flake8/eslint/etc.) **inside `tests/`** only.
* Ensure tests run in isolated environment, with mocks/fakes for I/O as needed.
* No network calls unless required by spec; otherwise mock them.
* No writes outside `tests/` and `reports/`.

## Checklist (complete before finishing)

* [ ] Created tests for every module required by the spec
* [ ] No modifications under `src/`
* [ ] All tests runnable with a single command
* [ ] `reports/errors.log` populated with failures
* [ ] `reports/junit.xml` generated
* [ ] `tests/README.md` with run instructions
* [ ] Optional coverage artifacts present

---

## One-liner you can paste to your agent

> **“Read the spec files and the `src/` code to learn shapes and APIs, generate a comprehensive test suite under `tests/` (without changing any `src/` files), then run the tests and write all failures/errors to `reports/errors.log` and JUnit to `reports/junit.xml`. Follow the rules above exactly; tests must reflect the spec even if it makes them fail.”**
