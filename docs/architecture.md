# Architecture

## Overview

The Browser Orchestrator provides a unified browser automation interface for agents and automation clients.

```text
Agent / LLM / Client
  -> MCP Tool Interface
  -> Router Layer
     -> Main backend: browser-use
     -> Secondary backend: Playwright MCP
  -> Normalized Output
```

## Backend Roles

### Main backend: `browser-use`
- Default path for `web_search`
- Default path for `read_top_results`
- Default path for `navigate_and_extract`
- Best fit for research and multi-step browsing

### Secondary backend: Playwright MCP
- Preferred path for `open_page`
- Preferred path for `extract_page`
- Best fit for deterministic single-page access
- Used as the secondary backend when the main backend result is weak or unsuitable

## Router Behavior

The router in [adapter/router.py](../adapter/router.py):

- chooses the preferred backend based on tool type
- checks result quality and stop conditions
- retries the same tool on the secondary backend when needed
- normalizes both backends into the same `BrowserResult` shape

## Data Flow

1. Request arrives at the FastAPI app.
2. Router selects the preferred backend for that tool.
3. Preferred backend executes.
4. Router checks for blocked/restricted conditions.
5. If the result is thin, low-confidence, or failed, router tries the secondary backend.
6. The final normalized result is returned to the caller.

## Configuration

- `config/browser-policy.yaml` controls backend settings and stop conditions
- `config/app-config.yaml` controls app/logging settings
- `.env` provides runtime credentials and backend parameters
