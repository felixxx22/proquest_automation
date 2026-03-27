# ProQuest Scraper

[![Tests](https://github.com/yourusername/proquest_scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/proquest_scraper/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

Automatically download newspaper articles from ProQuest without manual login prompts.

## Overview

This tool automates the process of searching ProQuest, logging in, and downloading newspaper PDF articles. Instead of manually clicking through login screens every time, you set up your credentials once, and the script handles everything automatically.

### Key Features

- **Automated Login**: Handles ProQuest My Research authentication with persistent session storage
- **Intelligent Retry**: Automatic recovery from modal dialogs and UI hiccups with manual intervention fallback
- **Human-like Behavior**: Random delays and realistic typing to avoid detection
- **Smart Renaming**: PDFs automatically renamed by publication date (YYYYMMDD_N format)
- **Date Filtering**: Search within custom date ranges; auto-detects where previous downloads ended
- **Async Performance**: Fast parallel page operations using Playwright's async API
- **Error Logging**: Captures screenshots and detailed logs when issues occur

## Prerequisites

You need to have Python installed on your computer. This was tested with Python 3.7+.

### Check If Python Is Installed

Open a terminal or command prompt and type:
```
python --version
```

If you see a version number like `Python 3.x.x`, you're good. If not, [download Python here](https://www.python.org/downloads/).

## Setup (One Time Only)

### Step 1: Create a `.env` File

In the project folder, you'll see a `.env` file. Open it with a text editor and add your ProQuest My Research credentials:

```
PROQUEST_RESEARCH_EMAIL=your_email@example.com
PROQUEST_RESEARCH_PASSWORD=your_password
```

**Save the file.** This file is never shared or uploaded—it's only used locally by your computer.

### Step 2: Install Dependencies

Open a terminal in the project folder and run:

```
pip install -r requirements.txt
```

This downloads the libraries the script needs (mainly Playwright for browser automation).

## Running the Script

### Basic Usage

Open a terminal in the project folder and run:

```
python proquest_download.py "your search query" -n 5
```

### Run With a Parameter File (Recommended)

Edit `run_params.psd1` with your query and options, then run:

```
.\run_from_params.ps1
```

You can also pass a different config file:

```
.\run_from_params.ps1 -ConfigPath .\my_params.psd1
```

Replace:
- `"your search query"` with what you want to search for (examples: `"stock market"`, `"financial news"`)
- `5` with how many PDFs you want to download

**Example:**
```
python proquest_download.py "FINANCIAL MARKETS AND NEWSPAPERS" -n 10
```

### What Happens

1. A browser window opens (do not close it).
2. The script logs in automatically using your `.env` credentials.
3. It searches ProQuest for your query.
4. It downloads PDFs and saves them to the `downloads/` folder.
5. Each PDF is renamed with its publication date.

**The browser window will stay open.** You can watch the automation happen, or just leave it running in the background.

### Advanced Options

#### Start From a Specific Date

Download articles only after a certain date:

```
python proquest_download.py "your query" -n 5 -d 2023-01-01
```

#### Save to a Different Folder

```
python proquest_download.py "your query" -n 5 -o C:\MyFolder\Articles
```

#### Pass Credentials via Command Line (Instead of `.env`)

```
python proquest_download.py "your query" --research-email your@email.com --research-password your_password
```

## Where Are My Downloaded Files?

By default, PDFs are saved to:
- **Windows:** `C:\Users\YourUsername\Documents\Projects\proquest_scraper\downloads\`
- **Mac/Linux:** `./downloads/`

## Architecture

```
proquest_download.py
├── Authentication (Auth0 via My Research)
├── Search & Filtering (Date ranges, sorting)
├── Download Loop
│   ├── Article retrieval
│   ├── PDF download
│   └── Smart renaming
└── Error Recovery (Modal handling, screenshots)
```

### Key Components

| Function | Purpose |
|----------|---------|
| `ensure_login()` | Handles ProQuest authentication with session persistence |
| `perform_search()` | Executes search query with human-like typing delays |
| `apply_date_range()` | Filters results by custom date range |
| `download_and_rename()` | Downloads PDF and renames by article publication date |
| `_handle_suggested_sources_modal()` | Auto-closes common UI modals |
| `_recover_or_wait_for_user()` | Graceful error recovery with manual intervention option |

## Advanced Usage

### Integration with Scripts

```python
import asyncio
from proquest_download import download

asyncio.run(download(
    search_query="financial markets",
    num_files=50,
    start_date="2023-01-01",
    output_dir="./my_articles"
))
```

## Troubleshooting

### Login Failures
- Verify credentials in `.env` file
- Check if your ProQuest account is active
- Try clearing the `monash_session/` folder to reset browser state

### "No more 'Next' links found"
- This is normal when you've reached the end of search results
- Adjust your search query or date range for more results

### Stuck on Modal Dialog
- If manual recovery is required, inspect the browser window
- Look for dialog boxes or unexpected UI elements
- Press Enter in the terminal to continue

### Files Not Downloading
- Ensure PDFs aren't blocked by browser security settings
- Check download folder permissions
- Increase timeout values if ProQuest is slow (edit `slow_mo=1000` in code)

## Known Limitations

- Requires an active ProQuest My Research account
- Date extraction depends on article metadata formatting
- ProQuest layout changes may require selector updates
- High-volume downloads may trigger rate limiting

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is provided for educational and personal research purposes. Ensure compliance with ProQuest's terms of service and institutional policies before use.

Each file is named with the article's publication date: `YYYYMMDD_#.pdf`
- Example: `20230115_1.pdf` = January 15, 2023, first article

## Troubleshooting

### "No My Research credentials found"

Make sure your `.env` file exists and contains both `PROQUEST_RESEARCH_EMAIL` and `PROQUEST_RESEARCH_PASSWORD`.

### Browser Window Opens But Nothing Happens

Open your web browser and manually go to ProQuest. Log in with your credentials. The script will start working once it detects you're logged in.

### Modal Dialog / "Suggested sources" Appears

Sometimes ProQuest shows a popup. The script tries to close it automatically:
1. If automatic closure fails, you'll see a prompt in the terminal: `"Please inspect/fix the page in the browser, then press Enter to continue..."`
2. Simply click the "Close" button on the popup, then press Enter in the terminal.

### Downloads Seem Slow

That's intentional! The script pauses between actions to mimic human behavior and avoid triggering anti-bot protections. Expect 5-30 seconds per article depending on file sizes.

### Error Files Saved

If something goes wrong, screenshots of the error are saved to `error_screenshots/` folder. These help diagnose what went wrong.

## Session Persistence

After the first successful login, your session is saved. The next time you run the script:
- It will **not** prompt for login again (faster!)
- If your session expires, it will log in automatically using your `.env` credentials

To clear the saved session, delete the `monash_session/` folder.

## Tips for Best Results

1. **Start with a small number:** Try `-n 3` first to make sure everything works.
2. **Use specific search queries:** The more specific, the better. Avoid very broad searches.
3. **Run during off-hours if possible:** ProQuest may have fewer anti-bot triggers at night.
4. **Keep your `.env` file safe:** Never share it or commit it to version control.
5. **Don't close the browser window while the script runs:** Let it finish naturally.

## Still Stuck?

Check the terminal output! The script prints detailed messages about what it's doing. If there are error messages, they usually tell you exactly what went wrong.

If you see timestamped logs like `[2026-03-23 14:30:45]`, those are tracking recovery attempts:
- `"modal handled automatically"` = good, it fixed a popup
- `"manual intervention required"` = you need to fix something in the browser, then press Enter
- `"resuming automation"` = it's continuing after your fix

Enjoy downloading!
