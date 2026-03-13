"""
HTTP-based search service.
Works without API keys - uses direct HTTP requests to search engines.
"""

import requests
import re
from urllib.parse import quote_plus, unquote
from typing import List, Dict, Optional

from ..schemas import BrowserResult, Metadata
from ..logging_config import get_logger

logger = get_logger("http-search")


class HTTPSearchService:
    """Search using HTTP requests to search engines."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 15)
    
    async def initialize(self) -> bool:
        return True
    
    def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using DuckDuckGo HTML version."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml',
            }
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code != 200:
                return []
            
            # Parse results
            results = []
            ddg_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(ddg_pattern, response.text)
            
            for url, title in matches[:max_results]:
                url = unquote(url)
                if url.startswith('//'):
                    url = 'https:' + url
                results.append({'title': title.strip(), 'url': url})
            
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def _search_bing(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using Bing."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
            }
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code != 200:
                return []
            
            results = []
            # Bing result pattern
            bing_pattern = r'<h2[^>]*><a[^>]*href="[^"]*"[^>]*>([^<]+)</a></h2>'
            href_pattern = r'<h2[^>]*><a[^>]*href="([^"]*)"'
            
            titles = re.findall(bing_pattern, response.text)
            hrefs = re.findall(href_pattern, response.text)
            
            for title, url in zip(titles[:max_results], hrefs[:max_results]):
                url = unquote(url)
                if 'http' in url and 'microsoft' not in url:
                    results.append({'title': title.strip(), 'url': url})
            
            return results
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []
    
    async def web_search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Perform web search via HTTP."""
        logger.info(f"HTTP Search: '{query}'")
        
        # Try DuckDuckGo first
        results = self._search_duckduckgo(query, max_results)
        
        # Fallback to Bing
        if not results:
            results = self._search_bing(query, max_results)
        
        if not results:
            return BrowserResult(
                status="failed",
                backend="http-search",
                title=f"No results for: {query}",
                summary="No search results found",
                error="No HTTP search results",
                metadata=Metadata(used_fallback=True, reason="http_search_fallback")
            )
        
        key_points = [r['title'] for r in results]
        
        return BrowserResult(
            status="success",
            backend="http-search",
            title=f"Search results for: {query}",
            url=f"https://duckduckgo.com/?q={quote_plus(query)}",
            summary=f"Found {len(results)} results for '{query}'",
            content="\n".join([f"- {r['title']}: {r['url']}" for r in results]),
            key_points=key_points,
            confidence="high",
            metadata=Metadata(
                used_fallback=True,
                reason="http_search_fallback",
                visited_urls=[r['url'] for r in results[:3]],
                attempt_count=1
            )
        )
    
    async def open_page(self, url: str) -> BrowserResult:
        """Open a page via HTTP."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', response.text, re.I)
            title = title_match.group(1) if title_match else url
            
            return BrowserResult(
                status="success",
                backend="http-search",
                title=title,
                url=url,
                summary=f"Fetched {url}",
                content=response.text[:5000],
                confidence="medium",
                metadata=Metadata(used_fallback=True, visited_urls=[url])
            )
        except Exception as e:
            return BrowserResult(
                status="failed",
                backend="http-search",
                error=str(e),
                metadata=Metadata(used_fallback=True)
            )
    
    async def extract_page(self, url: Optional[str] = None) -> BrowserResult:
        """Extract page content via HTTP."""
        if not url:
            return BrowserResult(status="failed", error="No URL provided")
        return await self.open_page(url)
    
    async def read_top_results(self, query: str, max_results: int = 3) -> BrowserResult:
        """Search and read top results."""
        return await self.web_search(query, max_results)
    
    async def navigate_and_extract(self, task: str, url: str) -> BrowserResult:
        """Navigate and extract."""
        return await self.open_page(url)
