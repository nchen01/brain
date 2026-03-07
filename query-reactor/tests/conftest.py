import os
import pathlib
import pytest
from uuid import uuid4
from datetime import datetime

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
    ERROR_LOG.write_text("\n".join(lines), encoding='utf-8')

# Test fixtures for common data structures
@pytest.fixture
def sample_user_query():
    """Sample UserQuery for testing."""
    from src.models.core import UserQuery
    return UserQuery(
        user_id=uuid4(),
        conversation_id=uuid4(),
        id=uuid4(),
        text="What is Python programming?",
        timestamp=int(datetime.now().timestamp() * 1000)
    )

@pytest.fixture
def sample_workunit():
    """Sample WorkUnit for testing."""
    from src.models.core import WorkUnit
    return WorkUnit(
        parent_query_id=uuid4(),
        text="What is Python programming?",
        is_subquestion=False,
        user_id=uuid4(),
        conversation_id=uuid4()
    )

@pytest.fixture
def sample_evidence_item():
    """Sample EvidenceItem for testing."""
    from src.models.core import EvidenceItem, Provenance, SourceType
    
    provenance = Provenance(
        source_type=SourceType.db,
        source_id="test_source",
        retrieval_path="P1",
        router_decision_id=uuid4()
    )
    
    return EvidenceItem(
        workunit_id=uuid4(),
        user_id=uuid4(),
        conversation_id=uuid4(),
        content="Python is a high-level programming language.",
        score_raw=0.8,
        provenance=provenance
    )

@pytest.fixture
def sample_reactor_state(sample_user_query):
    """Sample ReactorState for testing."""
    from src.models.state import ReactorState
    return ReactorState(original_query=sample_user_query)