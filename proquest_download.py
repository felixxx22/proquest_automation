import asyncio
import random
import re
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict
from playwright.async_api import async_playwright, Page

# --- CONFIG ---
RESULTS_URL = "https://www.proquest.com/index"
DEFAULT_DOWNLOAD_DIR = "./downloads"
DEFAULT_SESSION_DIR = "./monash_session"
DEFAULT_ENV_FILE = "./.env"
DEFAULT_ERROR_DIR = "./error_screenshots"


def log_cli(message: str):
    """Write a timestamped log line to the command line."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_env_file(env_path: str = DEFAULT_ENV_FILE):
    """Load KEY=VALUE entries from a .env file into process environment.

    Existing environment variables are not overwritten.
    """
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


async def human_delay(min_sec=1, max_sec=3):
    """Sleep for a random duration to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def get_next_start_date(download_dir: str) -> Optional[str]:
    """Determine the start date by finding the latest dated file in the download folder.

    Scans filenames matching the pattern YYYYMMDD_N.ext and returns the day
    after the most recent date found, formatted as yyyy-mm-dd.

    Args:
        download_dir: Path to the download directory to scan.

    Returns:
        str or None: The next start date as 'yyyy-mm-dd', or None if no dated files exist.
    """
    if not os.path.exists(download_dir):
        return None

    dates = []
    for filename in os.listdir(download_dir):
        match = re.match(r'(\d{8})_\d+\.\w+', filename)
        if match:
            try:
                dates.append(datetime.strptime(match.group(1), "%Y%m%d"))
            except ValueError:
                continue

    if not dates:
        return None

    next_date = max(dates) + timedelta(days=1)
    return next_date.strftime("%Y-%m-%d")


async def _is_signed_in(page: Page) -> bool:
    """Best-effort check for an authenticated My Research session.

    Some sign-in links are only rendered/visible after opening the My Research
    dropdown, so this check actively opens that menu before deciding.
    """
    # Fast checks before interacting with UI.
    if await page.locator("#central-header-login").count() > 0:
        return False
    if await page.locator("#featureLink_signInMr").count() > 0:
        return False
    if await page.locator("a.gaMRSignIn").count() > 0:
        return False

    # Open My Research dropdown and check for any sign-in affordances.
    try:
        mr_dropdown = page.locator("#mrDropdown")
        if await mr_dropdown.count() > 0:
            await mr_dropdown.first.click()
            await human_delay(0.3, 0.8)
    except Exception:
        # If menu interaction fails, continue with remaining checks.
        pass

    sign_in_in_menu = page.locator(
        "#featureLink_signInMr, a.gaMRSignIn, a[href*='/myresearch/signin']"
    )
    if await sign_in_in_menu.count() > 0:
        return False

    return True


async def _perform_research_login(page: Page, email: str, password: str) -> bool:
    """Open My Research sign-in and submit credentials."""
    print("Attempting automated My Research login...")

    # Click 1: My Research and Language Selection menu.
    mr_dropdown = page.locator("#mrDropdown")
    await mr_dropdown.wait_for(state="visible", timeout=15000)
    await mr_dropdown.click()
    await human_delay(0.5, 1.2)

    # Click 2: Sign into My Research.
    # Prefer the new modal trigger element, then fall back to visible links.
    clicked_sign_in = False

    feature_sign_in = page.locator("#featureLink_signInMr")
    if await feature_sign_in.count() > 0:
        try:
            await feature_sign_in.first.wait_for(state="visible", timeout=8000)
            await feature_sign_in.first.click()
            clicked_sign_in = True
        except Exception:
            clicked_sign_in = False

    if not clicked_sign_in:
        visible_sign_in = page.locator("a.gaMRSignIn:visible, a[href*='/myresearch/signin']:visible").first
        if await visible_sign_in.count() > 0:
            await visible_sign_in.click()
            clicked_sign_in = True

    if not clicked_sign_in:
        # Last resort: navigate directly using hidden sign-in href.
        hidden_href = await page.locator("a.gaMRSignIn, a[href*='/myresearch/signin']").first.get_attribute("href")
        if hidden_href:
            await page.goto(hidden_href)
            clicked_sign_in = True

    if not clicked_sign_in:
        raise RuntimeError("Could not find a usable 'Sign into My Research' entry.")

    # Wait for post-click navigation/modal rendering before selecting inputs.
    # Sign-in may either navigate to a new page or open an inline/modal form.
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    # Strong gate: do not continue until login UI is actually present.
    # This avoids racing on pages where DOM loaded but Auth0 widget is late.
    await page.wait_for_selector(
        "div.auth0-lock-social-button-text, input[id='1-email'], input[name='email'], .auth0-lock-input",
        state="visible",
        timeout=45000,
    )
    await human_delay(0.4, 1.0)

    # If Auth0 account picker appears for this email, use it instead of typing credentials.
    account_picker_text = page.locator("div.auth0-lock-social-button-text", has_text=email).first
    if await account_picker_text.count() > 0 and await account_picker_text.is_visible():
        print("Using existing Auth0 account picker entry...")
        account_picker_button = account_picker_text.locator("xpath=ancestor::button[1]")
        if await account_picker_button.count() > 0:
            await account_picker_button.first.click()
        else:
            await account_picker_text.click()

        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await human_delay(1, 2)
        return True

    # Wait for Auth0 fields to appear.
    username_input = page.locator("input[id='1-email'], input[name='email']").first
    password_input = page.locator("input[name='password']").first
    submit_button = page.locator("button.auth0-lock-submit").first

    await username_input.wait_for(state="visible", timeout=30000)
    await username_input.click()
    await username_input.fill("")
    await username_input.type(email, delay=random.uniform(45, 110))
    await human_delay(0.2, 0.6)

    await password_input.wait_for(state="visible", timeout=30000)
    await password_input.click()
    await password_input.fill("")
    await password_input.type(password, delay=random.uniform(45, 110))
    await human_delay(0.2, 0.6)

    await submit_button.wait_for(state="visible", timeout=30000)
    await submit_button.click()

    # Allow redirects and post-auth page loads to complete.
    await page.wait_for_load_state("networkidle")
    await human_delay(2, 4)

    # If the sign-in form is still visible, authentication likely failed.
    if await username_input.is_visible() and await password_input.is_visible():
        print("Login form is still visible after submit. Credentials may be invalid.")
        return False

    return True


