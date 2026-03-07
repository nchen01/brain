"""M5 - Internet Retrieval using Google Search API."""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
import aiohttp
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging

from ..models import ReactorState, EvidenceItem, Provenance, SourceType
from .base import RetrievalModule
from ..config.loader import config_loader

logger = logging.getLogger(__name__)


class M5InternetRetrievalLangGraph(RetrievalModule):
    """M5 - Internet Retrieval module using Google Custom Search API."""
    
    def __init__(self):
        super().__init__("M5", "P2")
        
        # Load configuration for Perplexity API
        self.api_key = config_loader.get_env("PERPLEXITY_API_KEY")
        self.model = self._get_config("m5.model", "sonar")
        self.max_results = self._get_config("m5.max_results", 10)
        self.rate_limit_delay = self._get_config("m5.rate_limit_delay", 1.0)
        self.timeout_seconds = self._get_config("m5.timeout_seconds", 30)
        
        # Validate required configuration
        if not self.api_key:
            self.logger.warning("Perplexity API key not found. M5 will use placeholder responses.")
        elif self.api_key == "your_perplexity_api_key":
            self.logger.warning("Perplexity API key not configured. M5 will use placeholder responses.")
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """Execute internet retrieval for all WorkUnits in the state."""
        self._log_execution_start(state, f"Processing {len(state.workunits)} WorkUnits")
        
        try:
            # Process each WorkUnit
            for workunit in state.workunits:
                await self._process_workunit(state, workunit)
            
            evidence_count = len([e for e in state.evidences if any(
                e.workunit_id == wu.id for wu in state.workunits
            )])
            
            self._log_execution_end(state, f"Retrieved {evidence_count} evidence items")
            return state
            
        except Exception as e:
            self._log_error(state, e)
            print(f"🔄 FALLBACK TRIGGERED: M5 Execute - {e}")
            print(f"   → Returning state with any evidence that was successfully retrieved")
            # Return state with any evidence that was successfully retrieved
            return state
    
    async def _process_workunit(self, state: ReactorState, workunit) -> None:
        """Process a single WorkUnit to retrieve evidence."""
        try:
            self.logger.info(f"[{self.module_code}] Processing WorkUnit: {workunit.text[:50]}...")
            
            # Check if we should use actual API or placeholder
            use_actual_api = self.api_key and self.api_key != "your_perplexity_api_key"
            
            if use_actual_api:
                search_results = await self._search_perplexity(workunit.text)
                # If API call fails, fall back to placeholder
                if not search_results:
                    self.logger.warning(f"[{self.module_code}] Perplexity API call failed, using placeholder results")
                    search_results = self._create_placeholder_search_results(workunit.text)
            else:
                search_results = self._create_placeholder_search_results(workunit.text)
            
            # Create evidence items from search results
            evidence_items = await self._create_evidence_items(
                search_results, workunit, state.original_query.user_id, 
                state.original_query.conversation_id
            )
            
            # Add evidence to state
            for evidence in evidence_items:
                state.add_evidence(evidence)
                
            self.logger.info(f"[{self.module_code}] Created {len(evidence_items)} evidence items for WorkUnit")
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Failed to process WorkUnit {workunit.id}: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M5 WorkUnit Processing - {e}")
            print(f"   → Continuing with next WorkUnit")
    
    async def _search_perplexity(self, query: str) -> List[Dict[str, Any]]:
        """Perform Perplexity API search request."""
        try:
            url = "https://api.perplexity.ai/chat/completions"
            
            # Get prompts from configuration
            system_prompt = self._get_prompt("m5_search_assistant",
                "You are a search assistant. Provide comprehensive search results with sources, titles, and relevant content excerpts."
            )
            
            search_prompt_template = self._get_prompt("m5_search_prompt",
                "Create effective search prompts for comprehensive information retrieval."
            )
            
            # Create search prompt for Perplexity
            search_prompt = f"""Search for information about: {query}

Please provide comprehensive search results with multiple sources. For each source, include:
1. Title of the content
2. URL/source link
3. Relevant excerpt or summary
4. Key information related to the query

Focus on recent, authoritative sources and provide diverse perspectives."""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": search_prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.2,
                "return_citations": True,
                "return_images": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_perplexity_response(data, query)
                    elif response.status == 429:
                        # Rate limited
                        self.logger.warning(f"[{self.module_code}] Perplexity rate limited, waiting {self.rate_limit_delay}s")
                        await asyncio.sleep(self.rate_limit_delay)
                        # Retry once
                        async with session.post(url, json=payload, headers=headers) as retry_response:
                            if retry_response.status == 200:
                                retry_data = await retry_response.json()
                                return self._parse_perplexity_response(retry_data, query)
                    
                    error_text = await response.text()
                    self.logger.error(f"[{self.module_code}] Perplexity API error: {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Perplexity API request failed: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M5 Perplexity API - {e}")
            print(f"   → Returning empty results")
            return []
    
    def _parse_perplexity_response(self, data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Parse Perplexity API response into search result format."""
        try:
            results = []
            
            # Get the main response content
            if 'choices' in data and data['choices']:
                content = data['choices'][0].get('message', {}).get('content', '')
                
                # First, try to use search_results if available (structured data)
                search_results = data.get('search_results', [])
                if search_results:
                    for i, search_result in enumerate(search_results[:self.max_results]):
                        result = {
                            'title': search_result.get('title', f'Search Result {i+1} for: {query}'),
                            'snippet': search_result.get('snippet', content[:200] if content else ''),
                            'link': search_result.get('url', f'https://perplexity.ai/search?q={query}'),
                            'displayLink': search_result.get('url', '').replace('https://', '').replace('http://', '').split('/')[0] if search_result.get('url') else 'perplexity.ai',
                            'formattedUrl': search_result.get('url', f'https://perplexity.ai/search?q={query}')
                        }
                        results.append(result)
                
                # If no search_results, try citations (list of URLs)
                elif 'citations' in data and data['citations']:
                    citations = data['citations']
                    for i, citation_url in enumerate(citations[:self.max_results]):
                        # Citations are just URLs, so we need to create titles and snippets
                        domain = citation_url.replace('https://', '').replace('http://', '').split('/')[0]
                        result = {
                            'title': f'Citation {i+1}: {domain}',
                            'snippet': f'Content from {citation_url} related to: {query}',
                            'link': citation_url,
                            'displayLink': domain,
                            'formattedUrl': citation_url
                        }
                        results.append(result)
                
                # If no structured data, create results from the content
                else:
                    content_chunks = self._split_content_into_results(content, query)
                    for i, chunk in enumerate(content_chunks[:self.max_results]):
                        result = {
                            'title': f'Perplexity Search Result {i+1} for: {query}',
                            'snippet': chunk,
                            'link': f'https://perplexity.ai/search?q={query}',
                            'displayLink': 'perplexity.ai',
                            'formattedUrl': f'https://perplexity.ai/search?q={query}'
                        }
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"[{self.module_code}] Failed to parse Perplexity response: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M5 Response Parsing - {e}")
            print(f"   → Returning empty results")
            return []
    
    def _split_content_into_results(self, content: str, query: str) -> List[str]:
        """Split Perplexity content into multiple result chunks."""
        if not content:
            return []
        
        # Split by paragraphs or sentences
        chunks = []
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            if len(paragraph.strip()) > 50:  # Only include substantial paragraphs
                chunks.append(paragraph.strip())
        
        # If we don't have enough chunks, split by sentences
        if len(chunks) < 3:
            sentences = content.split('. ')
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk + sentence) < 300:
                    current_chunk += sentence + ". "
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        
        return chunks[:self.max_results]
    
    def _create_placeholder_search_results(self, query: str) -> List[Dict[str, Any]]:
        """Create placeholder search results for testing/development."""
        return [
            {
                'title': f'Search Result 1 for: {query}',
                'snippet': f'This is a placeholder search result snippet for the query "{query}". It contains relevant information that would typically be found on the web.',
                'link': 'https://example.com/result1',
                'displayLink': 'example.com',
                'formattedUrl': 'https://example.com/result1'
            },
            {
                'title': f'Search Result 2 for: {query}',
                'snippet': f'Another placeholder result providing additional context about "{query}". This would normally come from a different website.',
                'link': 'https://example.org/result2',
                'displayLink': 'example.org',
                'formattedUrl': 'https://example.org/result2'
            },
            {
                'title': f'Search Result 3 for: {query}',
                'snippet': f'A third placeholder result with more information related to "{query}". This demonstrates multiple sources of information.',
                'link': 'https://example.net/result3',
                'displayLink': 'example.net',
                'formattedUrl': 'https://example.net/result3'
            }
        ]
    
    async def _create_evidence_items(self, search_results: List[Dict[str, Any]], 
                                   workunit, user_id: UUID, conversation_id: UUID) -> List[EvidenceItem]:
        """Convert search results to EvidenceItem objects."""
        evidence_items = []
        
        for i, result in enumerate(search_results):
            try:
                # Extract content (use snippet or try to extract full content)
                content = result.get('snippet', '')
                title = result.get('title', '')
                url = result.get('link', '')
                
                # For Perplexity results, we already have high-quality content
                # Only try content extraction for non-Perplexity URLs
                if (url and not url.startswith('https://example.') and 
                    not url.startswith('https://perplexity.ai')):
                    extracted_content = await self._extract_content(url)
                    if extracted_content and len(extracted_content) > len(content):
                        content = extracted_content
                
                # Create provenance
                provenance = Provenance(
                    source_type=SourceType.web,
                    source_id=url,
                    url=url,
                    retrieval_path=self.path_id,
                    router_decision_id=workunit.id,  # Using workunit ID as router decision ID
                    language="en"  # Default to English, could be detected
                )
                
                # Create evidence item
                evidence = EvidenceItem(
                    workunit_id=workunit.id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                    title=title,
                    score_raw=0.8 - (i * 0.1),  # Decreasing score based on search rank
                    provenance=provenance
                )
                
                evidence_items.append(evidence)
                
            except Exception as e:
                self.logger.error(f"[{self.module_code}] Failed to create evidence item: {e}")
                print(f"🔄 FALLBACK TRIGGERED: M5 Evidence Creation - {e}")
                print(f"   → Skipping this evidence item")
                continue
        
        return evidence_items
    
    async def _extract_content(self, url: str) -> Optional[str]:
        """Extract content from a web page."""
        try:
            # Simple content extraction using requests and BeautifulSoup
            # In production, you might want to use more sophisticated tools
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, headers={'User-Agent': 'QueryReactor/1.0'}) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text content
                        text = soup.get_text()
                        
                        # Clean up text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        # Limit content length
                        max_length = 10000  # 10KB limit
                        if len(text) > max_length:
                            text = text[:max_length] + "..."
                        
                        return text
                    
        except Exception as e:
            self.logger.warning(f"[{self.module_code}] Content extraction failed for {url}: {e}")
            print(f"🔄 FALLBACK TRIGGERED: M5 Content Extraction - {e}")
            print(f"   → Returning None for URL: {url}")
            return None
        
        return None


# Global instance
m5_internet_retrieval = M5InternetRetrievalLangGraph()


# LangGraph node function for integration
async def internet_retrieval_lg(state: ReactorState) -> ReactorState:
    """LangGraph node for M5 - Internet Retrieval."""
    return await m5_internet_retrieval.execute(state)