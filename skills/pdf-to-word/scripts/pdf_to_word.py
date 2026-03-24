#!/usr/bin/env python3
"""
PDF to Word Converter
Converts PDF files to Microsoft Word (.docx) format
"""

import argparse
import sys
import os
from pathlib import Path


def check_pdf2docx():
    """Check if pdf2docx is installed"""
    try:
        from pdf2docx import Converter
        return True
    except ImportError:
        return False


def install_pdf2docx():
    """Install pdf2docx if not present"""
    import subprocess
    print("Installing pdf2docx...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pdf2docx"], 
                      check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def convert_pdf_to_word(pdf_path, output_path=None, start_page=None, end_page=None):
    """Convert PDF to Word document"""
    if not check_pdf2docx():
        print("pdf2docx not installed. Attempting to install...")
        if not install_pdf2docx():
            print("Error: Failed to install pdf2docx. Install manually with: pip install pdf2docx")
            return False
    
    try:
        from pdf2docx import Converter
    except ImportError:
        print("Error: pdf2docx import failed even after installation")
        return False
    
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return False
    
    # Determine output path
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = pdf_path.with_suffix('.docx')
    
    print(f"Converting: {pdf_path}")
    print(f"Output: {output_path}")
    
    try:
        # Create converter
        cv = Converter(str(pdf_path))
        
        # Convert
        cv.convert(
            str(output_path),
            start=start_page,
            end=end_page
        )
        cv.close()
        
        print(f"✅ Conversion successful: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False


def parse_page_range(pages_str):
    """Parse page range string like '1-5'"""
    if not pages_str:
        return None, None
    
    if '-' in pages_str:
        parts = pages_str.split('-')
        return int(parts[0]), int(parts[1])
    
    # Single page - convert just that page
    try:
        page = int(pages_str)
        return page, page
    except ValueError:
        return None, None


def batch_convert(directory, pattern="*.pdf"):
    """Convert all PDFs in a directory"""
    pdf_files = list(Path(directory).glob(pattern))
    
    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    success_count = 0
    
    for pdf_file in pdf_files:
        if convert_pdf_to_word(pdf_file):
            success_count += 1
    
    print(f"\nConverted {success_count}/{len(pdf_files)} files")


def main():
    parser = argparse.ArgumentParser(description='Convert PDF to Word (.docx)')
    parser.add_argument('input', help='PDF file or directory to convert')
    parser.add_argument('--output', '-o', help='Output Word file path')
    parser.add_argument('--pages', help='Page range to convert (e.g., 1-5)')
    parser.add_argument('--batch', action='store_true', help='Convert all PDFs in directory')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: Path not found: {args.input}")
        sys.exit(1)
    
    if args.batch and input_path.is_dir():
        batch_convert(input_path)
    elif input_path.is_dir():
        print("Use --batch flag to convert all PDFs in directory")
        sys.exit(1)
    else:
        start_page, end_page = parse_page_range(args.pages)
        success = convert_pdf_to_word(args.input, args.output, start_page, end_page)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()