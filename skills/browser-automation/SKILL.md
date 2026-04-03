---
name: browser-automation
description: Control and automate web browser for web scraping, form filling, screenshots, and page interactions. Use when you need to (1) Open and navigate websites, (2) Take screenshots of web pages, (3) Fill forms and click buttons, (4) Extract data from websites, (5) Automate web workflows, (6) Login to websites, (7) Download files from web pages, or (8) Monitor web page changes.
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

```bash
# Open a website
browser action=open targetUrl=https://example.com

# Take screenshot
browser action=screenshot

# Get interactive snapshot with refs
browser action=snapshot targetId=<tab_id>
```

## Core Actions

| Action | Description |
|--------|-------------|
| `start` | Start browser if not running |
| `stop` | Stop browser |
| `open` | Navigate to URL |
| `snapshot` | Get page with numbered element refs |
| `screenshot` | Take screenshot |
| `navigate` | Navigate to URL (same as open) |
| `act` | Click/type/scroll on element by ref |

## Facebook Scraping Workflow

### Step 1: Open Facebook Post
```
browser action=open targetUrl=https://www.facebook.com/groups/<group_id>/permalink/<post_id>/
```

### Step 2: Wait for Dialog
Facebook posts open in a dialog. Identify with:
```
browser action=snapshot targetId=<tab> refs=aria compact=true
```
Look for `[role="dialog"]` element.

### Step 3: Expand All Replies
Click "View X replies" buttons:
```
browser action=act targetId=<tab> ref=<reply_button_ref> kind=click
```

Button text patterns to find:
- `查看 1 則回覆`
- `查看 X 則回覆` (X = number)
- `查看全部 X 則回覆`
- `View more replies`

### Step 4: Scroll in Dialog
Scroll within dialog using:
```
browser action=act targetId=<tab> ref=<dialog_ref> kind=press key=ArrowDown
```
Repeat several times to load all comments.

### Step 5: Extract Comments
Use `snapshot` with refs to find comment elements:
- `[role="article"]` - Comment blocks
- `a[href*="/groups/"]` - User profile links
- `div[dir="auto"]` - Comment text

### Step 6: Save to Database
```python
import sqlite3
from datetime import datetime

conn = sqlite3.connect('fb_leads_final.db')
cursor = conn.cursor()

comments = [
    {"name": "Username", "text": "Comment content"},
    # ... more comments
]

for c in comments:
    cursor.execute('''
        INSERT OR IGNORE INTO fb_leads 
        (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (post_url, c['name'], '', c['text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

conn.commit()
```

## Key Learnings (2026-04-03)

### Facebook Dialog Pattern
- Posts open in `[role="dialog"]` overlay
- Close button: `[aria-label="關閉"]` or `[aria-label="Close"]`
- Main dialog ref: `e1406` (typically)

### Comment Expansion
- "View replies" buttons use `ref=eXXXX` (dynamic)
- Use `snapshot compact=true refs=aria` to find them
- Patterns: `查看 \d+ 則回覆`, `View \d+ repl`

### Scrolling in Dialogs
- Cannot use `window.scrollIntoView` in dialogs
- Use keyboard: `kind=press key=ArrowDown`
- Or: focus dialog then use scroll

### Dynamic Loading
- Facebook shows "載入中..." for loading content
- Wait 2-3 seconds between actions
- May need to scroll to trigger lazy load

### Comment Extraction
- Use `role="article"` for comment blocks
- User names in `a[href*="facebook.com"]` links
- Comment text in `div[dir="auto"]` elements
- Filter out short text (< 3 chars)

## Commands Reference

| Command | Description |
|---------|-------------|
| `open <url>` | Navigate to URL |
| `status` | Check browser status |
| `start` | Start browser |
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

## Tips

- Browser runs in isolated profile
- Supports Chrome, Brave, Edge (Chromium)
- Cookies and sessions persist
- Use `--headless` for background operation

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Dialog not opening | Click post link directly |
| Elements not found | Use `snapshot refs=aria` |
| Scroll not working | Try `kind=press key=ArrowDown` |
| Page stuck loading | Wait 3-5 seconds |
| Login required | Check cookies in `~/.fb_crawler/` |
