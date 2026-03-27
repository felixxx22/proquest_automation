import asyncio
import random
import os
import sys
from playwright.async_api import async_playwright

# --- CONFIG ---
RESULTS_URL = "https://www.proquest.com/docview/98852127/7F291B4897A4013PQ/1?accountid=12528&sourcetype=Newspapers"
DOWNLOAD_DIR = "./nyt_pdfs_1915"

async def download(search_query):
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./monash_session",
            headless=False, 
            slow_mo=800 # Slightly slower to mimic human browsing
        )
        page = await context.new_page()
        page.set_default_timeout(60000)

        print(f"Opening: {RESULTS_URL}")
        await page.goto(RESULTS_URL)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # --- LOOPING LOGIC ---
        record_count = 0
        max_records = 2 # Safety limit, change as needed

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
    # Default query for testing
    query = 'title("FINANCIAL MARKETS") AND stype.exact("Newspapers")'
    if len(sys.argv) == 2:
        query = sys.argv[1]
    
    asyncio.run(download(query))