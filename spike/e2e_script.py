import asyncio
import random
import os
import sys
from playwright.async_api import async_playwright

# --- CONFIG ---
RESULTS_URL = "https://www.proquest.com/index"
DOWNLOAD_DIR = "./spike_downloads"

async def download(search_query):
    # if not os.path.exists(DOWNLOAD_DIR):
    #     os.makedirs(DOWNLOAD_DIR)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./monash_session",
            headless=False, # Keep it visible for the first few runs
            slow_mo=500
        )
        page = await context.new_page()
        page.set_default_timeout(60000)

        print(f"Opening: {RESULTS_URL}")
        try:
            await page.goto(RESULTS_URL)

            # Check if the session is valid by looking for the login button
            if await page.locator("#central-header-login").is_visible():
                print("Session details are invalid. Please sign in.")
                input("Press Enter after signing in to continue...")

                # Reload the page after the user signs in
                await page.reload()

                # Verify again if the session is valid
                if await page.locator("#central-header-login").is_visible():
                    print("Sign-in failed. Exiting.")
                    return

        except Exception as e:
            print(f"Error while accessing the site: {e}")
            return

        try:
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
        
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # --- LOOPING LOGIC ---
        record_count = 0
        max_records = 3 # Safety limit, change as needed

        while record_count < max_records:
            try:            
                print(f"Processing record {record_count + 1}...")
                await asyncio.sleep(random.uniform(3, 6)) # Anti-bot breathing room

                # 1. Start the download expectation
                async with page.expect_download() as download_info:
                    # Locate the PDF download button
                    pdf_btn = page.locator('a.pdf-download').first
                    await pdf_btn.click()
                    print("Download clicked...")

                # 2. Handle the file
                download = await download_info.value
                file_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                await download.save_as(file_path)
                print(f"Saved: {file_path}")

                # 3. Logic to click "Next Record"
                next_button = page.locator("a#nextLink")
                
                # Check if 'Next' exists and is visible
                if await next_button.is_visible():
                    print("Moving to next record...")
                    await next_button.click()

                    await asyncio.sleep(random.uniform(3, 6)) # Anti-bot breathing room

                    # Wait for the next page to actually load its content
                    await page.wait_for_load_state("networkidle")
                    record_count += 1

                else:
                    print("No more 'Next' links found. Finished.")
                    await asyncio.sleep(random.uniform(3, 6)) # Anti-bot breathing room

                    break

            except Exception as e:
                print(f"Error encountered: {e}")
                await page.screenshot(path=f"error_record_{record_count}.png")
                break # Exit loop on major error

        await context.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        # testing only  
        asyncio.run(download('title("FINANCIAL MARKETS") AND stype.exact("Newspapers") AND bdl(1007155)'))

        print("Usage: python download_test.py \"<search query>\"")
        # sys.exit(1)

    else: 
        asyncio.run(download(sys.argv[1]))