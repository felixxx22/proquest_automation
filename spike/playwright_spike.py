import asyncio
from playwright.async_api import async_playwright

async def capture_monash_auth():
    async with async_playwright() as p:
        # 'user_data_dir' is where your login 'state' is saved
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./monash_session", 
            headless=False,  # Headless MUST be False so you can see the MFA
            slow_mo=500      # Slows down actions so the site doesn't flag you
        )
        page = await context.new_page()
        
        print("Starting the Monash Handshake...")
        await page.goto("https://www.proquest.com/login")
        
        # At this point, you will manually:
        # 1. Type 'Monash University'
        # 2. Click through to the Monash SSO page
        # 3. Enter your credentials and finish MFA
        
        print("\nACTION REQUIRED:")
        print("1. In the browser, select Monash University.")
        print("2. Complete your SSO and MFA.")
        print("3. Once you see the ProQuest search dashboard, come back here.")
        
        input("\nPress ENTER in this terminal once you are fully logged in...")
        
        await context.close()
        print("Session saved to ./monash_session")

if __name__ == "__main__":
    asyncio.run(capture_monash_auth())