# Agent Browser Policy

## For Agents And LLM Clients

When you need browser automation, use this orchestrator.

## Navigation

Use these documents depending on the situation:

- New operator or new agent entry point: [docs/onboarding.md](../docs/onboarding.md)
- How the system works: [docs/architecture.md](../docs/architecture.md)
- Routing behavior: [docs/routing-policy.md](../docs/routing-policy.md)
- How to test `browser-use`: [browser-use-testing.md](./browser-use-testing.md)
- Troubleshooting: [docs/troubleshooting.md](../docs/troubleshooting.md)

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

## Local Activity Logging

When testing or debugging, write a local activity log on the orchestrator host so operators can inspect what happened later.

- Store logs under `logs/`
- Recommended file: `logs/agent-activity.log`
- These logs are local-only and should not be committed to git

Each log entry should include:

1. Timestamp
2. Tool or workflow being run
3. Target URL or query
4. Key action taken
5. Result status
6. Error or stop reason, if any

## Login Page Handling

If a login page is reached:

1. Stop automated actions immediately.
2. Keep the current browser session open if possible.
3. Report clearly that human login is required.
4. Ask the operator to complete the credential entry and any required verification directly in the browser UI.
5. Resume testing only after the human confirms login is complete.

Do not attempt to guess, autofill, bypass, or brute-force credentials.

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