async def ensure_login(page: Page, research_email: str = None, research_password: str = None):
    """Navigate to ProQuest and ensure My Research is signed in.

    Reuses persisted session when valid. If not authenticated and credentials
    are provided, performs automated login.

    Args:
        page: The Playwright page instance.
        research_email: My Research email/username.
        research_password: My Research password.

    Returns:
        bool: True if login/session is valid, False otherwise.
    """
    print(f"Opening: {RESULTS_URL}")
    try:
        await page.goto(RESULTS_URL)
        await human_delay(1, 2)

        if await _is_signed_in(page):
            print("Existing My Research session is valid.")
            return True

        # Session is not authenticated. Load .env and try automated login.
        load_env_file()
        email = research_email or os.getenv("PROQUEST_RESEARCH_EMAIL")
        password = research_password or os.getenv("PROQUEST_RESEARCH_PASSWORD")
        if not email or not password:
            print("No My Research credentials found.")
            print("Set PROQUEST_RESEARCH_EMAIL and PROQUEST_RESEARCH_PASSWORD, or pass --research-email/--research-password.")
            return False

        if not await _perform_research_login(page, email, password):
            return False

        await page.goto(RESULTS_URL, wait_until="domcontentloaded", timeout=60000)
        await human_delay(1, 2)
        if not await _is_signed_in(page):
            print("Automated login did not produce an authenticated session.")
            return False

    except Exception as e:
        print(f"Error while accessing the site: {e}")
        return False

    print("My Research login confirmed. Session persisted to disk.")
    return True


async def perform_search(page: Page, search_query: str):
    """Type a search query and submit it.

    Simulates human-like typing with random delays between keystrokes.

    Args:
        page: The Playwright page instance.
        search_query: The ProQuest search query string.
    """
    search_box = page.locator("#searchTerm")
    await search_box.wait_for(state="visible")

    await search_box.click()
    await human_delay(0.5, 1.5)
    await search_box.type(search_query, delay=random.uniform(50, 150))

    await human_delay(1, 3)
    await search_box.press("Enter")

    await human_delay(4, 8)


