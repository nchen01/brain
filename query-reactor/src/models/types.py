"""Core type definitions for QueryReactor system."""

from __future__ import annotations
from typing import Annotated
from enum import Enum
from pydantic import Field

# Common type aliases
EpochMs = Annotated[int, Field(ge=0, description="UNIX epoch time in milliseconds")]
Score = Annotated[float, Field(description="Generic numerical score")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")]


class Role(str, Enum):
    """Conversation role enumeration."""
    user = "user"
    assistant = "assistant"
    system = "system"


class SourceType(str, Enum):
    """Evidence source type enumeration."""
    db = "db"
    web = "web"
    api = "api"


class RQCStatus(str, Enum):
    """Retrieval Quality Check status enumeration."""
    ok = "ok"
    no_fit = "no_fit"


class RQCReason(str, Enum):
    """Reasons for RQC no_fit status."""
    not_found = "not_found"
    low_overlap = "low_overlap"
    low_quality = "low_quality"


class SMRDecision(str, Enum):
    """SmartRetrieval Controller decision enumeration."""
    answer_ready = "answer_ready"
    needs_better_decomposition = "needs_better_decomposition"
    insufficient_evidence = "insufficient_evidence"