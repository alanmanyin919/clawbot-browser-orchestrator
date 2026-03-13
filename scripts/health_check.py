#!/usr/bin/env python3
"""Health check for external browser and CDP."""
import asyncio
import sys
import json
import urllib.request

async def check_cdp_health():
    """Check if CDP browser is available and responsive."""
    cdp_url = "http://127.0.0.1:9222"
    results = {
        "cdp_endpoint": False,
        "browser_version": None,
        "websocket_url": None,
        "playwright_connect": False,
        "navigation_test": False,
    }
    
    # Check 1: CDP endpoint responds
    print("Checking CDP endpoint...")
    try:
        with urllib.request.urlopen(f"{cdp_url}/json/version", timeout=5) as response:
            data = json.loads(response.read().decode())
            results["cdp_endpoint"] = True
            results["browser_version"] = data.get("Browser")
            results["websocket_url"] = data.get("webSocketDebuggerUrl")
            print(f"  ✅ CDP endpoint OK: {results['browser_version']}")
    except Exception as e:
        print(f"  ❌ CDP endpoint failed: {e}")
        return results
    
    # Check 2: Playwright can connect
    print("Checking Playwright CDP connection...")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            results["playwright_connect"] = True
            print("  ✅ Playwright connects via CDP")
            
            # Check 3: Navigation works
            print("Testing navigation...")
            page = await browser.new_page()
            await page.goto("https://example.com")
            title = await page.title()
            if title:
                results["navigation_test"] = True
                print(f"  ✅ Navigation OK: '{title}'")
            await page.close()
            await browser.close()
    except Exception as e:
        print(f"  ❌ Playwright connection failed: {e}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(check_cdp_health())
    
    # Summary
    all_ok = all([
        results["cdp_endpoint"],
        results["playwright_connect"],
        results["navigation_test"]
    ])
    
    print("\n" + "="*40)
    print("HEALTH CHECK SUMMARY")
    print("="*40)
    print(f"CDP Endpoint:       {'✅' if results['cdp_endpoint'] else '❌'}")
    print(f"Playwright Connect: {'✅' if results['playwright_connect'] else '❌'}")
    print(f"Navigation Test:    {'✅' if results['navigation_test'] else '❌'}")
    print("="*40)
    
    if all_ok:
        print("🎉 All checks PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some checks FAILED")
        sys.exit(1)