async def apply_date_range(page: Page, start_date: str):
    """Open the custom date range panel and apply a date filter.

    Sets the starting date to the provided value and the ending date to today.

    Args:
        page: The Playwright page instance.
        start_date: The starting date in 'yyyy-mm-dd' format.
    """
    print(f"Setting custom date range with starting date: {start_date}")

    custom_date_link = page.locator('#customDateRangeLink')
    await custom_date_link.wait_for(state="visible", timeout=10000)
    await custom_date_link.scroll_into_view_if_needed()
    await human_delay(0.5, 1.5)
    await custom_date_link.click()

    await human_delay(1, 2)

    # Fill starting date
    starting_date_input = page.locator('#startingDate')
    await starting_date_input.wait_for(state="visible", timeout=10000)
    await starting_date_input.click()
    await human_delay(0.3, 0.8)
    await starting_date_input.fill(start_date)
    print(f"Entered starting date: {start_date}")

    await human_delay(1, 2)

    # Fill ending date (today)
    ending_date_input = page.locator('#endingDate')
    await ending_date_input.wait_for(state="visible", timeout=10000)
    await ending_date_input.click()
    await human_delay(0.3, 0.8)
    today = datetime.now().strftime("%Y-%m-%d")
    await ending_date_input.fill(today)
    print(f"Entered ending date: {today}")

    await human_delay(1, 2)

    # Click Apply
    apply_button = page.locator('#dateRangeSubmit')
    await apply_button.wait_for(state="visible", timeout=10000)
    await apply_button.scroll_into_view_if_needed()
    await human_delay(0.5, 1)
    await apply_button.click()
    print("Clicked Apply button for date range")

    await page.wait_for_load_state("networkidle")
    await human_delay(5, 8)


async def sort_oldest_first(page: Page):
    """Change the sort order to 'Oldest first' using the sort combo box.

    Args:
        page: The Playwright page instance.
    """
    print("Sorting by oldest first...")

    sort_button = page.locator(
        "button[aria-controls='sortType-listbox']"
    ).or_(page.locator("#sortType"))
    await sort_button.wait_for(state="visible", timeout=10000)
    await sort_button.scroll_into_view_if_needed()
    await human_delay(0.5, 1.5)
    await sort_button.click()
    print("Opened sort dropdown")

    await human_delay(1, 2)

    oldest_first_option = page.locator('#sortType-combo-1[data-bgvalue="DateAsc"]')
    await oldest_first_option.wait_for(state="visible", timeout=5000)
    await oldest_first_option.click()
    print("Selected 'Oldest first' sorting")

    await page.wait_for_load_state("networkidle")
    await human_delay(5, 8)


async def click_first_result(page: Page):
    """Click the first search result and wait for the document page to load.

    Args:
        page: The Playwright page instance.
    """
    first_result_link = page.locator("h3#result-header-1 a").first
    await first_result_link.wait_for(state="visible", timeout=10000)

    await first_result_link.scroll_into_view_if_needed()
    await human_delay(1, 2)

    print("Clicking the first result header...")
    await first_result_link.click()
    await page.wait_for_load_state("networkidle")
    print(f"Successfully navigated to: {page.url}")

    await page.evaluate("window.scrollBy(0, 200)")
    await human_delay(8, 15)


async def extract_date_from_page(page: Page):
    """Extract the article date from the newspaperArticle element on the page.

    Parses dates in the format '11 Nov 1930' from the element text.

    Args:
        page: The Playwright page instance.

    Returns:
        str or None: The date formatted as 'YYYYMMDD', or None if extraction fails.
    """
    date_element = page.locator("span.newspaperArticle")
    date_text = await date_element.inner_text()

    date_match = re.search(r'(\d{1,2})\s+(\w{3})\s+(\d{4})', date_text)
    if not date_match:
        return None

    day = date_match.group(1).zfill(2)
    month_str = date_match.group(2)
    year = date_match.group(3)

    date_obj = datetime.strptime(f"{day} {month_str} {year}", "%d %b %Y")
    return date_obj.strftime("%Y%m%d")


def rename_downloaded_file(file_path: str, formatted_date: str, date_counter: Dict[str, int], download_dir: str) -> str:
    """Rename a downloaded file using the article date and a per-date counter.

    Files are renamed to YYYYMMDD_N.ext where N increments for each file
    sharing the same date.

    Args:
        file_path: The original path of the downloaded file.
        formatted_date: The date string in 'YYYYMMDD' format.
        date_counter: A dict tracking how many files have been saved per date.
        download_dir: Path to the download directory.

    Returns:
        str: The new filename.
    """
    if formatted_date not in date_counter:
        date_counter[formatted_date] = 0
    else:
        date_counter[formatted_date] += 1

    file_extension = os.path.splitext(file_path)[1]
    new_filename = f"{formatted_date}_{date_counter[formatted_date]}{file_extension}"
    new_file_path = os.path.join(download_dir, new_filename)

    os.rename(file_path, new_file_path)
    return new_filename


