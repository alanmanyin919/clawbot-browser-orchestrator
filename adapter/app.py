"""
Browser Orchestrator - Main Application.

Exposes MCP-style tools for browser automation:
- web_search
- open_page
- extract_page
- read_top_results
- navigate_and_extract
"""

import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add adapter to path
sys.path.insert(0, str(Path(__file__).parent))

from adapter.logging_config import setup_logging, get_logger
from adapter.schemas import BrowserResult, HealthStatus
from adapter.router import get_router
from adapter.health import get_health_checker

# Setup logging
setup_logging()
logger = get_logger("app")

# Create FastAPI app
app = FastAPI(
    title="Browser Orchestrator",
    description="Browser automation MCP stack with browser-use as main access and Playwright for direct page access",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5


class OpenPageRequest(BaseModel):
    url: str


class ExtractRequest(BaseModel):
    url: Optional[str] = None


class ReadTopResultsRequest(BaseModel):
    query: str
    max_results: Optional[int] = 3


class NavigateExtractRequest(BaseModel):
    task: str
    url: Optional[str] = None


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    checker = get_health_checker()
    return await checker.check_health()


# Tool endpoints
@app.post("/tools/web_search")
async def web_search(request: SearchRequest) -> BrowserResult:
    """
    Web Search Tool.
    
    Search the web and return top results with summaries.
    Uses browser-use by default and tries Playwright if needed.
    """
    logger.info(f"Tool: web_search - '{request.query}'")
    router = get_router()
    return await router.web_search(request.query, request.max_results)


@app.post("/tools/open_page")
async def open_page(request: OpenPageRequest) -> BrowserResult:
    """
    Open Page Tool.
    
    Open a URL in the browser.
    """
    logger.info(f"Tool: open_page - {request.url}")
    router = get_router()
    return await router.open_page(request.url)


@app.post("/tools/extract_page")
async def extract_page(request: ExtractRequest) -> BrowserResult:
    """
    Extract Page Tool.
    
    Extract content from a page (current or specified URL).
    """
    logger.info(f"Tool: extract_page - {request.url}")
    router = get_router()
    return await router.extract_page(request.url)


@app.post("/tools/read_top_results")
async def read_top_results(request: ReadTopResultsRequest) -> BrowserResult:
    """
    Read Top Results Tool.
    
    Search and read top N results.
    """
    logger.info(f"Tool: read_top_results - '{request.query}' (max={request.max_results})")
    router = get_router()
    return await router.read_top_results(request.query, request.max_results)


@app.post("/tools/navigate_and_extract")
async def navigate_and_extract(request: NavigateExtractRequest) -> BrowserResult:
    """
    Navigate and Extract Tool.
    
    Multi-step navigation and extraction.
    """
    logger.info(f"Tool: navigate_and_extract - {request.task}")
    router = get_router()
    return await router.navigate_and_extract(request.task, request.url or "")


# MCP compatibility endpoints
@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "web_search",
                "description": "Search the web and return top results",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "number", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "open_page",
                "description": "Open a URL in the browser",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            },
            {
                "name": "extract_page",
                "description": "Extract content from a page",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}}
                }
            },
            {
                "name": "read_top_results",
                "description": "Search and read top N results",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "number", "default": 3}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "navigate_and_extract",
                "description": "Multi-step navigation and extraction",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "url": {"type": "string"}
                    },
                    "required": ["task"]
                }
            }
        ]
    }


# Startup
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Starting Browser Orchestrator...")
    router = get_router()
    await router.initialize()
    logger.info("Browser Orchestrator ready")


# Shutdown
@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down Browser Orchestrator...")
    router = get_router()
    await router.close()


if __name__ == "__main__":
    import uvicorn
    
    # Get port from env or default
    port = int(os.getenv("MCP_PORT", "3101"))
    
    uvicorn.run(app, host="0.0.0.0", port=port)
