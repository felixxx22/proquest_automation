import asyncio
import random
import os
import sys
from playwright.async_api import async_playwright

# --- CONFIG ---
RESULTS_URL = "https://www.proquest.com/index"
DOWNLOAD_DIR = "./nyt_pdfs_1915"

async def download(search_query):
    # if not os.path.exists(DOWNLOAD_DIR):
    #     os.makedirs(DOWNLOAD_DIR)

    async with async_playwright() as p:
        # Load your Monash session
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./monash_session",
            headless=False, # Keep it visible for the first few runs
            slow_mo=500
        )
        page = await context.new_page()
        page.set_default_timeout(60000)

        print(f"Opening: {RESULTS_URL}")
        await page.goto(RESULTS_URL)
        
        try:
            # Wait for the element to actually exist before filling
            search_box = page.locator("#searchTerm")
            await search_box.wait_for(state="visible")
            
            # CRITICAL: Added 'await' here
            await search_box.fill(search_query)
            
            # Optional: Press Enter to trigger the search
            await search_box.press("Enter")
            
            # Give the results page time to load
            await asyncio.sleep(random.uniform(5, 10))

        except Exception as e:
            print(f"Error encountered: {e}")
            await page.screenshot(path="error_debug.png")
            # await page.go_back() # Only use if you've actually moved pages

        try:
            # 1. Target the link specifically inside 'result-header-1'
            # The selector 'h3#result-header-1 a' finds the link within that header
            first_result_link = page.locator("h3#result-header-1 a").first
            
            # 2. Wait for it to be ready
            await first_result_link.wait_for(state="visible", timeout=10000)
            
            print("Clicking the first result header...")
            
            # 3. Click and wait for the document page to load
            await first_result_link.click()
            await page.wait_for_load_state("networkidle")
            
            print(f"Successfully navigated to: {page.url}")

            await asyncio.sleep(random.uniform(5, 10))

        except Exception as e:
            print(f"Could not click the first result: {e}")
            await page.screenshot(path="nav_error.png")
        
        await context.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        # testing only  
        asyncio.run(download('title("FINANCIAL MARKETS") AND stype.exact("Newspapers") AND bdl(1007155)'))

        print("Usage: python download_test.py \"<search query>\"")
        # sys.exit(1)

    else: 
        asyncio.run(download(sys.argv[1]))