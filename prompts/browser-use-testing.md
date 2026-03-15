# Browser-Use Testing Prompt

## Purpose

Use this prompt when an agent or operator needs to verify whether `browser-use` is working correctly.

Do not jump straight to Google or to a site-specific conclusion. Test in stages so the failure can be classified correctly.

## Linked Documents

- Entry point: [docs/onboarding.md](../docs/onboarding.md)
- Main operating policy: [clawbot-browser-policy.md](./clawbot-browser-policy.md)
- Primary backend usage: [primary-tool-usage.md](./primary-tool-usage.md)
- Troubleshooting: [docs/troubleshooting.md](../docs/troubleshooting.md)
- Known issues: [docs/TEST_ISSUES.md](../docs/TEST_ISSUES.md)

## Test In This Order

1. Browser startup or external browser availability
2. CDP reachability
3. Direct navigation to a safe page
4. `browser-use` on a simple safe task
5. Real search workflow such as Google

## External Browser Mode

If using external browser mode:

- Start local Chrome or Chromium with CDP on port `9222`
- Then let the orchestrator connect to it
- Do not claim browser automation is broken until CDP is reachable

Basic check:

```bash
curl http://127.0.0.1:9222/json/version
```

## Container Mode

If running inside a container:

- Start Chromium with remote debugging enabled
- Bind the debug address so the orchestrator can reach it
- Expose port `9222`

Example:

```bash
chromium \
  --headless=new \
  --remote-debugging-address=0.0.0.0 \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chromium-profile \
  --no-sandbox \
  --disable-dev-shm-usage \
  --no-first-run \
  --no-default-browser-check \
  about:blank
```

## Recommended Test Sequence

### Step 1: CDP Reachability

Check:

```bash
curl http://127.0.0.1:9222/json/version
```

If this fails:

- classify as `CDP failure`
- stop

### Step 2: Direct Browser Navigation

Use a simple page such as:

- `https://example.com`

If this fails:

- classify as `browser/network failure`
- do not blame Google

### Step 3: browser-use Basic Task

Use `browser-use` on a low-risk task:

- open `https://example.com`
- return the page title and a short visible summary

If this fails due to malformed JSON, `<think>` pollution, or provider output mismatch:

- classify as `LLM/provider failure`

### Step 4: Search Workflow

Only after the earlier steps succeed, test:

- `web_search("OpenAI latest news")`

If this fails but simple pages worked:

- classify as `site-specific block`

If this fails and simple pages also failed:

- classify as `environment/network policy issue`

## Login And CAPTCHA Handling

If a login page or CAPTCHA appears:

1. Stop automated actions immediately
2. Keep the browser session open if possible
3. Ask the operator to complete credentials or verification directly in the UI
4. Resume only after the operator confirms completion

Do not try to bypass credentials, CAPTCHA, or human verification.

## Local Logging

When testing, write a local operator-readable activity log:

- Directory: `logs/`
- Recommended file: `logs/agent-activity.log`
- Do not commit these logs

Each entry should include:

1. Timestamp
2. Test step
3. Tool or command used
4. Target URL or query
5. Observed result
6. Final classification

## Classification Labels

Use these labels consistently:

- `CDP failure`
- `browser/network failure`
- `LLM/provider failure`
- `site-specific block`
- `environment/network policy issue`

## Reporting Format

When reporting a test result, include:

1. Which step failed
2. What was executed
3. What evidence was observed
4. What category the failure belongs to
