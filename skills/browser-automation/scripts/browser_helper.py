#!/usr/bin/env python3
"""
Browser Automation Helper
Wrapper for OpenClaw's browser tool
"""

import argparse
import subprocess
import sys
import json
import time


def run_openclaw_browser(args):
    """Run openclaw browser command"""
    cmd = ["openclaw", "browser"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", "openclaw CLI not found"


def browser_status():
    """Check browser status"""
    success, stdout, stderr = run_openclaw_browser(["status"])
    if success:
        print(stdout)
    else:
        print(f"Error: {stderr}", file=sys.stderr)
        return False
    return True


def browser_start():
    """Start browser"""
    print("Starting browser...")
    success, stdout, stderr = run_openclaw_browser(["start"])
    if success:
        print("✅ Browser started")
        return True
    else:
        print(f"❌ Failed to start: {stderr}", file=sys.stderr)
        return False


def browser_stop():
    """Stop browser"""
    print("Stopping browser...")
    success, stdout, stderr = run_openclaw_browser(["stop"])
    if success:
        print("✅ Browser stopped")
        return True
    else:
        print(f"❌ Failed to stop: {stderr}", file=sys.stderr)
        return False


def browser_open(url):
    """Open a URL"""
    print(f"Opening: {url}")
    success, stdout, stderr = run_openclaw_browser(["open", url])
    if success:
        print(f"✅ Opened: {url}")
        return True
    else:
        print(f"❌ Failed to open: {stderr}", file=sys.stderr)
        return False


def browser_navigate(url):
    """Navigate to URL in current tab"""
    print(f"Navigating to: {url}")
    success, stdout, stderr = run_openclaw_browser(["navigate", url])
    if success:
        print(f"✅ Navigated to: {url}")
        return True
    else:
        print(f"❌ Failed to navigate: {stderr}", file=sys.stderr)
        return False


def browser_tabs():
    """List tabs"""
    success, stdout, stderr = run_openclaw_browser(["tabs"])
    if success:
        print(stdout)
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_screenshot(output=None, full_page=False):
    """Take screenshot"""
    args = ["screenshot"]
    if full_page:
        args.append("--full-page")
    
    success, stdout, stderr = run_openclaw_browser(args)
    if success:
        # Extract MEDIA path from output
        for line in stdout.split('\n'):
            if 'MEDIA:' in line:
                path = line.split('MEDIA:')[1].strip()
                if output:
                    # Copy to requested location
                    import shutil
                    shutil.copy(path, output)
                    print(f"✅ Screenshot saved: {output}")
                else:
                    print(f"✅ Screenshot: {path}")
                return True
        print(stdout)
        return True
    else:
        print(f"❌ Failed: {stderr}", file=sys.stderr)
        return False


def browser_snapshot(interactive=True):
    """Get page snapshot"""
    args = ["snapshot"]
    if interactive:
        args.append("--interactive")
    
    success, stdout, stderr = run_openclaw_browser(args)
    if success:
        print(stdout)
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_content():
    """Get page text content"""
    success, stdout, stderr = run_openclaw_browser(["snapshot", "--format", "aria"])
    if success:
        print(stdout)
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_click(ref):
    """Click element by ref"""
    print(f"Clicking ref: {ref}")
    success, stdout, stderr = run_openclaw_browser(["click", str(ref)])
    if success:
        print(f"✅ Clicked ref {ref}")
        return True
    else:
        print(f"❌ Failed: {stderr}", file=sys.stderr)
        return False


def browser_type(ref, text, submit=False):
    """Type text into element"""
    print(f"Typing into ref {ref}: {text}")
    args = ["type", str(ref), text]
    if submit:
        args.append("--submit")
    
    success, stdout, stderr = run_openclaw_browser(args)
    if success:
        print(f"✅ Typed text")
        return True
    else:
        print(f"❌ Failed: {stderr}", file=sys.stderr)
        return False


def browser_scroll():
    """Scroll down"""
    success, stdout, stderr = run_openclaw_browser(["evaluate", "--fn", "window.scrollBy(0, 500)"])
    if success:
        print("✅ Scrolled down")
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_back():
    """Go back"""
    success, stdout, stderr = run_openclaw_browser(["evaluate", "--fn", "history.back()"])
    if success:
        print("✅ Went back")
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_refresh():
    """Refresh page"""
    success, stdout, stderr = run_openclaw_browser(["navigate", "--reload"])
    if success:
        print("✅ Page refreshed")
    else:
        print(f"Error: {stderr}", file=sys.stderr)


def browser_pdf(output="page.pdf"):
    """Save as PDF"""
    success, stdout, stderr = run_openclaw_browser(["pdf"])
    if success:
        for line in stdout.split('\n'):
            if 'MEDIA:' in line:
                path = line.split('MEDIA:')[1].strip()
                import shutil
                shutil.copy(path, output)
                print(f"✅ PDF saved: {output}")
                return True
        print(stdout)
    else:
        print(f"❌ Failed: {stderr}", file=sys.stderr)
    return False


def browser_fill(form_data):
    """Fill form fields"""
    # form_data: list of dicts with ref, type, value
    import json
    fields_json = json.dumps(form_data)
    success, stdout, stderr = run_openclaw_browser(["fill", "--fields", fields_json])
    if success:
        print("✅ Form filled")
        return True
    else:
        print(f"❌ Failed: {stderr}", file=sys.stderr)
        return False


def browser_wait_for_text(text, timeout=10000):
    """Wait for text to appear"""
    success, stdout, stderr = run_openclaw_browser(["wait", "--text", text, "--timeout-ms", str(timeout)])
    if success:
        print(f"✅ Text found: {text}")
        return True
    else:
        print(f"❌ Text not found: {stderr}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='Browser Automation Helper')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status
    subparsers.add_parser('status', help='Check browser status')
    
    # Start
    subparsers.add_parser('start', help='Start browser')
    
    # Stop
    subparsers.add_parser('stop', help='Stop browser')
    
    # Open
    open_parser = subparsers.add_parser('open', help='Open URL')
    open_parser.add_argument('url', help='URL to open')
    
    # Navigate
    nav_parser = subparsers.add_parser('navigate', help='Navigate to URL')
    nav_parser.add_argument('url', help='URL to navigate to')
    
    # Tabs
    subparsers.add_parser('tabs', help='List tabs')
    
    # Screenshot
    screenshot_parser = subparsers.add_parser('screenshot', help='Take screenshot')
    screenshot_parser.add_argument('--output', '-o', help='Output file path')
    screenshot_parser.add_argument('--full-page', action='store_true', help='Full page screenshot')
    
    # Snapshot
    snapshot_parser = subparsers.add_parser('snapshot', help='Get page snapshot')
    snapshot_parser.add_argument('--no-interactive', action='store_true', help='Non-interactive mode')
    
    # Content
    subparsers.add_parser('content', help='Get page content')
    
    # Click
    click_parser = subparsers.add_parser('click', help='Click element')
    click_parser.add_argument('ref', help='Element ref number')
    
    # Type
    type_parser = subparsers.add_parser('type', help='Type text')
    type_parser.add_argument('ref', help='Element ref number')
    type_parser.add_argument('text', help='Text to type')
    type_parser.add_argument('--submit', action='store_true', help='Press Enter after typing')
    
    # Scroll
    subparsers.add_parser('scroll', help='Scroll down')
    
    # Back
    subparsers.add_parser('back', help='Go back')
    
    # Refresh
    subparsers.add_parser('refresh', help='Refresh page')
    
    # PDF
    pdf_parser = subparsers.add_parser('pdf', help='Save as PDF')
    pdf_parser.add_argument('--output', '-o', default='page.pdf', help='Output file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'status':
        browser_status()
    elif args.command == 'start':
        browser_start()
    elif args.command == 'stop':
        browser_stop()
    elif args.command == 'open':
        browser_open(args.url)
    elif args.command == 'navigate':
        browser_navigate(args.url)
    elif args.command == 'tabs':
        browser_tabs()
    elif args.command == 'screenshot':
        browser_screenshot(args.output, args.full_page)
    elif args.command == 'snapshot':
        browser_snapshot(not args.no_interactive)
    elif args.command == 'content':
        browser_content()
    elif args.command == 'click':
        browser_click(args.ref)
    elif args.command == 'type':
        browser_type(args.ref, args.text, args.submit)
    elif args.command == 'scroll':
        browser_scroll()
    elif args.command == 'back':
        browser_back()
    elif args.command == 'refresh':
        browser_refresh()
    elif args.command == 'pdf':
        browser_pdf(args.output)


if __name__ == '__main__':
    main()