import os
import asyncio

async def run(page):
    print("Starting AURA Campus UI tests...")
    
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    
    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        url = os.environ.get("AURA_URL", "http://localhost:3000")
        print(f"Navigating to {url}")
        await page.goto(url, timeout=30000)
        
        # Wait for network idle or app container
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # Check title or any text
        print("Page title:", await page.title())
        
        # Take a screenshot to inspect
        await page.screenshot(path="/app/test_reports/debug_screenshot.png", quality=40, full_page=False)
        print("Saved debug screenshot")

    except Exception as e:
        print(f"Error during AURA UI test execution: {str(e)}")
        raise e
