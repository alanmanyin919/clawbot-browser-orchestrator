# Known Test Issues

## Issue 1: read_top_results Falls Back to Playwright MCP

### Symptom
When running `read_top_results`, the primary browser-use sometimes fails and falls back to Playwright MCP, which throws:
```
"unhandled errors in a TaskGroup (1 sub-exception)"
```

### Root Cause
- Playwright MCP integration has a compatibility issue with the current environment
- The error appears to be related to asyncio TaskGroup handling in the MCP server

### Impact
- `read_top_results` fails when fallback is triggered
- Other tools that use Playwright as secondary also fail

### Workaround
- browser-use (primary) works correctly
- The issue only affects fallback scenarios

---

## Issue 2: Blocked/Login Pages Return Empty Error

### Symptom
When accessing blocked pages (e.g., Google sign-in), the response has:
```json
{
  "status": "failed",
  "error": "",
  "confidence": "low"
}
```

Expected:
```json
{
  "status": "blocked",
  "error": "Login required to access this content"
}
```

### Root Cause
- The orchestrator is not properly detecting login walls/CAPTCHA
- browser-use returns empty error when it encounters authentication pages
- The stop condition detection logic needs improvement

### Impact
- Blocked pages are not properly identified
- Clients cannot distinguish between failed requests and restricted access

### Workaround
- Manual inspection of `visited_urls` can reveal if a login page was visited

---

## Status: Needs Evaluation

These issues require evaluation to determine:
1. Priority of fixing Playwright MCP vs. relying on browser-use only
2. How to improve blocked/restricted detection