async def download_and_rename(page: Page, date_counter: Dict[str, int], download_dir: str) -> None:
    """Download the current article's PDF and rename it by article date.

    Args:
        page: The Playwright page instance.
        date_counter: A dict tracking how many files have been saved per date.
        download_dir: Path to the download directory.
    """
    # Simulate reading the document
    await human_delay(5, 10)
    await page.evaluate("window.scrollBy(0, 300)")
    await human_delay(2, 4)

    # Download the PDF
    async with page.expect_download() as download_info:
        pdf_btn = page.locator('a.pdf-download').first
        await pdf_btn.scroll_into_view_if_needed()
        await human_delay(0.5, 1.5)
        await pdf_btn.click()
        print("Download clicked...")

    download = await download_info.value
    file_path = os.path.join(download_dir, download.suggested_filename)
    await download.save_as(file_path)
    print(f"Saved: {file_path}")

    # Extract date and rename
    try:
        formatted_date = await extract_date_from_page(page)
        if formatted_date:
            new_filename = rename_downloaded_file(file_path, formatted_date, date_counter, download_dir)
            print(f"Renamed to: {new_filename}")
        else:
            print("Could not extract date, keeping original filename")
    except Exception as e:
        print(f"Error extracting/renaming file: {e}, keeping original filename")


async def navigate_to_next_record(page: Page):
    """Click the 'Next Record' link if available.

    Args:
        page: The Playwright page instance.

    Returns:
        bool: True if navigation to the next record succeeded, False if no more records.
    """
    await human_delay(3, 6)

    next_button = page.locator("a#nextLink")
    if await next_button.is_visible():
        print("Moving to next record...")
        await next_button.scroll_into_view_if_needed()
        await human_delay(0.5, 1.2)
        await next_button.click()

        await page.wait_for_load_state("networkidle", timeout=20000)
        await human_delay(2, 4)
        return True

    print("No more 'Next' links found. Finished.")
    await human_delay(3, 6)
    return False


async def _handle_suggested_sources_modal(page: Page) -> bool:
    """Close the Suggested sources modal if it is currently shown.

    Returns True when the modal is detected and handled.
    """
    modal_title = page.locator("h2#myModalLabel_suggestedSourcesModal")
    if await modal_title.count() == 0:
        return False
    if not await modal_title.first.is_visible():
        return False

    log_cli("Detected 'Suggested sources' modal. Applying modal-specific recovery...")

    checkbox = page.locator("#modalSessionChoice").first
    if await checkbox.count() > 0 and await checkbox.is_visible():
        if not await checkbox.is_checked():
            await checkbox.check()
            await human_delay(0.2, 0.5)

    close_selector = (
        "a[data-dismiss='modal'][id^='button_']:has-text('Close'), "
        "a[data-dismiss='modal'].btn.btn-default:has-text('Close')"
    )
    close_button = page.locator(close_selector).first
    if await close_button.count() > 0:
        try:
            await close_button.scroll_into_view_if_needed()
        except Exception:
            pass

        click_strategies = [
            ("normal click", lambda: close_button.click(timeout=4000)),
            ("force click", lambda: close_button.click(timeout=4000, force=True)),
            (
                "javascript click",
                lambda: close_button.evaluate("el => el.click()"),
            ),
        ]

        for strategy_name, strategy_call in click_strategies:
            try:
                log_cli(f"Attempting modal close via {strategy_name}.")
                await strategy_call()
                await human_delay(0.4, 1.0)
                if not await modal_title.first.is_visible():
                    log_cli(f"Modal close succeeded via {strategy_name}.")
                    return True
            except Exception as close_error:
                log_cli(f"Modal close failed via {strategy_name}: {close_error}")

        # Final fallback: ESC often maps to bootstrap modal close handlers.
        try:
            log_cli("Attempting modal close via Escape key fallback.")
            await page.keyboard.press("Escape")
            await human_delay(0.4, 1.0)
            if not await modal_title.first.is_visible():
                log_cli("Modal close succeeded via Escape key fallback.")
                return True
        except Exception as escape_error:
            log_cli(f"Escape key fallback failed: {escape_error}")

    return False


async def _recover_or_wait_for_user(page: Page, step_name: str, error: Exception):
    """Attempt known UI recovery, otherwise pause for manual intervention."""
    print(f"Error in '{step_name}': {error}")

    try:
        os.makedirs(DEFAULT_ERROR_DIR, exist_ok=True)
        safe_step_name = re.sub(r"[^a-zA-Z0-9_-]", "_", step_name)
        screenshot_path = os.path.join(DEFAULT_ERROR_DIR, f"error_{safe_step_name}.png")
        await page.screenshot(path=screenshot_path)
    except Exception:
        pass

    try:
        if await _handle_suggested_sources_modal(page):
            log_cli("Recovery path used: modal handled automatically; continuing.")
            return
    except Exception as modal_error:
        print(f"Modal recovery attempt failed: {modal_error}")

    log_cli("Recovery path used: manual intervention required.")
    print("Automatic recovery not available for this screen.")
    input("Please inspect/fix the page in the browser, then press Enter to continue...")
    log_cli("Manual intervention acknowledged; resuming automation.")
    await human_delay(0.5, 1.5)


