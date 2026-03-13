"""
browser-use fallback service.

This implementation runs browser-use in-process and uses an OpenAI-compatible
model configuration, which can point at MiniMax.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from ..llm_factory import LLMConfigurationError, create_llm, resolve_llm_settings
from ..logging_config import get_logger
from ..schemas import BrowserResult, Metadata

logger = get_logger("browser-use-fallback")


class BrowserUseFallbackService:
    """Fallback browser service backed by browser-use."""

    # Default CDP URL - can be overridden via config
    DEFAULT_CDP_URL = os.getenv("CDP_URL", "http://127.0.0.1:9222")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.provider = self.config.get("provider", os.getenv("LLM_PROVIDER", "minimax"))
        self.model = self.config.get("model", os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"))
        self.api_key = self.config.get("api_key", os.getenv("MINIMAX_API_KEY"))
        self.base_url = self.config.get("base_url", os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1"))
        self.max_steps = int(self.config.get("max_steps", os.getenv("BROWSER_USE_MAX_STEPS", "12")))
        self.timeout_seconds = int(
            self.config.get("timeout_seconds", os.getenv("MINIMAX_TIMEOUT_SECONDS", "90"))
        )
        self.max_retries = int(self.config.get("max_retries", os.getenv("MINIMAX_MAX_RETRIES", "2")))
        self.headless = self._parse_bool(
            self.config.get("headless", os.getenv("PLAYWRIGHT_HEADLESS", "true"))
        )
        # CDP connection - use external browser if available
        self.cdp_url = self.config.get("cdp_url", self.DEFAULT_CDP_URL)
        self.use_external_browser = self._parse_bool(
            self.config.get("use_external_browser", os.getenv("USE_EXTERNAL_BROWSER", "true"))
        )

    async def initialize(self) -> bool:
        """Validate imports and provider configuration for browser-use."""
        try:
            self._validate_runtime()
            logger.info("browser-use fallback service initialized")
            return True
        except Exception as exc:
            logger.error(f"Failed to initialize browser-use fallback: {exc}")
            return False

    async def web_search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Use browser-use to search Google and summarize the top results."""
        logger.info(f"Fallback: web_search '{query}'")
        task = (
            f"Open Google search for '{query}'. Collect up to {max_results} organic results. "
            "Return a concise plain-text list. Each item must include title, URL, and a short snippet."
        )
        return await self._run_task(task, reason="Fallback used for complex search")

    async def open_page(self, url: str) -> BrowserResult:
        """Use browser-use to open a page and report final location metadata."""
        logger.info(f"Fallback: open_page {url}")
        task = (
            f"Open {url}. Do not browse elsewhere unless redirected. "
            "Return the page title and final URL in plain text."
        )
        return await self._run_task(task, reason="Fallback used for complex navigation", url=url)

    async def extract_page(self, url: Optional[str] = None) -> BrowserResult:
        """Use browser-use to extract visible content from a page."""
        logger.info(f"Fallback: extract_page {url or '[current page]'}")
        task = (
            f"Open {url}. Extract the main visible page content in plain text and summarize the page."
            if url
            else "Extract the current page content in plain text and summarize the page."
        )
        return await self._run_task(
            task,
            reason="Fallback used for dynamic content extraction",
            url=url,
        )

    async def read_top_results(self, query: str, max_results: int = 3) -> BrowserResult:
        """Use browser-use to search and summarize multiple top results."""
        logger.info(f"Fallback: read_top_results '{query}' max={max_results}")
        task = (
            f"Search Google for '{query}'. Open the top {max_results} useful results and summarize the key findings. "
            "Return a concise multi-source summary with source URLs."
        )
        return await self._run_task(task, reason="Fallback used for multi-page reading")

    async def navigate_and_extract(self, task: str, url: str) -> BrowserResult:
        """Use browser-use for task-oriented browsing."""
        logger.info(f"Fallback: navigate_and_extract '{task}' -> {url}")
        prompt = (
            f"Start at {url}. Complete this task: {task}. "
            "Return the final answer, include important supporting details, and list the URLs visited."
        )
        return await self._run_task(prompt, reason="Fallback used for multi-step workflow", url=url)

    async def close(self):
        """No-op because browser-use runs per request."""
        logger.info("Closing browser-use fallback service")

    def check_ready(self) -> bool:
        """Synchronous readiness check for health probes."""
        try:
            self._validate_runtime()
            return True
        except Exception:
            return False

    def _validate_runtime(self):
        self._load_browser_use_dependencies()
        resolve_llm_settings(
            config={
                "provider": self.provider,
                "model": self.model,
                "api_key": self.api_key,
                "base_url": self.base_url,
                "timeout_seconds": self.timeout_seconds,
                "max_retries": self.max_retries,
            }
        )

    def _load_browser_use_dependencies(self):
        try:
            from browser_use import Agent, Browser, BrowserConfig
        except ImportError as exc:
            raise RuntimeError(
                "browser-use fallback requires 'browser-use'. "
                "Install dependencies from requirements.txt."
            ) from exc
        return Agent, Browser, BrowserConfig

    async def _run_task(self, task: str, reason: str, url: Optional[str] = None) -> BrowserResult:
        try:
            self._validate_runtime()
            Agent, Browser, BrowserConfig = self._load_browser_use_dependencies()
            llm = create_llm(
                provider=self.provider,
                config={
                    "model": self.model,
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                    "timeout_seconds": self.timeout_seconds,
                    "max_retries": self.max_retries,
                },
            )
            browser = Browser(
                config=BrowserConfig(
                    headless=self.headless,
                    cdp_url=self.cdp_url if self.use_external_browser else None
                )
            )
            try:
                agent = Agent(task=task, llm=llm, browser=browser)
                history = await asyncio.wait_for(
                    agent.run(max_steps=self.max_steps),
                    timeout=self.timeout_seconds,
                )
            finally:
                close = getattr(browser, "close", None)
                if close is not None:
                    maybe_coro = close()
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro

            content = self._extract_history_result(history)
            visited_urls = self._extract_history_urls(history)
            final_url = visited_urls[-1] if visited_urls else url
            title = self._extract_title(content, final_url)
            confidence = "high" if len(content) >= 400 else "medium"

            return BrowserResult(
                status="success" if content else "failed",
                backend="better-browser-use",
                title=title,
                url=final_url,
                summary=self._build_summary(content, title, task),
                content=content or None,
                key_points=self._extract_key_points(content),
                confidence=confidence if content else "low",
                error=None if content else "browser-use completed without returning output",
                metadata=Metadata(
                    used_fallback=True,
                    reason=reason,
                    visited_urls=visited_urls,
                    attempt_count=1,
                ),
            )
        except (LLMConfigurationError, Exception) as exc:
            logger.error(f"Fallback execution failed: {exc}")
            return BrowserResult(
                status="failed",
                backend="better-browser-use",
                url=url,
                error=str(exc),
                confidence="low",
                metadata=Metadata(
                    used_fallback=True,
                    reason=reason,
                    visited_urls=[url] if url else [],
                    attempt_count=1,
                ),
            )

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def _extract_history_result(history: Any) -> str:
        if history is None:
            return ""

        if hasattr(history, "final_result"):
            final_result = history.final_result()
            if isinstance(final_result, str):
                return final_result.strip()
            if final_result is not None:
                return str(final_result).strip()

        if hasattr(history, "result"):
            result = history.result
            if isinstance(result, str):
                return result.strip()
            if result is not None:
                return str(result).strip()

        return str(history).strip()

    @staticmethod
    def _extract_history_urls(history: Any) -> List[str]:
        if history is None:
            return []

        if hasattr(history, "urls"):
            try:
                urls = history.urls()
                if isinstance(urls, list):
                    return [str(url) for url in urls if url]
            except Exception:
                pass

        return []

    @staticmethod
    def _build_summary(content: str, title: Optional[str], fallback: str) -> str:
        if content:
            clipped = " ".join(content.split())[:220].strip()
            return clipped if len(content) <= 220 else f"{clipped}..."
        return title or fallback

    @staticmethod
    def _extract_key_points(content: str, limit: int = 5) -> List[str]:
        if not content:
            return []
        lines = [line.strip("-• ").strip() for line in content.splitlines()]
        structured = [line for line in lines if len(line) > 20]
        if structured:
            return structured[:limit]
        sentences = [part.strip() for part in content.replace("?", ".").replace("!", ".").split(".")]
        return [sentence for sentence in sentences if sentence][:limit]

    @staticmethod
    def _extract_title(content: str, fallback_url: Optional[str]) -> Optional[str]:
        if not content:
            return fallback_url
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        return first_line[:120] if first_line else fallback_url
