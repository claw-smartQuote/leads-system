---
name: simple-web-scraper
description: Simple web scraping using httpx + BeautifulSoup for public pages without anti-bot protection. Use when you need to scrape公开页面, 28car, or simple websites. For Facebook or anti-bot sites, use browser tool instead.
---

# Simple Web Scraper

Lightweight web scraping without Playwright or browser automation.

## Quick Start

```bash
python3 ~/.openclaw/workspace/simple_scraper.py <url>
```

## Features

- **httpx + BeautifulSoup** - Fast, lightweight
- **Auto-detection** of page type (28car, Facebook, generic)
- **SQLite storage** - Saves to fb_leads_final.db
- **Excel export** - Automatic xlsx output

## Usage

### From Command Line
```bash
# Scrape any URL
python3 ~/.openclaw/workspace/simple_scraper.py https://example.com

# Scrape 28car
python3 ~/.openclaw/workspace/simple_scraper.py https://www.28car.com/...

# Scrape Facebook (public posts only)
python3 ~/.openclaw/workspace/simple_scraper.py <facebook_post_url>
```

### From Agent
```python
from simple_scraper import scrape_url, export_to_excel

# Scrape a URL
results = scrape_url('https://example.com')

# Export to Excel
excel_path, count = export_to_excel()
```

## Limitations

- ❌ No JavaScript rendering
- ❌ No anti-bot bypass
- ❌ No login/session handling
- ✅ Good for public pages, APIs, simple sites

## For Complex Sites

| Site Type | Recommended Tool |
|-----------|-----------------|
| Facebook | Browser tool |
| Anti-bot sites | Scrapling (when available) |
| Simple public pages | This scraper |
| Complex SPAs | Playwright browser tool |
