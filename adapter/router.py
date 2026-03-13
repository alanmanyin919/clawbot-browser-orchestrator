"""
Browser Router - decides which backend to use per tool.
"""

from typing import Optional, Dict, Any, Tuple
import yaml
from pathlib import Path

from .schemas import BrowserResult, Metadata
from .services.playwright_primary import PlaywrightPrimaryService
from .services.browser_use import BrowserUseService
from .logging_config import get_logger

logger = get_logger("router")


class BrowserRouter:
    """Routes browser requests between browser-use and Playwright."""
    
    def __init__(self, config_path: str = "config/browser-policy.yaml"):
        # Load routing policy
        policy_file = Path(config_path)
        if policy_file.exists():
            with open(policy_file) as f:
                self.policy = yaml.safe_load(f)
        else:
            self.policy = self._default_policy()
        
        # Main backend is browser-use. Secondary backend is Playwright.
        self.browser_use = BrowserUseService(self.policy.get("browser_use", {}))
        self.playwright = PlaywrightPrimaryService(self.policy.get("playwright", {}))
        
        # Config
        self.max_retries = self.policy.get("browser_use", {}).get("max_retries", 2)
        self.fallback_enabled = True
        self.browser_use_available = False
        self.playwright_available = False
        
        self._initialized = False
    
    def _default_policy(self) -> Dict:
        """Default routing policy."""
        return {
            "primary": {
                "name": "better-browser-use",
                "timeout_seconds": 90,
                "max_retries": 2
            },
            "fallback": {
                "name": "playwright-mcp",
                "timeout_seconds": 45,
                "max_retries": 1
            },
            "fallback_triggers": [
                {"type": "extraction_failed", "description": "Primary extraction failed"},
                {"type": "navigation_stuck", "description": "Primary navigation got stuck"},
                {"type": "dynamic_content", "description": "Page content too dynamic"}
            ],
            "stop_conditions": [
                {"type": "captcha", "action": "blocked"},
                {"type": "login_required", "action": "blocked"},
                {"type": "access_denied", "action": "restricted"}
            ]
        }
    
    async def initialize(self):
        """Initialize both backends."""
        if self._initialized:
            return
        
        logger.info("Initializing browser router...")
        
        # Initialize main backend (browser-use)
        browser_use_ok = await self.browser_use.initialize()
        self.browser_use_available = browser_use_ok
        logger.info(f"browser-use backend: {'OK' if browser_use_ok else 'FAILED'}")
        
        # Initialize secondary backend (Playwright)
        playwright_ok = await self.playwright.initialize()
        self.playwright_available = playwright_ok
        self.fallback_enabled = playwright_ok
        logger.info(f"Playwright backend: {'OK' if playwright_ok else 'FAILED'}")
        
        self._initialized = True
        logger.info("Browser router initialized")
    
    def _preferred_backend(self, tool_name: str) -> Tuple[Any, Any]:
        """Return preferred and secondary backends for a tool."""
        if tool_name in {"open_page", "extract_page"}:
            return self.playwright, self.browser_use
        return self.browser_use, self.playwright

    def _should_use_secondary(self, result: BrowserResult, tool_name: str = "") -> bool:
        """
        Determine if fallback should be used based on result.
        
        Returns True if:
        - Primary failed
        - Extraction was incomplete
        - Navigation got stuck
        """
        if not self.fallback_enabled:
            return False
        
        # Check for failure
        if result.status == "failed":
            logger.info(f"Secondary trigger: preferred backend failed - {result.error}")
            return True
        
        if tool_name == "navigate_and_extract" and result.confidence != "high":
            logger.info("Secondary trigger: navigate_and_extract returned unresolved or low confidence result")
            return True

        # Check for incomplete content
        if result.status == "success":
            content = (result.content or "").strip()
            if content and len(content) < 200:
                logger.info("Secondary trigger: Thin content detected")
                return True
            if not content and tool_name in {"extract_page", "read_top_results"}:
                logger.info("Secondary trigger: Missing extracted content")
                return True
        
        # Check for low confidence
        if result.confidence == "low":
            logger.info("Secondary trigger: Low confidence result")
            return True
        
        return False

    async def _run_with_routing(self, tool_name: str, *args) -> BrowserResult:
        """Run a tool on the preferred backend, then try the secondary backend if needed."""
        await self.initialize()
        preferred, secondary = self._preferred_backend(tool_name)

        result = await getattr(preferred, tool_name)(*args)
        result = self._check_stop_conditions(result)
        if result.status in ["blocked", "restricted"]:
            return result

        if self._should_use_secondary(result, tool_name):
            logger.info("Router: Trying secondary backend")
            result = await getattr(secondary, tool_name)(*args)
            result = self._check_stop_conditions(result)

        return result
    
    def _check_stop_conditions(self, result: BrowserResult) -> BrowserResult:
        """
        Check if we should stop due to anti-bot measures.
        
        Returns modified result with blocked/restricted status if needed.
        """
        content = (result.content or "").lower()
        url = (result.url or "").lower()
        combined = content + url
        
        stop_conditions = self.policy.get("stop_conditions", [])
        
        for condition in stop_conditions:
            condition_type = condition.get("type", "")
            action = condition.get("action", "blocked")
            
            # Check for CAPTCHA
            if condition_type == "captcha":
                if any(x in combined for x in ["captcha", "recaptcha", "verify you're human"]):
                    logger.warning("Stop condition: CAPTCHA detected")
                    result.status = "blocked"
                    result.error = "CAPTCHA challenge detected - stopping"
                    return result
            
            # Check for login required
            if condition_type == "login_required":
                if any(x in combined for x in ["sign in", "login required", "please sign in"]):
                    if "captcha" not in combined:  # Not a captcha page
                        logger.warning("Stop condition: Login required")
                        result.status = "blocked"
                        result.error = "Login required to access this content"
                        return result
            
            # Check for access denied
            if condition_type == "access_denied":
                if any(x in combined for x in ["403", "forbidden", "access denied", "blocked"]):
                    logger.warning("Stop condition: Access denied")
                    result.status = "restricted"
                    result.error = "Access denied to this resource"
                    return result
        
        return result
    
    async def web_search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Web search with browser-use preferred."""
        logger.info(f"Router: web_search for '{query}'")
        return await self._run_with_routing("web_search", query, max_results)
    
    async def open_page(self, url: str) -> BrowserResult:
        """Open a page with Playwright preferred."""
        logger.info(f"Router: open_page {url}")
        return await self._run_with_routing("open_page", url)
    
    async def extract_page(self, url: Optional[str] = None) -> BrowserResult:
        """Extract page content with Playwright preferred."""
        logger.info("Router: extract_page")
        return await self._run_with_routing("extract_page", url)
    
    async def read_top_results(self, query: str, max_results: int = 3) -> BrowserResult:
        """Read top results with browser-use preferred."""
        logger.info(f"Router: read_top_results '{query}' (max={max_results})")
        return await self._run_with_routing("read_top_results", query, max_results)
    
    async def navigate_and_extract(self, task: str, url: str) -> BrowserResult:
        """Navigate and extract with browser-use preferred."""
        logger.info(f"Router: navigate_and_extract - {task}")
        return await self._run_with_routing("navigate_and_extract", task, url)
    
    async def close(self):
        """Clean up resources."""
        await self.browser_use.close()
        await self.playwright.close()


# Global router instance
_router: Optional[BrowserRouter] = None


def get_router() -> BrowserRouter:
    """Get the global router instance."""
    global _router
    if _router is None:
        _router = BrowserRouter()
    return _router
