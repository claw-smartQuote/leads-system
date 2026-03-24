---
name: browser-automation
description: Control and automate web browser for web scraping, form filling, screenshots, and page interactions. Use when the user needs to (1) Open and navigate websites, (2) Take screenshots of web pages, (3) Fill forms and click buttons, (4) Extract data from websites, (5) Automate web workflows, (6) Login to websites, (7) Download files from web pages, or (8) Monitor web page changes.
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "config": ["browser.enabled"] },
      },
  }
---

# Browser Automation

Automate web browser tasks using OpenClaw's built-in browser control.

## Quick Start

### Open a website

```bash
python3 {baseDir}/scripts/browser_helper.py open https://example.com
```

### Take a screenshot

```bash
python3 {baseDir}/scripts/browser_helper.py screenshot --output page.png
```

### Get page content

```bash
python3 {baseDir}/scripts/browser_helper.py content
```

### Full workflow example

```bash
# Open site, login, and screenshot
python3 {baseDir}/scripts/browser_helper.py open https://example.com
python3 {baseDir}/scripts/browser_helper.py snapshot
# Use the ref numbers from snapshot to interact
python3 {baseDir}/scripts/browser_helper.py click 12
python3 {baseDir}/scripts/browser_helper.py type 15 "username"
python3 {baseDir}/scripts/browser_helper.py screenshot --output result.png
```

## Commands

| Command | Description |
|---------|-------------|
| `open <url>` | Navigate to a URL |
| `status` | Check browser status |
| `start` | Start browser if not running |
| `stop` | Stop browser |
| `tabs` | List all tabs |
| `screenshot` | Take screenshot |
| `snapshot` | Get interactive page snapshot with refs |
| `content` | Get page text content |
| `click <ref>` | Click element by ref number |
| `type <ref> <text>` | Type text into input field |
| `scroll` | Scroll page down |
| `back` | Go back |
| `refresh` | Refresh page |
| `pdf` | Save page as PDF |

## Using with AI

The `snapshot` command returns a page view with numbered refs:

```
[ref=12] button "Submit"
[ref=15] textbox "Username"
```

Use these ref numbers with `click` and `type` commands.

## Tips

- Browser runs in isolated profile (doesn't affect your personal browser)
- Supports Chrome, Brave, Edge (Chromium-based browsers)
- Cookies and sessions persist within the profile
- Use `--headless` for background operation (if configured)