async def download(
    search_query: str,
    num_files: int = 3,
    start_date: Optional[str] = None,
    output_dir: Optional[str] = None,
    research_email: Optional[str] = None,
    research_password: Optional[str] = None,
) -> None:
    """Main entry point: search ProQuest and download newspaper article PDFs.

    Launches a persistent browser session, logs in, executes a search query,
    optionally filters by date range, sorts by oldest first, then iterates
    through results downloading and renaming each PDF.

    Args:
        search_query: The ProQuest search query string.
        num_files: Maximum number of PDFs to download.
        start_date: Optional starting date filter in 'yyyy-mm-dd' format.
                    If not provided, auto-detects from existing downloads.
        output_dir: Directory to save downloaded PDFs. Defaults to './downloads'.
    """
    download_dir = output_dir or DEFAULT_DOWNLOAD_DIR

    # Auto-detect start date if not provided
    if start_date is None:
        start_date = get_next_start_date(download_dir)
        if start_date:
            print(f"Auto-detected start date (one day after latest file): {start_date}")
        else:
            print("No existing files found. Starting without date filter.")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=DEFAULT_SESSION_DIR,
            headless=False,
            slow_mo=1000,
        )
        page = await context.new_page()
        page.set_default_timeout(90000)

        # --- Login ---
        if not await ensure_login(page, research_email, research_password):
            await context.close()
            return

        # --- Search ---
        for attempt in range(2):
            try:
                await perform_search(page, search_query)
                break
            except Exception as e:
                await _recover_or_wait_for_user(page, "search", e)
                if attempt == 1:
                    print("Search still failing after recovery attempts.")
                    await context.close()
                    return

        # --- Date filter ---
        if start_date:
            try:
                await apply_date_range(page, start_date)
            except Exception as e:
                await _recover_or_wait_for_user(page, "date_range", e)
                try:
                    await apply_date_range(page, start_date)
                except Exception as retry_error:
                    print(f"Could not set custom date range after recovery: {retry_error}")

        # --- Sort ---
        try:
            await sort_oldest_first(page)
        except Exception as e:
            await _recover_or_wait_for_user(page, "sort_oldest_first", e)
            try:
                await sort_oldest_first(page)
            except Exception as retry_error:
                print(f"Could not change sort order after recovery: {retry_error}")

        # --- Open first result ---
        for attempt in range(2):
            try:
                await click_first_result(page)
                break
            except Exception as e:
                await _recover_or_wait_for_user(page, "open_first_result", e)
                if attempt == 1:
                    print("Could not click the first result after recovery attempts.")
                    await context.close()
                    return

        # --- Download loop ---
        os.makedirs(download_dir, exist_ok=True)
        date_counter = {}

        record_num = 0
        while record_num < num_files:
            try:
                print(f"Processing record {record_num + 1}...")
                await download_and_rename(page, date_counter, download_dir)

                if record_num < num_files - 1:
                    if not await navigate_to_next_record(page):
                        break
                record_num += 1
            except Exception as e:
                await _recover_or_wait_for_user(page, f"record_{record_num + 1}", e)
                # Retry same record after user/modal recovery.
                continue

        await context.close()


if __name__ == "__main__":
    load_env_file()

    parser = argparse.ArgumentParser(description='Download PDFs from ProQuest')
    parser.add_argument('search_query', type=str, help='The search query to use')
    parser.add_argument('-n', '--num-files', type=int, default=3,
                        help='Number of files to download (default: 3)')
    parser.add_argument('-d', '--start-date', type=str, default=None,
                        help='Starting date in yyyy-mm-dd format (optional, auto-detects from existing files)')
    parser.add_argument('-o', '--output-dir', type=str, default=None,
                        help='Directory to save downloaded PDFs (default: ./downloads)')
    parser.add_argument('--research-email', type=str, default=None,
                        help='My Research email. If omitted, uses PROQUEST_RESEARCH_EMAIL env var.')
    parser.add_argument('--research-password', type=str, default=None,
                        help='My Research password. If omitted, uses PROQUEST_RESEARCH_PASSWORD env var.')

    args = parser.parse_args()
    asyncio.run(
        download(
            args.search_query,
            args.num_files,
            args.start_date,
            args.output_dir,
            args.research_email,
            args.research_password,
        )
    )
