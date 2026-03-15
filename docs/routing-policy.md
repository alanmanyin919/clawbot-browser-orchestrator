# Routing Policy

## Overview

The router chooses a preferred backend by tool type.

Current temporary policy:

- Playwright is preferred only for `open_page` and `extract_page`
- Playwright secondary fallback is disabled for `web_search`, `read_top_results`, and `navigate_and_extract`
- This restriction is intentional until the current Playwright MCP issue is resolved

## Preferred Backend By Tool

| Tool | Preferred backend | Secondary backend |
|------|-------------------|------------------|
| `web_search` | `browser-use` | none |
| `read_top_results` | `browser-use` | none |
| `navigate_and_extract` | `browser-use` | none |
| `open_page` | Playwright MCP | `browser-use` |
| `extract_page` | Playwright MCP | `browser-use` |

## Result Quality Rules

For the tools that still allow secondary routing, the router tries the secondary backend when:

- `status = "failed"`
- `confidence = "low"`
- `navigate_and_extract` cannot confirm the task outcome
- extracted content is missing
- extracted content is too thin to be useful

## Stop Conditions

The router returns blocked or restricted immediately for:

- CAPTCHA or human-verification pages
- login walls
- 403 / forbidden / access denied pages

## Practical Intent

- Use `browser-use` as the main access layer for research and multi-step browsing.
- Use Playwright for direct page opening and deterministic extraction.
- Preserve the same public API regardless of which backend answered.
