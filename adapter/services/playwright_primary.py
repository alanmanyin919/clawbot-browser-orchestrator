"""
Playwright MCP primary service.

This implementation launches a local Playwright MCP process over stdio
for each request and uses the browser tools exposed by that server.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import quote_plus

from ..logging_config import get_logger
from ..schemas import BrowserResult, Metadata

logger = get_logger("playwright-primary")


class PlaywrightPrimaryService:
    """Primary browser service backed by a local Playwright MCP server."""

    REQUIRED_TOOLS = {"browser_navigate", "browser_run_code"}
    
    # Default CDP URL
    DEFAULT_CDP_URL = os.getenv("CDP_URL", "http://127.0.0.1:9222")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.command = self.config.get(
            "command",
            os.getenv("PLAYWRIGHT_MCP_COMMAND", "npx"),
        )
        self.args = self._parse_args(
            self.config.get("args", os.getenv("PLAYWRIGHT_MCP_ARGS", "@playwright/mcp@latest"))
        )
        self.timeout_seconds = int(
            self.config.get("timeout_seconds", os.getenv("PLAYWRIGHT_MCP_TIMEOUT_SECONDS", "45"))
        )
        self.headless = self._parse_bool(
            self.config.get("headless", os.getenv("PLAYWRIGHT_HEADLESS", "true"))
        )
        # CDP connection - use external browser if available
        self.cdp_url = self.config.get("cdp_url", self.DEFAULT_CDP_URL)
        self.use_external_browser = self._parse_bool(
            self.config.get("use_external_browser", os.getenv("USE_EXTERNAL_BROWSER", "true"))
        )
        self._validated_tools: Optional[set[str]] = None
        self._import_error: Optional[str] = None

    async def initialize(self) -> bool:
        """Validate that the Playwright MCP runtime can start and exposes required tools."""
        try:
            logger.info("Initializing Playwright primary service")
            await self._validate_required_tools()
            logger.info("Playwright primary service initialized")
            return True
        except Exception as exc:
            self._import_error = str(exc)
            logger.error(f"Failed to initialize Playwright primary service: {exc}")
            return False

    async def web_search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Perform a Google search and extract top results using Playwright MCP."""
        logger.info(f"Primary: web_search '{query}'")
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"

        try:
            async with self._session() as session:
                await self._navigate(session, search_url)
                await self._wait_for_page(session)
                payload = await self._run_json(
                    session,
                    self._google_results_script(),
                    {"maxResults": max_results},
                )

            results = payload.get("results", [])
            visited = [search_url] + [item["url"] for item in results if item.get("url")]
            key_points = [
                self._summarize_search_result(item)
                for item in results[:max_results]
                if item.get("title") and item.get("url")
            ]
            content = "\n".join(
                f"{idx + 1}. {item.get('title', 'Untitled')} - {item.get('url', '')}\n{item.get('snippet', '').strip()}".strip()
                for idx, item in enumerate(results[:max_results])
            ).strip()

            confidence = "high" if results else "low"
            status = "success" if results else "failed"
            summary = (
                f"Found {len(results[:max_results])} Google results for '{query}'"
                if results
                else f"No Google results extracted for '{query}'"
            )
            error = None if results else "No search results could be extracted from Google"

            return BrowserResult(
                status=status,
                backend="playwright-mcp",
                title=payload.get("title") or f"Google results for {query}",
                url=payload.get("url") or search_url,
                summary=summary,
                content=content or None,
                key_points=key_points,
                confidence=confidence,
                error=error,
                metadata=Metadata(
                    used_fallback=False,
                    visited_urls=visited,
                    attempt_count=1,
                ),
            )
        except Exception as exc:
            logger.error(f"Primary web_search failed: {exc}")
            return self._failure(str(exc), url=search_url)

    async def open_page(self, url: str) -> BrowserResult:
        """Open a URL and capture final page metadata."""
        logger.info(f"Primary: open_page {url}")
        try:
            async with self._session() as session:
                await self._navigate(session, url)
                await self._wait_for_page(session)
                page_data = await self._run_json(session, self._page_metadata_script())

            return BrowserResult(
                status="success",
                backend="playwright-mcp",
                title=page_data.get("title"),
                url=page_data.get("url") or url,
                summary=f"Opened {page_data.get('url') or url}",
                content=None,
                confidence="high",
                metadata=Metadata(
                    used_fallback=False,
                    visited_urls=[page_data.get("url") or url],
                    attempt_count=1,
                ),
            )
        except Exception as exc:
            logger.error(f"Primary open_page failed: {exc}")
            return self._failure(str(exc), url=url)

    async def extract_page(self, url: Optional[str] = None) -> BrowserResult:
        """Navigate if needed and extract visible text from the page."""
        logger.info(f"Primary: extract_page {url or '[current page]'}")
        try:
            async with self._session() as session:
                if url:
                    await self._navigate(session, url)
                    await self._wait_for_page(session)
                page_data = await self._run_json(session, self._page_extract_script())

            content = self._normalize_text(page_data.get("content"))
            confidence = "high" if len(content) >= 500 else "low"
            status = "success" if content else "failed"
            summary = self._build_summary(content, page_data.get("title"), fallback="Page content extracted")
            error = None if content else "No visible content extracted from page"

            return BrowserResult(
                status=status,
                backend="playwright-mcp",
                title=page_data.get("title"),
                url=page_data.get("url") or url,
                summary=summary,
                content=content or None,
                key_points=self._extract_key_points(content),
                confidence=confidence,
                error=error,
                metadata=Metadata(
                    used_fallback=False,
                    visited_urls=[page_data.get("url") or url] if (page_data.get("url") or url) else [],
                    attempt_count=1,
                ),
            )
        except Exception as exc:
            logger.error(f"Primary extract_page failed: {exc}")
            return self._failure(str(exc), url=url)

    async def read_top_results(self, query: str, max_results: int = 3) -> BrowserResult:
        """Search Google and read the top extracted results."""
        logger.info(f"Primary: read_top_results '{query}' max={max_results}")
        search_result = await self.web_search(query, max_results)
        if search_result.status != "success":
            return search_result

        parsed_results = self._parse_search_content(search_result.content or "")
        page_summaries: List[str] = []
        key_points = list(search_result.key_points)
        visited_urls = list(search_result.metadata.visited_urls)

        for item in parsed_results[:max_results]:
            url = item.get("url")
            if not url:
                continue
            page_result = await self.extract_page(url)
            if page_result.url:
                visited_urls.append(page_result.url)
            if page_result.status != "success":
                key_points.append(f"Could not extract {url}: {page_result.error or 'unknown error'}")
                continue
            snippet = self._build_summary(page_result.content or "", page_result.title, fallback=url)
            page_summaries.append(f"{page_result.title or url}\n{snippet}")
            if snippet:
                key_points.append(snippet)

        content = "\n\n".join(page_summaries).strip()
        confidence = "high" if page_summaries else "low"
        status = "success" if page_summaries else "failed"

        return BrowserResult(
            status=status,
            backend="playwright-mcp",
            title=f"Top {max_results} results for: {query}",
            url=search_result.url,
            summary=f"Read {len(page_summaries)} top results for '{query}'",
            content=content or search_result.content,
            key_points=key_points[: max(max_results * 2, 5)],
            confidence=confidence,
            error=None if page_summaries else "No result pages could be extracted",
            metadata=Metadata(
                used_fallback=False,
                visited_urls=self._dedupe_urls(visited_urls),
                attempt_count=1,
            ),
        )

    async def navigate_and_extract(self, task: str, url: str) -> BrowserResult:
        """Deterministically navigate and extract; low confidence if task is not clearly resolved."""
        logger.info(f"Primary: navigate_and_extract '{task}' -> {url}")
        extracted = await self.extract_page(url)
        if extracted.status != "success":
            return extracted

        content = extracted.content or ""
        resolved = self._task_keywords_present(task, content)
        confidence = "high" if resolved else "low"
        summary = (
            f"Completed deterministic extraction for '{task}'"
            if resolved
            else f"Loaded and extracted the page for '{task}', but could not confirm the task was resolved"
        )

        return BrowserResult(
            status="success",
            backend="playwright-mcp",
            title=extracted.title or task,
            url=extracted.url or url,
            summary=summary,
            content=content,
            key_points=extracted.key_points,
            confidence=confidence,
            metadata=Metadata(
                used_fallback=False,
                reason=None if resolved else "Task resolution not confirmed by deterministic extraction",
                visited_urls=extracted.metadata.visited_urls,
                attempt_count=1,
            ),
        )

    async def list_available_tools(self) -> List[str]:
        """List tool names exposed by the Playwright MCP server."""
        async with self._session() as session:
            tools = await session.list_tools()
        return sorted(tool.name for tool in getattr(tools, "tools", []))

    async def close(self):
        """No-op because sessions are request-scoped."""
        logger.info("Closing Playwright primary service")

    @staticmethod
    def _parse_args(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value is None:
            return []
        return [part for part in str(value).split() if part]

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[Any]:
        ClientSession, StdioServerParameters, stdio_client = self._load_mcp_sdk()
        server_params = StdioServerParameters(command=self.command, args=self._command_args())
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    def _load_mcp_sdk(self):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError(
                "The 'mcp' package is required for Playwright integration. "
                "Install dependencies from requirements.txt."
            ) from exc
        return ClientSession, StdioServerParameters, stdio_client

    def _command_args(self) -> List[str]:
        args = list(self.args)
        if self.headless and "--headless" not in args:
            args.append("--headless")
        return args

    async def _validate_required_tools(self):
        if self._validated_tools is not None:
            return

        async with self._session() as session:
            tools = await session.list_tools()
        tool_names = {tool.name for tool in getattr(tools, "tools", [])}
        missing = self.REQUIRED_TOOLS - tool_names
        if missing:
            raise RuntimeError(
                "Playwright MCP server is missing required tools: "
                + ", ".join(sorted(missing))
            )
        self._validated_tools = tool_names

    async def _navigate(self, session: Any, url: str):
        await self._validate_required_tools()
        await self._call_tool(session, "browser_navigate", {"url": url})

    async def _wait_for_page(self, session: Any):
        if self._validated_tools and "browser_wait_for" in self._validated_tools:
            try:
                await self._call_tool(session, "browser_wait_for", {"time": 1})
            except Exception:
                logger.debug("browser_wait_for failed; continuing without explicit wait")
        else:
            await asyncio.sleep(1)

    async def _run_json(self, session: Any, code: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        variables = variables or {}
        response = await self._call_tool(
            session,
            "browser_run_code",
            {"code": code, "variables": variables},
        )
        payload = self._extract_tool_payload(response)
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Playwright MCP returned non-JSON output: {payload[:200]}") from exc
        raise RuntimeError(f"Unsupported Playwright MCP payload: {type(payload).__name__}")

    async def _call_tool(self, session: Any, name: str, arguments: Dict[str, Any]) -> Any:
        try:
            return await asyncio.wait_for(
                session.call_tool(name, arguments),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(f"Timed out calling Playwright MCP tool '{name}'") from exc

    def _extract_tool_payload(self, response: Any) -> Any:
        structured = getattr(response, "structuredContent", None)
        if structured is not None:
            return structured

        texts: List[str] = []
        for item in getattr(response, "content", []) or []:
            text = getattr(item, "text", None)
            if text:
                texts.append(text)
        joined = "\n".join(texts).strip()
        return joined

    def _failure(self, error: str, url: Optional[str] = None) -> BrowserResult:
        return BrowserResult(
            status="failed",
            backend="playwright-mcp",
            url=url,
            error=error,
            confidence="low",
            metadata=Metadata(used_fallback=False, attempt_count=1),
        )

    @staticmethod
    def _normalize_text(text: Optional[str], limit: int = 12000) -> str:
        if not text:
            return ""
        normalized = " ".join(str(text).split())
        return normalized[:limit].strip()

    @staticmethod
    def _extract_key_points(text: str, limit: int = 5) -> List[str]:
        if not text:
            return []
        sentences = [part.strip() for part in text.replace("?", ".").replace("!", ".").split(".")]
        return [sentence for sentence in sentences if sentence][:limit]

    @staticmethod
    def _build_summary(content: str, title: Optional[str], fallback: str) -> str:
        if content:
            clipped = content[:220].strip()
            return clipped if len(content) <= 220 else f"{clipped}..."
        return title or fallback

    @staticmethod
    def _dedupe_urls(urls: List[str]) -> List[str]:
        seen = set()
        deduped = []
        for url in urls:
            if url and url not in seen:
                deduped.append(url)
                seen.add(url)
        return deduped

    @staticmethod
    def _parse_search_content(content: str) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        blocks = [block.strip() for block in content.split("\n") if block.strip()]
        for block in blocks:
            if " - http" not in block:
                continue
            first_line = block.split("\n", 1)[0]
            title, _, url = first_line.partition(" - ")
            results.append({"title": title.split(". ", 1)[-1], "url": url.strip()})
        return results

    @staticmethod
    def _task_keywords_present(task: str, content: str) -> bool:
        if not content:
            return False
        content_lower = content.lower()
        tokens = [
            token
            for token in "".join(ch.lower() if ch.isalnum() else " " for ch in task).split()
            if len(token) >= 4
        ]
        if not tokens:
            return len(content) > 500
        matched = sum(1 for token in tokens if token in content_lower)
        return matched >= max(1, min(2, len(tokens)))

    @staticmethod
    def _summarize_search_result(item: Dict[str, Any]) -> str:
        title = item.get("title", "Untitled")
        snippet = (item.get("snippet") or "").strip()
        return f"{title}: {snippet}" if snippet else title

    @staticmethod
    def _google_results_script() -> str:
        return """
const maxResults = variables.maxResults ?? 5;
const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
const payload = await page.evaluate((limit) => {
  const selectors = [
    'div#search div.g',
    'div[data-snc]',
    'div[data-hveid]'
  ];
  const seen = new Set();
  const results = [];
  const nodes = Array.from(document.querySelectorAll(selectors.join(',')));
  for (const node of nodes) {
    const titleEl = node.querySelector('h3');
    const anchor = titleEl?.closest('a') || node.querySelector('a[href]');
    if (!titleEl || !anchor) continue;
    const url = anchor.href;
    const title = titleEl.innerText;
    if (!url || !title || seen.has(url)) continue;
    const snippetEl = node.querySelector('.VwiC3b, .yXK7lf, .MUxGbd, [data-sncf]');
    results.push({
      title,
      url,
      snippet: snippetEl ? snippetEl.innerText : ''
    });
    seen.add(url);
    if (results.length >= limit) break;
  }
  return {
    title: document.title,
    url: window.location.href,
    results
  };
}, maxResults);

payload.title = normalize(payload.title);
payload.url = normalize(payload.url);
payload.results = (payload.results || []).map((item) => ({
  title: normalize(item.title),
  url: normalize(item.url),
  snippet: normalize(item.snippet)
}));

return JSON.stringify(payload);
""".strip()

    @staticmethod
    def _page_metadata_script() -> str:
        return """
const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
const payload = await page.evaluate(() => ({
  title: document.title,
  url: window.location.href
}));

payload.title = normalize(payload.title);
payload.url = normalize(payload.url);
return JSON.stringify(payload);
""".strip()

    @staticmethod
    def _page_extract_script() -> str:
        return """
const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
const payload = await page.evaluate(() => {
  const text = document.body ? document.body.innerText : '';
  return {
    title: document.title,
    url: window.location.href,
    content: text
  };
});

payload.title = normalize(payload.title);
payload.url = normalize(payload.url);
payload.content = normalize(payload.content);
return JSON.stringify(payload);
""".strip()
