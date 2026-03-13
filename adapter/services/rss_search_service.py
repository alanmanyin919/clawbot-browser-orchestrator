"""
RSS Search Service - Uses news RSS feeds for search results.
Works without API keys as a fallback when search engines are blocked.
"""

import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from html import unescape
from datetime import datetime, timedelta

from ..schemas import BrowserResult, Metadata
from ..logging_config import get_logger

logger = get_logger("rss_search")


class RSSSearchService:
    """Search using RSS feeds from major news sources."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.news_sources = [
            # (feed_url, source_name)
            ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
            ("https://feeds.bbci.co.uk/news/rss.xml", "BBC"),
            ("http://feeds.reuters.com/reuters/topNews", "Reuters"),
            ("http://feeds.reuters.com/reuters/worldNews", "Reuters World"),
        ]
    
    async def initialize(self) -> bool:
        """Initialize the service (no-op for RSS)."""
        return True
    
    async def web_search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Search using RSS feeds."""
        logger.info(f"RSS Search: '{query}'")
        
        results = await self._search_rss(query, max_results)
        
        if not results:
            return BrowserResult(
                status="failed",
                title=f"No results found for: {query}",
                url="",
                summary=f"Could not find any results for '{query}' via RSS feeds.",
                content=None,
                key_points=[],
                confidence="low",
                error="No RSS results found",
                metadata=Metadata(
                    used_fallback=True,
                    reason="rss_search",
                    visited_urls=[],
                    attempt_count=1
                )
            )
        
        # Build key_points as strings
        key_points = []
        for r in results:
            point = f"{r['title']} ({r['source']})"
            key_points.append(point)
        
        # Build content
        content_parts = []
        for r in results:
            content_parts.append(f"## {r['title']}\n{r['snippet']}\nSource: {r['source']}\nURL: {r['url']}")
        
        return BrowserResult(
            status="success",
            title=f"RSS Results for: {query}",
            url="",
            summary=f"Found {len(results)} results from news RSS feeds for '{query}'.",
            content="\n\n".join(content_parts),
            key_points=key_points,
            confidence="medium",
            error=None,
            metadata=Metadata(
                used_fallback=True,
                reason="rss_search",
                visited_urls=[r["url"] for r in results],
                attempt_count=1
            )
        )
    
    async def _search_rss(self, query: str, max_results: int) -> List[Dict]:
        """Search multiple RSS feeds for query."""
        results = []
        query_words = set(query.lower().split())
        
        for url, source_name in self.news_sources:
            try:
                feed_results = await self._fetch_feed(url, source_name, query_words, max_results)
                results.extend(feed_results)
            except Exception as e:
                logger.warning(f"Error fetching {source_name}: {e}")
            
            if len(results) >= max_results:
                break
        
        # Remove duplicates and limit
        seen = set()
        unique_results = []
        for r in results:
            if r["title"] not in seen:
                seen.add(r["title"])
                unique_results.append(r)
        
        return unique_results[:max_results]
    
    async def _fetch_feed(self, url: str, source_name: str, query_words: set, max_results: int) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        results = []
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (compatible; OpenClaw/1.0)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
            
            root = ET.fromstring(data)
            
            for item in root.findall('.//item')[:30]:
                title_el = item.find('title')
                desc_el = item.find('description')
                link_el = item.find('link')
                
                title = title_el.text if title_el is not None else ""
                desc = desc_el.text if desc_el is not None else ""
                link = link_el.text if link_el is not None else ""
                
                if not title:
                    continue
                
                # Check relevance
                search_text = (title + " " + desc).lower()
                if any(word in search_text for word in query_words):
                    # Clean description
                    desc_clean = unescape(desc)
                    if len(desc_clean) > 200:
                        desc_clean = desc_clean[:200] + "..."
                    
                    results.append({
                        "title": unescape(title),
                        "snippet": desc_clean,
                        "url": link,
                        "source": source_name
                    })
        
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        
        return results
    
    async def close(self):
        """Close the service (no-op for RSS)."""
        pass
