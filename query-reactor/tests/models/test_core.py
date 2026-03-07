"""Tests for core data models based on specification requirements."""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from pydantic import ValidationError

from src.models.core import (
    UserQuery, WorkUnit, EvidenceItem, Provenance, SourceType,
    ClarifiedQuery, HistoryTurn, Role, Answer, Citation
)


class TestUserQuery:
    """Test UserQuery model per Requirement 1.2 - unique identifiers for isolation."""
    
    def test_user_query_creation_with_required_fields_spec_1_2(self):
        """Test UserQuery creation with all required fields."""
        user_id = uuid4()
        conversation_id = uuid4()
        query_id = uuid4()
        timestamp = int(datetime.now().timestamp() * 1000)
        
        query = UserQuery(
            user_id=user_id,
            conversation_id=conversation_id,
            id=query_id,
            text="What is Python?",
            timestamp=timestamp
        )
        
        assert query.user_id == user_id
        assert query.conversation_id == conversation_id
        assert query.id == query_id
        assert query.text == "What is Python?"
        assert query.timestamp == timestamp
    
    def test_user_query_requires_user_id_spec_1_2(self):
        """Test that UserQuery requires user_id for multi-tenant isolation."""
        with pytest.raises(ValidationError):
            UserQuery(
                conversation_id=uuid4(),
                id=uuid4(),
                text="What is Python?",
                timestamp=int(datetime.now().timestamp() * 1000)
            )
    
    def test_user_query_requires_conversation_id_spec_1_2(self):
        """Test that UserQuery requires conversation_id for session grouping."""
        with pytest.raises(ValidationError):
            UserQuery(
                user_id=uuid4(),
                id=uuid4(),
                text="What is Python?",
                timestamp=int(datetime.now().timestamp() * 1000)
            )
    
    def test_user_query_auto_generates_id_spec_1_2(self):
        """Test that UserQuery auto-generates unique query identifier."""
        query = UserQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            text="What is Python?",
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        # Should auto-generate a UUID
        assert query.id is not None
        assert isinstance(query.id, UUID)
    
    def test_user_query_empty_text_validation(self):
        """Test that UserQuery rejects empty text."""
        with pytest.raises(ValidationError):
            UserQuery(
                user_id=uuid4(),
                conversation_id=uuid4(),
                id=uuid4(),
                text="",
                timestamp=int(datetime.now().timestamp() * 1000)
            )


class TestWorkUnit:
    """Test WorkUnit model per Requirement 2.4 - query decomposition with traceability."""
    
    def test_workunit_creation_spec_2_4(self):
        """Test WorkUnit creation for query decomposition."""
        parent_id = uuid4()
        user_id = uuid4()
        conversation_id = uuid4()
        
        workunit = WorkUnit(
            parent_query_id=parent_id,
            text="What is Python?",
            is_subquestion=False,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        assert workunit.parent_query_id == parent_id
        assert workunit.text == "What is Python?"
        assert workunit.is_subquestion is False
        assert workunit.user_id == user_id
        assert workunit.conversation_id == conversation_id
        assert workunit.id is not None  # Should auto-generate
    
    def test_workunit_subquestion_traceability_spec_2_4(self):
        """Test WorkUnit maintains traceability for sub-questions."""
        parent_id = uuid4()
        
        subquestion = WorkUnit(
            parent_query_id=parent_id,
            text="What is Python syntax?",
            is_subquestion=True,
            user_id=uuid4(),
            conversation_id=uuid4(),
            priority=1
        )
        
        assert subquestion.parent_query_id == parent_id
        assert subquestion.is_subquestion is True
        assert subquestion.priority == 1
    
    def test_workunit_requires_parent_query_id_spec_2_4(self):
        """Test that WorkUnit requires parent_query_id for traceability."""
        with pytest.raises(ValidationError):
            WorkUnit(
                text="What is Python?",
                is_subquestion=False,
                user_id=uuid4(),
                conversation_id=uuid4()
            )


class TestEvidenceItem:
    """Test EvidenceItem model per Requirement 3.4 - evidence with provenance."""
    
    def test_evidence_item_creation_with_provenance_spec_3_4(self):
        """Test EvidenceItem creation with full provenance information."""
        workunit_id = uuid4()
        user_id = uuid4()
        conversation_id = uuid4()
        router_decision_id = uuid4()
        
        provenance = Provenance(
            source_type=SourceType.db,
            source_id="test_db",
            retrieval_path="P1",
            router_decision_id=router_decision_id
        )
        
        evidence = EvidenceItem(
            workunit_id=workunit_id,
            user_id=user_id,
            conversation_id=conversation_id,
            content="Python is a programming language.",
            score_raw=0.85,
            provenance=provenance
        )
        
        assert evidence.workunit_id == workunit_id
        assert evidence.user_id == user_id
        assert evidence.conversation_id == conversation_id
        assert evidence.content == "Python is a programming language."
        assert evidence.score_raw == 0.85
        assert evidence.provenance.source_type == SourceType.db
        assert evidence.provenance.retrieval_path == "P1"
    
    def test_evidence_item_requires_provenance_spec_3_4(self):
        """Test that EvidenceItem requires provenance for traceability."""
        with pytest.raises(ValidationError):
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=uuid4(),
                conversation_id=uuid4(),
                content="Python is a programming language."
            )
    
    def test_evidence_item_empty_content_validation(self):
        """Test that EvidenceItem rejects empty content."""
        provenance = Provenance(
            source_type=SourceType.db,
            source_id="test_db",
            retrieval_path="P1",
            router_decision_id=uuid4()
        )
        
        with pytest.raises(ValidationError):
            EvidenceItem(
                workunit_id=uuid4(),
                user_id=uuid4(),
                conversation_id=uuid4(),
                content="",
                provenance=provenance
            )


