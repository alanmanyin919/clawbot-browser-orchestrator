# Main Tool Usage - browser-use

## When to Use

`browser-use` is the **default choice**. Use it for:

- Web searches
- Topic research
- Multi-page reading
- Multi-step browsing workflows
- Dynamic sites that need more adaptive interaction

## Why Primary?

- ✅ Better for research workflows
- ✅ Handles multi-step browsing
- ✅ Good default for agentic tasks
- ✅ Main access path in this project

## Router Behavior

You normally do not call `browser-use` directly.

- Use the orchestrator tool that matches the task
- The router usually sends `web_search`, `read_top_results`, and `navigate_and_extract` to `browser-use`
- If the result is weak or failed, the router may retry with Playwright

## Usage Examples

### Web Search
```python
# Search and get results
result = await router.web_search("Python tutorials")
```

### Open Page
```python
# Open a URL
result = await router.open_page("https://example.com")
```

### Extract Content
```python
# Get page content
result = await router.extract_page("https://example.com")
```

### Read Top Results
```python
# Search and read multiple sources
result = await router.read_top_results("best Python books", max_results=3)
```

### Navigate & Extract
```python
# Multi-step task
result = await router.navigate_and_extract(
    task="Find the contact form",
    url="https://example.com/contact"
)
```

## Expected Output

```json
{
  "status": "success",
  "backend": "better-browser-use",
  "title": "Page Title",
  "url": "https://example.com",
  "summary": "Short summary",
  "content": "Full content...",
  "key_points": ["Point 1", "Point 2"],
  "confidence": "high"
}
```

## When It Might Fail

- Deterministic direct page access
- Lightweight single-page extraction
- Sites where a simple page load is enough

**That's okay** - the router will automatically try Playwright when a direct page-access path is better.
