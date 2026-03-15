# Onboarding Guide

## Start Here

Use this document as the entry point for a new Clawbot or operator working with the browser orchestrator.

The goal is simple:

1. Understand what the orchestrator does
2. Know which document to open next
3. Follow the correct action for the current situation

## What The Orchestrator Is

The orchestrator is the control layer between Clawbot and the browser backends.

- Clawbot chooses a browser tool
- The orchestrator routes the request
- `browser-use` handles search, research, and multi-step browsing
- Playwright handles direct page open and extraction
- The final result is returned in one normalized response shape

For the architecture overview, read:

- [architecture.md](./architecture.md)
- [routing-policy.md](./routing-policy.md)

## If You Are New

Read these in order:

1. [README.md](../README.md)
2. [setup.md](./setup.md)
3. [architecture.md](./architecture.md)
4. [routing-policy.md](./routing-policy.md)
5. [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)

## Situation-Based Navigation

### I need to run the orchestrator locally

Open:

- [setup.md](./setup.md)
- [README.md](../README.md)

### I want to understand the request workflow

Open:

- [architecture.md](./architecture.md)
- [routing-policy.md](./routing-policy.md)
- [adapter/app.py](../adapter/app.py)
- [adapter/router.py](../adapter/router.py)

### I want to know how Clawbot should use the tools

Open:

- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)
- [primary-tool-usage.md](../prompts/primary-tool-usage.md)
- [fallback-tool-usage.md](../prompts/fallback-tool-usage.md)

### I want to test whether browser-use works

Open:

- [browser-use-testing.md](../prompts/browser-use-testing.md)
- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)
- [troubleshooting.md](./troubleshooting.md)

### I am using external browser mode

Open:

- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)
- [setup.md](./setup.md)

Important rule:

- If using external browser mode, start local Chrome or Chromium with CDP on port `9222`, then let the orchestrator connect to it.

### I am running inside a container

Open:

- [browser-use-testing.md](../prompts/browser-use-testing.md)
- [setup.md](./setup.md)

Important rule:

- Start Chromium with remote debugging enabled and expose port `9222`.

### A login page or CAPTCHA appears

Open:

- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)
- [troubleshooting.md](./troubleshooting.md)

Important rule:

- Stop automation
- Keep the browser session open if possible
- Ask the human to complete credentials or verification in the UI
- Resume only after the human confirms completion

### I need to inspect what Clawbot did

Open:

- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)

Important rule:

- Local activity logs should be written under `logs/`
- Recommended file: `logs/clawbot-activity.log`
- These logs are local-only and must not be committed

### A test failed and I need known issues

Open:

- [TEST_ISSUES.md](./TEST_ISSUES.md)
- [troubleshooting.md](./troubleshooting.md)

## Current Operational Rules

- `browser-use` is the main backend for `web_search`, `read_top_results`, and `navigate_and_extract`
- Playwright is preferred for `open_page` and `extract_page`
- Playwright secondary fallback is currently disabled for the search/research tools until the MCP issue is resolved

## Suggested Reading By Role

### For operators

- [setup.md](./setup.md)
- [troubleshooting.md](./troubleshooting.md)
- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)

### For developers

- [architecture.md](./architecture.md)
- [routing-policy.md](./routing-policy.md)
- [adapter/router.py](../adapter/router.py)
- [adapter/services/browser_use.py](../adapter/services/browser_use.py)
- [adapter/services/playwright_primary.py](../adapter/services/playwright_primary.py)

### For Clawbot prompt maintenance

- [clawbot-browser-policy.md](../prompts/clawbot-browser-policy.md)
- [primary-tool-usage.md](../prompts/primary-tool-usage.md)
- [fallback-tool-usage.md](../prompts/fallback-tool-usage.md)
- [browser-use-testing.md](../prompts/browser-use-testing.md)