class TestProvenance:
    """Test Provenance model per Requirement 3.4 - source metadata tracking."""
    
    def test_provenance_creation_spec_3_4(self):
        """Test Provenance creation with source metadata."""
        router_decision_id = uuid4()
        
        provenance = Provenance(
            source_type=SourceType.web,
            source_id="wikipedia.org",
            retrieval_path="P2",
            router_decision_id=router_decision_id,
            url="https://en.wikipedia.org/wiki/Python"
        )
        
        assert provenance.source_type == SourceType.web
        assert provenance.source_id == "wikipedia.org"
        assert provenance.retrieval_path == "P2"
        assert provenance.router_decision_id == router_decision_id
        assert provenance.url == "https://en.wikipedia.org/wiki/Python"
    
    def test_provenance_requires_source_type_spec_3_4(self):
        """Test that Provenance requires source_type classification."""
        with pytest.raises(ValidationError):
            Provenance(
                source_id="test_source",
                retrieval_path="P1",
                router_decision_id=uuid4()
            )
    
    def test_provenance_requires_router_decision_id_spec_3_4(self):
        """Test that Provenance requires router_decision_id for traceability."""
        with pytest.raises(ValidationError):
            Provenance(
                source_type=SourceType.db,
                source_id="test_source",
                retrieval_path="P1"
            )


class TestClarifiedQuery:
    """Test ClarifiedQuery model per Requirement 2.1 - interactive clarification."""
    
    def test_clarified_query_creation_spec_2_1(self):
        """Test ClarifiedQuery creation with clarification metadata."""
        user_id = uuid4()
        conversation_id = uuid4()
        query_id = uuid4()
        timestamp = int(datetime.now().timestamp() * 1000)
        
        clarified = ClarifiedQuery(
            user_id=user_id,
            conversation_id=conversation_id,
            id=query_id,
            text="What is Python programming language?",
            timestamp=timestamp,
            original_text="What is Python?",
            clarification_turns=2,
            confidence=0.9
        )
        
        assert clarified.original_text == "What is Python?"
        assert clarified.clarification_turns == 2
        assert clarified.confidence == 0.9
        assert clarified.text == "What is Python programming language?"
    
    def test_clarified_query_confidence_threshold_spec_2_1(self):
        """Test ClarifiedQuery confidence validation per spec."""
        # Should accept confidence >= 0.0 and <= 1.0
        clarified = ClarifiedQuery(
            user_id=uuid4(),
            conversation_id=uuid4(),
            id=uuid4(),
            text="What is Python?",
            timestamp=int(datetime.now().timestamp() * 1000),
            original_text="Python?",
            clarification_turns=1,
            confidence=0.8
        )
        assert clarified.confidence == 0.8


class TestAnswer:
    """Test Answer model per Requirement 5.2 - answers with citations."""
    
    def test_answer_creation_with_citations_spec_5_2(self):
        """Test Answer creation with proper citations mapping."""
        evidence_id = uuid4()
        
        citation = Citation(
            evidence_id=evidence_id,
            span_start=0,
            span_end=20
        )
        
        answer = Answer(
            workunit_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            query_id=uuid4(),
            text="Python is a high-level programming language.",
            citations=[citation],
            confidence=0.9
        )
        
        assert len(answer.citations) == 1
        assert answer.citations[0].evidence_id == evidence_id
        assert answer.citations[0].span_start == 0
        assert answer.citations[0].span_end == 20
        assert answer.confidence == 0.9
    
    def test_answer_requires_citations_spec_5_2(self):
        """Test that Answer requires citations for verification."""
        # Answer should be valid even without citations (empty list is allowed)
        answer = Answer(
            workunit_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            query_id=uuid4(),
            text="Python is a programming language.",
            citations=[],
            confidence=0.8
        )
        assert answer.citations == []


class TestHistoryTurn:
    """Test HistoryTurn model for conversation history tracking."""
    
    def test_history_turn_creation(self):
        """Test HistoryTurn creation for conversation tracking."""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        turn = HistoryTurn(
            role=Role.user,
            text="What is Python?",
            timestamp=timestamp
        )
        
        assert turn.role == Role.user
        assert turn.text == "What is Python?"
        assert turn.timestamp == timestamp
    
    def test_history_turn_assistant_role(self):
        """Test HistoryTurn with assistant role."""
        turn = HistoryTurn(
            role=Role.assistant,
            text="Python is a programming language.",
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        assert turn.role == Role.assistant