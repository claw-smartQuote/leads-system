#!/usr/bin/env python3
"""
PDF Text Extraction Tool with OCR support
Extracts text from PDF files, including scanned documents
"""

import argparse
import sys
import os
import re
import tempfile
import subprocess
from pathlib import Path


def check_command(cmd):
    """Check if a command exists"""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_text_native(pdf_path, first_page=None, last_page=None):
    """Extract text using pdftotext (poppler)"""
    if not check_command("pdftotext"):
        return None, "pdftotext not installed. Install with: brew install poppler"
    
    cmd = ["pdftotext", "-layout"]
    
    if first_page:
        cmd.extend(["-f", str(first_page)])
    if last_page:
        cmd.extend(["-l", str(last_page)])
    
    cmd.append(pdf_path)
    cmd.append("-")  # Output to stdout
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout, None
        return None, result.stderr
    except Exception as e:
        return None, str(e)


def extract_text_with_ocr(pdf_path, first_page=None, last_page=None, lang="chi_sim+eng"):
    """Extract text using OCR (tesseract)"""
    if not check_command("tesseract"):
        return None, "tesseract not installed. Install with: brew install tesseract tesseract-lang"
    
    if not check_command("pdftoppm"):
        return None, "pdftoppm not installed. Install with: brew install poppler"
    
    # Convert PDF to images
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = ["pdftoppm", "-png", pdf_path, os.path.join(tmpdir, "page")]
        
        if first_page:
            cmd.extend(["-f", str(first_page)])
        if last_page:
            cmd.extend(["-l", str(last_page)])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return None, f"Failed to convert PDF to images: {e.stderr.decode()}"
        
        # OCR each image
        pages = sorted(Path(tmpdir).glob("page-*.png"))
        all_text = []
        
        for page_img in pages:
            try:
                result = subprocess.run(
                    ["tesseract", str(page_img), "-", "-l", lang],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    all_text.append(result.stdout)
            except Exception as e:
                all_text.append(f"[Error processing page: {e}]")
        
        return "\n--- Page Break ---\n".join(all_text), None


def needs_ocr(pdf_path):
    """Check if PDF likely needs OCR (no extractable text)"""
    text, _ = extract_text_native(pdf_path)
    if text and len(text.strip()) > 50:
        return False
    return True


def search_in_text(text, query):
    """Search for query in text and return matching lines"""
    lines = text.split('\n')
    matches = []
    query_lower = query.lower()
    
    for i, line in enumerate(lines, 1):
        if query_lower in line.lower():
            matches.append(f"Line {i}: {line}")
    
    return matches


def parse_page_range(pages_str):
    """Parse page range string like '1-5' or '1,3,5'"""
    if not pages_str:
        return None, None
    
    # Handle range like "1-5"
    if '-' in pages_str:
        parts = pages_str.split('-')
        return int(parts[0]), int(parts[1])
    
    # Single page
    try:
        page = int(pages_str)
        return page, page
    except ValueError:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Extract text from PDF files')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('--ocr', action='store_true', help='Use OCR for scanned documents')
    parser.add_argument('--pages', help='Page range (e.g., 1-5 or 3)')
    parser.add_argument('--search', help='Search for specific text')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--lang', default='chi_sim+eng', help='OCR language (default: chi_sim+eng)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    first_page, last_page = parse_page_range(args.pages)
    
    # Determine if OCR is needed
    use_ocr = args.ocr
    if not use_ocr and needs_ocr(args.pdf_path):
        print("Note: PDF appears to be scanned. Consider using --ocr flag.", file=sys.stderr)
    
    # Extract text
    if use_ocr:
        text, error = extract_text_with_ocr(args.pdf_path, first_page, last_page, args.lang)
    else:
        text, error = extract_text_native(args.pdf_path, first_page, last_page)
    
    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    
    # Search if requested
    if args.search and text:
        matches = search_in_text(text, args.search)
        if matches:
            text = f"Found {len(matches)} matches for '{args.search}':\n\n" + '\n'.join(matches)
        else:
            text = f"No matches found for '{args.search}'"
    
    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text or "")
        print(f"Text saved to: {args.output}")
    else:
        print(text or "")


if __name__ == '__main__':
    main()