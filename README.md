# Clawbot Browser Orchestrator

Browser orchestration layer for Clawbot/OpenClaw. This service exposes a single MCP-style HTTP surface and routes browser tasks between a main `browser-use` backend and a secondary Playwright MCP backend for direct page access.[1][2]

## Status

This repository now includes concrete backend integrations, but they depend on local runtime configuration:

- The FastAPI service, router, schemas, config, prompts, and tests are present.
- The main backend runs `browser-use` in-process with an OpenAI-compatible model configuration.
- The secondary backend starts a local Playwright MCP process over stdio per request.
- The shell scripts are still lightweight helpers; real execution now depends on the environment variables documented below.

If you use this repo today, treat it as a documented starter project rather than a production-ready browser automation gateway.

## What This Project Does

The orchestrator gives Clawbot a consistent interface for browser actions:

```text
Clawbot / LLM
  -> Browser Orchestrator API
  -> Router
     -> Main: browser-use
     -> Secondary: Playwright MCP
  -> Normalized BrowserResult
```

Core goals:

- Prefer an agentic browser backend for search, research, and multi-step tasks.
- Use Playwright for deterministic single-page access and extraction.
- Return a normalized result shape regardless of backend.
- Keep routing rules, stop conditions, and prompts in repo-managed config/docs.

## Current API Surface

The FastAPI app in [adapter/app.py](adapter/app.py) exposes:

- `POST /tools/web_search`
- `POST /tools/open_page`
- `POST /tools/extract_page`
- `POST /tools/read_top_results`
- `POST /tools/navigate_and_extract`
- `GET /health`
- `GET /mcp/tools`

The normalized response model lives in [adapter/schemas.py](adapter/schemas.py).

## Repository Layout

```text
clawbot-browser-orchestrator/
├── adapter/              # FastAPI app, router, schemas, service wrappers
├── config/               # Routing policy, app config, MCP config
├── docs/                 # Setup, architecture, routing, troubleshooting
├── prompts/              # Backend usage guidance for the agent
├── scripts/              # Local start and health scripts
├── tests/                # Schema/router tests and demo task notes
├── requirements.txt
└── package.json
```

## Local Setup

### Requirements

- Python 3.11+
- Node.js 18+
- A `browser-use` runtime[2]
- A Playwright MCP runtime[1]

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.example .env
```

### Run the orchestrator

```bash
python3 adapter/app.py
```

Default port: `3101`

### Optional local helper scripts

```bash
./scripts/start_primary.sh
./scripts/start_fallback.sh
./scripts/start_all.sh
./scripts/healthcheck.sh
```

Important: the app now runs `browser-use` as the main execution path for search and workflow tasks, and starts Playwright MCP internally for direct page access.

## Suggested Upstream Integration Targets

### Secondary backend: Playwright MCP

The current docs in the upstream Playwright MCP repository show the standard MCP config using `npx @playwright/mcp@latest`.[1]

Example:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

### Main backend: browser-use

The upstream `browser-use` project documents Python 3.11+, installation via `uv add browser-use`, and optional browser installation with `uvx browser-use install`.[2]

This repository uses `browser-use` as the main access layer for search, research, and multi-step tasks.

## Configuration

Main config files:

- [config/browser-policy.yaml](config/browser-policy.yaml): main/secondary backend names, timeouts, triggers, stop conditions
- [config/app-config.yaml](config/app-config.yaml): app-level settings
- [config/mcp.json](config/mcp.json): MCP-related config stub

Common runtime environment variables:

- `MCP_PORT` defaults to `3101`
- `PLAYWRIGHT_MCP_COMMAND` defaults to `npx`
- `PLAYWRIGHT_MCP_ARGS` defaults to `@playwright/mcp@latest`
- `PLAYWRIGHT_MCP_TIMEOUT_SECONDS` defaults to `45`
- `PLAYWRIGHT_HEADLESS` defaults to `true`
- `LLM_PROVIDER` defaults to `minimax`
- `MINIMAX_API_KEY` must be set for the main browser-use backend
- `MINIMAX_BASE_URL` defaults to `https://api.minimax.io/v1`
- `MINIMAX_MODEL` defaults to `MiniMax-M2.5`
- `MINIMAX_TIMEOUT_SECONDS` defaults to `90`
- `MINIMAX_MAX_RETRIES` defaults to `2`
- `BROWSER_USE_MAX_STEPS` defaults to `12`

## MiniMax Provider Wiring

The browser-use integration uses a small provider factory in `adapter/llm_factory.py` and constructs MiniMax through its OpenAI-compatible API. The project does not use browser-use cloud and does not monkey-patch `ChatOpenAI` objects.

Quick start:

```bash
cp .env.example .env
python3 adapter/app.py
```

Smoke-check the MiniMax wiring:

```bash
python3 scripts/smoke_minimax.py
```

## Documentation

- [docs/setup.md](docs/setup.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/routing-policy.md](docs/routing-policy.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [tests/demo_tasks.md](tests/demo_tasks.md) (Clawbot Chromium test instructions)

## Next Implementation Steps

To turn this scaffold into a working service:

1. Add end-to-end tests against live MiniMax-backed `browser-use` and Playwright MCP.
2. Decide whether to keep the code name `better-browser-use` or rename the backend label to `browser-use` consistently.
3. Refine per-tool routing rules if some direct-page tasks should always bypass `browser-use`.

## Citations

[1] Microsoft, "Playwright MCP", GitHub repository and setup documentation: https://github.com/microsoft/playwright-mcp

[2] browser-use, "browser-use", GitHub repository and quickstart documentation: https://github.com/browser-use/browser-use
