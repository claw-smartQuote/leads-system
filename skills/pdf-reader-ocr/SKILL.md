---
name: pdf-reader-ocr
description: Read PDF files and extract text content with OCR support. Use when the user needs to (1) Extract text from PDF files, (2) Read scanned PDF documents that require OCR, (3) Convert PDF content to readable text format, (4) Search for text within PDF files, or (5) Process insurance documents, forms, or any PDF files for text extraction.
metadata:
  {
    "openclaw":
      {
        "emoji": "📄",
        "requires": { "bins": ["python3"], "anyBins": ["pdftotext", "tesseract"] },
        "install":
          [
            {
              "id": "brew-pdftotext",
              "kind": "brew",
              "formula": "poppler",
              "bins": ["pdftotext"],
              "label": "Install poppler (pdftotext)",
            },
            {
              "id": "brew-tesseract",
              "kind": "brew",
              "formula": "tesseract",
              "bins": ["tesseract"],
              "label": "Install tesseract (OCR)",
            },
          ],
      },
  }
---

# PDF Reader + OCR

Extract text from PDF files, including scanned documents that require OCR.

## Quick Start

### Extract text from a PDF

```bash
python3 {baseDir}/scripts/pdf_extract.py /path/to/document.pdf
```

### Extract with OCR for scanned documents

```bash
python3 {baseDir}/scripts/pdf_extract.py /path/to/scanned.pdf --ocr
```

### Extract specific pages

```bash
python3 {baseDir}/scripts/pdf_extract.py /path/to/document.pdf --pages 1-5
```

### Search for text in PDF

```bash
python3 {baseDir}/scripts/pdf_extract.py /path/to/document.pdf --search "保險條款"
```

## Features

- **Native text extraction**: For PDFs with embedded text
- **OCR support**: For scanned documents and images
- **Page selection**: Extract specific pages or ranges
- **Text search**: Find specific content within PDFs
- **Multi-language OCR**: Support for Chinese, English, and more

## When to use OCR

Use `--ocr` flag when:
- PDF is a scanned image (no selectable text)
- Text extraction returns garbled characters
- Document appears to be a photo or scan of a paper document

## Output

Text is output to stdout by default. Use `--output` to save to a file:

```bash
python3 {baseDir}/scripts/pdf_extract.py /path/to/document.pdf --output extracted.txt
```