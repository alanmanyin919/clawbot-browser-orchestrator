"""
Health check module for browser orchestrator.
"""

import time
from .schemas import HealthStatus
from .logging_config import get_logger
from .services.playwright_primary import PlaywrightPrimaryService
from .services.browser_use import BrowserUseService

logger = get_logger("health")


class HealthChecker:
    """Monitors health of browser-use and Playwright backends."""
    
    def __init__(self):
        self.start_time = time.time()
        self.browser_use_available = False
        self.playwright_available = False
        self.browser_use_service = BrowserUseService()
        self.playwright_service = PlaywrightPrimaryService()
    
    async def check_browser_use(self) -> bool:
        """Check if browser-use is available."""
        try:
            self.browser_use_available = self.browser_use_service.check_ready()
            return self.browser_use_available
        except Exception as e:
            logger.warning(f"browser-use health check failed: {e}")
            self.browser_use_available = False
            return False
    
    async def check_playwright(self) -> bool:
        """Check if Playwright MCP is available."""
        try:
            self.playwright_available = await self.playwright_service.initialize()
            return self.playwright_available
        except Exception as e:
            logger.warning(f"Playwright health check failed: {e}")
            self.playwright_available = False
            return False
    
    async def check_health(self) -> HealthStatus:
        """Get overall health status."""
        browser_use_ok = await self.check_browser_use()
        playwright_ok = await self.check_playwright()
        
        uptime = time.time() - self.start_time
        
        if browser_use_ok and playwright_ok:
            status = "healthy"
        elif browser_use_ok or playwright_ok:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            primary=browser_use_ok,
            fallback=playwright_ok,
            uptime_seconds=uptime
        )


# Global health checker instance
_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the global health checker."""
    return _health_checker
