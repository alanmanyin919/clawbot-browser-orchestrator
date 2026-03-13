#!/usr/bin/env python3
"""Test CDP connection and navigation."""
import asyncio
from playwright.async_api import async_playwright

async def test_cdp_connection():
    print("Testing CDP connection to existing browser...")
    
    async with async_playwright() as p:
        # Connect to existing browser via CDP
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        
        print("Connected to browser!")
        
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to example.com
        print("Navigating to https://example.com...")
        await page.goto("https://example.com")
        
        # Get title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Get content
        content = await page.content()
        print(f"Content length: {len(content)} chars")
        
        await page.close()
        await browser.close()
        
        print("✅ CDP navigation test PASSED!")
        return True

if __name__ == "__main__":
    asyncio.run(test_cdp_connection())
