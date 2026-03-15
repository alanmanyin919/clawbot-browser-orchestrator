"""
Normalized data schemas for browser orchestrator.
Both browser-use and Playwright return data in this standard format.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """Metadata about the request execution."""
    used_fallback: bool = False
    reason: Optional[str] = None
    visited_urls: List[str] = Field(default_factory=list)
    attempt_count: int = 1


class BrowserResult(BaseModel):
    """
    Standardized result format returned by all browser tools.
    
    This schema ensures both Playwright MCP and browser-use
    return consistent output that any agent or client can process uniformly.
    """
    status: Literal["success", "failed", "blocked", "restricted"] = "success"
    backend: Literal["playwright-mcp", "better-browser-use"] = "playwright-mcp"
    title: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    error: Optional[str] = None
    metadata: Metadata = Field(default_factory=Metadata)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()


class SearchResult(BaseModel):
    """Individual search result item."""
    title: str
    url: str
    snippet: str


class SearchResponse(BaseModel):
    """Response from web search operation."""
    query: str
    results: List[SearchResult]
    total_results: Optional[int] = None


class HealthStatus(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    primary: bool
    fallback: bool
    uptime_seconds: float
    version: str = "1.0.0"
