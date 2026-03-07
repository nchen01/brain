"""Tests for M5 Internet Retrieval module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
import time

from src.models.state import ReactorState
from src.models.core import UserQuery, WorkUnit
from src.modules.m5_internet_retrieval_langgraph import M5InternetRetrievalLangGraph


class TestM5InternetRetrieval:
    """Test suite for M5 Internet Retrieval module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.module = M5InternetRetrievalLangGraph()
        
        # Create test data
        self.user_id = uuid4()
        self.conversation_id = uuid4()
        self.query_id = uuid4()
        
        self.user_query = UserQuery(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            id=self.query_id,
            text="What are the latest developments in AI?",
            timestamp=int(time.time() * 1000),
            locale="en-US"
        )
        
        self.workunit = WorkUnit(
            parent_query_id=self.query_id,
            text="Latest AI developments 2024",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=True,
            priority=0
        )
        
        # Create test state
        self.state = ReactorState(original_query=self.user_query)
        self.state.add_workunit(self.workunit)
    
    def test_module_initialization(self):
        """Test module initialization and configuration."""
        assert self.module.module_code == "M5"
        assert self.module.path_id == "P2"
        assert self.module.max_results == 10
        assert self.module.content_extraction_enabled == True
        assert self.module.rate_limit_delay == 1.0
        assert self.module.timeout_seconds == 30
    
    @pytest.mark.asyncio
    async def test_execute_with_placeholder_data(self):
        """Test execute method with placeholder search results."""
        # Execute the module
        result_state = await self.module.execute(self.state)
        
        # Verify results
        assert isinstance(result_state, ReactorState)
        assert len(result_state.evidences) > 0
        
        # Check evidence properties
        for evidence in result_state.evidences:
            assert evidence.workunit_id == self.workunit.id
            assert evidence.user_id == self.user_id
            assert evidence.conversation_id == self.conversation_id
            assert evidence.content is not None
            assert evidence.provenance.retrieval_path == "P2"
            assert evidence.provenance.source_type.value == "web"
    
    def test_create_placeholder_search_results(self):
        """Test placeholder search results creation."""
        query = "test query"
        results = self.module._create_placeholder_search_results(query)
        
        assert len(results) == 3
        for result in results:
            assert "title" in result
            assert "snippet" in result
            assert "link" in result
            assert query in result["title"]
            assert query in result["snippet"]
    
    @pytest.mark.asyncio
    async def test_create_evidence_items(self):
        """Test evidence item creation from search results."""
        search_results = [
            {
                'title': 'Test Result 1',
                'snippet': 'This is a test snippet about AI developments.',
                'link': 'https://example.com/test1',
                'displayLink': 'example.com',
                'formattedUrl': 'https://example.com/test1'
            },
            {
                'title': 'Test Result 2',
                'snippet': 'Another test snippet with more AI information.',
                'link': 'https://example.org/test2',
                'displayLink': 'example.org',
                'formattedUrl': 'https://example.org/test2'
            }
        ]
        
        evidence_items = await self.module._create_evidence_items(
            search_results, self.workunit, self.user_id, self.conversation_id
        )
        
        assert len(evidence_items) == 2
        
        # Check first evidence item
        evidence1 = evidence_items[0]
        assert evidence1.workunit_id == self.workunit.id
        assert evidence1.title == "Test Result 1"
        assert evidence1.content == "This is a test snippet about AI developments."
        assert evidence1.provenance.url == "https://example.com/test1"
        assert evidence1.provenance.source_type.value == "web"
        assert evidence1.score_raw == 0.8
        
        # Check second evidence item
        evidence2 = evidence_items[1]
        assert abs(evidence2.score_raw - 0.7) < 0.001  # Decreasing score (with floating point tolerance)
    
    @pytest.mark.asyncio
    async def test_process_workunit_error_handling(self):
        """Test error handling in workunit processing."""
        # Create a workunit with problematic text
        bad_workunit = WorkUnit(
            parent_query_id=self.query_id,
            text="",  # Empty text
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=True,
            priority=0
        )
        
        # Should not raise exception
        await self.module._process_workunit(self.state, bad_workunit)
        
        # State should remain valid
        assert isinstance(self.state, ReactorState)
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_search_google_api_success(self, mock_get):
        """Test successful Google Search API call."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'items': [
                {
                    'title': 'API Test Result',
                    'snippet': 'Test snippet from API',
                    'link': 'https://api-test.com',
                    'displayLink': 'api-test.com'
                }
            ]
        })
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Set API credentials for this test
        self.module.api_key = "test_api_key"
        self.module.search_engine_id = "test_engine_id"
        
        results = await self.module._search_google("test query")
        
        assert len(results) == 1
        assert results[0]['title'] == 'API Test Result'
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_search_google_api_rate_limit(self, mock_get):
        """Test Google Search API rate limiting handling."""
        # Mock rate limit response followed by success
        mock_rate_limit_response = AsyncMock()
        mock_rate_limit_response.status = 429
        
        mock_success_response = AsyncMock()
        mock_success_response.status = 200
        mock_success_response.json = AsyncMock(return_value={'items': []})
        
        mock_get.return_value.__aenter__.side_effect = [
            mock_rate_limit_response,
            mock_success_response
        ]
        
        # Set API credentials for this test
        self.module.api_key = "test_api_key"
        self.module.search_engine_id = "test_engine_id"
        self.module.rate_limit_delay = 0.1  # Speed up test
        
        results = await self.module._search_google("test query")
        
        assert results == []  # Empty results but no exception
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_search_google_api_error(self, mock_get):
        """Test Google Search API error handling."""
        # Mock API error
        mock_response = AsyncMock()
        mock_response.status = 500
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Set API credentials for this test
        self.module.api_key = "test_api_key"
        self.module.search_engine_id = "test_engine_id"
        
        results = await self.module._search_google("test query")
        
        assert results == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_extract_content_success(self, mock_get):
        """Test successful content extraction."""
        # Mock successful content extraction
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="""
            <html>
                <head><title>Test Page</title></head>
                <body>
                    <h1>Main Content</h1>
                    <p>This is the main content of the page.</p>
                    <script>console.log('script');</script>
                    <style>body { color: red; }</style>
                </body>
            </html>
        """)
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        content = await self.module._extract_content("https://example.com/test")
        
        assert content is not None
        assert "Main Content" in content
        assert "This is the main content" in content
        assert "console.log" not in content  # Script should be removed
        assert "color: red" not in content  # Style should be removed
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_extract_content_failure(self, mock_get):
        """Test content extraction failure handling."""
        # Mock failed content extraction
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        content = await self.module._extract_content("https://example.com/notfound")
        
        assert content is None
    
    @pytest.mark.asyncio
    async def test_execute_multiple_workunits(self):
        """Test execution with multiple WorkUnits."""
        # Add another workunit
        workunit2 = WorkUnit(
            parent_query_id=self.query_id,
            text="AI machine learning trends",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            timestamp=int(time.time() * 1000),
            is_subquestion=True,
            priority=1
        )
        self.state.add_workunit(workunit2)
        
        # Execute the module
        result_state = await self.module.execute(self.state)
        
        # Should have evidence for both workunits
        workunit1_evidence = [e for e in result_state.evidences if e.workunit_id == self.workunit.id]
        workunit2_evidence = [e for e in result_state.evidences if e.workunit_id == workunit2.id]
        
        assert len(workunit1_evidence) > 0
        assert len(workunit2_evidence) > 0
    
    def test_module_configuration_loading(self):
        """Test that module loads configuration correctly."""
        # Test default values when config is not available
        module = M5InternetRetrievalLangGraph()
        
        assert module.max_results >= 1
        assert module.timeout_seconds > 0
        assert module.rate_limit_delay >= 0
        assert isinstance(module.content_extraction_enabled, bool)
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_state(self):
        """Test execution with empty state (no workunits)."""
        empty_state = ReactorState(original_query=self.user_query)
        
        result_state = await self.module.execute(empty_state)
        
        assert isinstance(result_state, ReactorState)
        assert len(result_state.evidences) == 0