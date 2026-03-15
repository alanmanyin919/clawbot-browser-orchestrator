# Clawbot Test Instructions: Browser-Use Orchestrator (Chromium)

This guide is the **end-to-end test playbook** for Clawbot against the browser orchestrator in this repository.

> **Browser requirement**: run all browser automation tests with **Chromium**.

---

## 1) What this verifies

The test flow validates:

- API health and MCP tool discovery.
- Tool routing behavior between:
  - `better-browser-use` (main backend)
  - `playwright-mcp` (secondary backend)
- Content extraction, multi-step navigation, and blocked/restricted handling.
- Chromium/CDP connectivity used by both backends.

---

## 2) Prerequisites

- Python 3.11+
- Node.js 18+
- `pip`, `npx`, `curl`
- Chromium browser installed

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## 3) Environment setup (force Chromium)

From repo root:

```bash
cp .env.example .env
```

Then ensure these env vars are set before starting services:

```bash
# API
export MCP_PORT=3101

# Main backend (browser-use)
export LLM_PROVIDER=minimax
export MINIMAX_API_KEY="<your-key>"
export MINIMAX_BASE_URL="https://api.minimax.io/v1"
export MINIMAX_MODEL="MiniMax-M2.5"
export BROWSER_USE_MAX_STEPS=12

# Use Chromium for browser-use runtime
export CHROME_CHANNEL=chromium
export USE_EXTERNAL_BROWSER=true
export CDP_URL="http://127.0.0.1:9222"

# Secondary backend (Playwright MCP) - Chromium explicitly
export PLAYWRIGHT_MCP_COMMAND=npx
export PLAYWRIGHT_MCP_ARGS="@playwright/mcp@latest --browser chromium"
export PLAYWRIGHT_HEADLESS=true
export PLAYWRIGHT_MCP_TIMEOUT_SECONDS=45
```

Notes:

- `CHROME_CHANNEL=chromium` keeps browser-use aligned with Chromium testing.
- `PLAYWRIGHT_MCP_ARGS` includes `--browser chromium` to keep Playwright MCP on Chromium too.

---

## 4) Start a Chromium instance with CDP

Start Chromium with remote debugging on port `9222` (CDP). Example:

```bash
chromium \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/clawbot-browser \
  --no-first-run \
  --no-default-browser-check \
  --disable-dev-shm-usage \
  about:blank
```

If your environment uses a different binary name, use that equivalent Chromium binary.

Verify CDP is up:

```bash
curl -s http://127.0.0.1:9222/json/version
```

Expected: JSON response containing browser/version data.

Optional connectivity smoke test:

```bash
python3 scripts/test_cdp.py
```

Expected output includes `✅ CDP navigation test PASSED!`.

---

## 5) Start the orchestrator

In a separate shell:

```bash
python3 adapter/app.py
```

Service should listen on `http://localhost:3101` unless overridden.

---

## 6) Baseline checks

### 6.1 Health

```bash
curl -s http://localhost:3101/health | python3 -m json.tool
```

Pass criteria:

- `status` is `healthy`
- `primary` is `true`
- `fallback` is `true`

### 6.2 Tool list

```bash
curl -s http://localhost:3101/mcp/tools | python3 -m json.tool
```

Pass criteria: includes these tools:

- `web_search`
- `open_page`
- `extract_page`
- `read_top_results`
- `navigate_and_extract`

---

## 7) Functional tool matrix

Run these in order and inspect `status`, `backend`, `confidence`, `error`, and `metadata.visited_urls`.

### 7.1 `web_search` (normally browser-use first)

```bash
curl -s -X POST http://localhost:3101/tools/web_search \
  -H "Content-Type: application/json" \
  -d '{"query":"python async tutorial","max_results":5}' | python3 -m json.tool
```

Pass criteria:

- `status` is `success`
- `backend` is either `better-browser-use` or `playwright-mcp`
- content includes multiple results/snippets

### 7.2 `open_page` (Playwright-preferred)

```bash
curl -s -X POST http://localhost:3101/tools/open_page \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' | python3 -m json.tool
```

Pass criteria:

- `status` is `success`
- `backend` is typically `playwright-mcp`
- `url` is populated

### 7.3 `extract_page` (Playwright-preferred)

```bash
curl -s -X POST http://localhost:3101/tools/extract_page \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' | python3 -m json.tool
```

Pass criteria:

- `status` is `success`
- non-empty `content`
- `confidence` is present (`high|medium|low`)

### 7.4 `read_top_results` (multi-page extraction)

```bash
curl -s -X POST http://localhost:3101/tools/read_top_results \
  -H "Content-Type: application/json" \
  -d '{"query":"python dependency injection","max_results":3}' | python3 -m json.tool
```

Pass criteria:

- `status` is `success`
- `content` includes synthesis from multiple results
- `metadata.visited_urls` has multiple URLs

### 7.5 `navigate_and_extract` (task resolution confidence)

```bash
curl -s -X POST http://localhost:3101/tools/navigate_and_extract \
  -H "Content-Type: application/json" \
  -d '{"task":"Find the latest Python release shown on the homepage","url":"https://www.python.org"}' | python3 -m json.tool
```

Pass criteria:

- `status` is `success`
- `summary` reflects task completion attempt
- `confidence` is `high` when resolution is clear, otherwise `low`/fallback behavior is acceptable

---

## 8) Negative and policy tests

### 8.1 Blocked/login wall behavior

```bash
curl -s -X POST http://localhost:3101/tools/open_page \
  -H "Content-Type: application/json" \
  -d '{"url":"https://accounts.google.com/signin"}' | python3 -m json.tool
```

Expected:

- `status` may be `blocked` or `restricted`
- `error` or `summary` should indicate access/login/human-verification constraints

### 8.2 Fallback observation

Use any query/page that causes thin or failed extraction. Then verify whether response switched backend:

```bash
curl -s -X POST http://localhost:3101/tools/extract_page \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' | python3 -m json.tool
```

Check:

- `backend` value
- `metadata.used_fallback`
- `metadata.reason` (if provided)

---

## 9) Automated tests in repository

Run unit/contract tests:

```bash
python3 -m pytest tests/ -v
```

These validate schemas, router behavior, and provider wiring independent of live web results.

---

## 10) Reporting template for Clawbot test runs

For each test run, record:

1. Commit SHA tested
2. Environment values used (redact secrets)
3. Chromium/CDP status (`/json/version` response seen)
4. Command executed
5. Result fields (`status`, `backend`, `confidence`, `error`)
6. Pass/Fail decision
7. Logs/snippets for failures

---

## 11) Quick run checklist

- [ ] Dependencies installed
- [ ] Env vars set with **Chromium** (`CHROME_CHANNEL=chromium`, Playwright MCP args include `--browser chromium`)
- [ ] Chromium launched with CDP (`9222`)
- [ ] Orchestrator started (`python3 adapter/app.py`)
- [ ] `/health` and `/mcp/tools` verified
- [ ] Functional tool matrix executed
- [ ] Negative/policy tests executed
- [ ] `pytest` executed
- [ ] Test report captured
