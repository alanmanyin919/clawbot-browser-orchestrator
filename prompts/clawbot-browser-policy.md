# Clawbot Browser Policy

## For Clawbot/LLM Agents

When you need browser automation, use this orchestrator.

## How The Orchestrator Works

1. Choose the tool that matches the user task.
2. The orchestrator routes the request to the preferred backend.
3. `browser-use` is the main backend for search, research, and multi-step browsing.
4. Playwright is preferred for direct page open and extraction tasks.
5. If the first result is failed, thin, or low-confidence, the router may try the other backend.
6. If a page is blocked, restricted, or requires login/CAPTCHA, stop and report that clearly.

## Tool Selection Guide

| Task | Use Tool |
|------|----------|
| Find information online | `web_search` |
| Visit a specific page | `open_page` |
| Get page content | `extract_page` |
| Research a topic | `read_top_results` |
| Complex navigation | `navigate_and_extract` |

## Important Rules

1. **Try simple tools first** - `web_search` is usually enough
2. **Main backend is browser-use** - it handles most research and workflow tasks
3. **Playwright is for direct page access** - the router prefers it for `open_page` and `extract_page`
4. **Do not choose backends manually in normal use** - call the tool, let the router decide
5. **Respect blocks** - If blocked, stop and report

## Local External Browser Mode

If using external browser mode, start local Chrome with CDP on port `9222`, then let the orchestrator connect to it.

## Don't

- Don't try to bypass CAPTCHA
- Don't try to bypass login walls
- Don't scrape restricted content
- Don't hammer the same site

## Response Format

All tools return:
```json
{
  "status": "success | failed | blocked | restricted",
  "backend": "playwright-mcp | better-browser-use",
  "title": "...",
  "url": "...",
  "summary": "...",
  "content": "...",
  "key_points": [...],
  "confidence": "high | medium | low",
  "error": "..."
}
```

## Interpretation Rules

- `success`: useful result returned
- `failed`: backend could not complete the task
- `blocked`: CAPTCHA, login wall, or human verification stopped the run
- `restricted`: access denied, forbidden page, or similar restriction
- `confidence`: use this to judge how trustworthy or complete the result is
- `backend`: shows which backend produced the final answer

## Example Usage

**Simple search:**
```
web_search(query="best Python frameworks 2024")
```

**Research topic:**
```
read_top_results(query="Python async programming", max_results=5)
```

**Get specific page:**
```
open_page(url="https://docs.python.org/3/")
```

**Complex workflow:**
```
navigate_and_extract(
  task="Find the pricing page and summarize the main plan differences",
  url="https://example.com"
)
```
