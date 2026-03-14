# Secondary Tool Usage - Playwright MCP

## When It's Used

The router prefers Playwright for direct page-access tasks and also uses it as the secondary backend when:

1. **Direct page open** - A single URL just needs to be loaded
2. **Direct extraction** - A page needs deterministic text extraction
3. **Main backend failed** - `browser-use` could not complete the task
4. **Main result is weak** - Content is too thin or confidence is low

## You Don't Choose It Directly

**The router decides.** Just use the normal tools and the system will pick Playwright when direct page access is the better fit.

## When It Might Be Used

- Direct URL loading
- Single-page extraction
- Fast page metadata retrieval
- Secondary path when `browser-use` underperforms

## What It Returns

Same normalized format as the main backend:

```json
{
  "status": "success",
  "backend": "playwright-mcp",
  "title": "Page Title",
  "url": "https://example.com",
  "summary": "Short summary",
  "content": "Full content...",
  "key_points": ["Point 1", "Point 2"],
  "confidence": "medium",
  "metadata": {
    "used_fallback": false,
    "reason": null
  }
}
```

## Note on Confidence

Playwright results typically have **high confidence** for direct page work because:
- deterministic page access is narrower in scope
- extraction is less agentic
- output is usually easier to validate

## Stop Conditions Apply

Even Playwright won't proceed for:
- CAPTCHA challenges
- Login walls
- Access restrictions

Returns `blocked` or `restricted` instead.
