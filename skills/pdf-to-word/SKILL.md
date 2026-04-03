---
name: pdf-to-word
description: Convert PDF files to Microsoft Word (.docx) format. Use when the user needs to (1) Convert PDF to editable Word documents, (2) Edit PDF content in Word, (3) Convert scanned PDFs to Word with OCR, (4) Convert insurance documents, forms, or reports from PDF to Word format for editing.
metadata:
  {
    "openclaw":
      {
        "emoji": "📝",
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "pip-pdf2docx",
              "kind": "pip",
              "package": "pdf2docx",
              "bins": [],
              "label": "Install pdf2docx (pip)",
            },
          ],
      },
  }
---

# PDF to Word Converter

Convert PDF files to editable Microsoft Word (.docx) documents.

## Quick Start

### Convert PDF to Word

```bash
python3 {baseDir}/scripts/pdf_to_word.py /path/to/document.pdf
```

### Specify output file

```bash
python3 {baseDir}/scripts/pdf_to_word.py /path/to/document.pdf --output /path/to/output.docx
```

### Convert specific pages

```bash
python3 {baseDir}/scripts/pdf_to_word.py /path/to/document.pdf --pages 1-5
```

## Features

- **Full conversion**: Preserves formatting, images, and layout
- **Page selection**: Convert only specific pages
- **Batch processing**: Convert multiple PDFs at once
- **Progress tracking**: See conversion progress for large documents

## Limitations

- Complex layouts may require manual adjustment after conversion
- Scanned PDFs need OCR first (use pdf-reader-ocr skill)
- Some fonts may be substituted if not available on system

## Tips

- For best results, ensure the PDF has embedded fonts
- Large PDFs may take longer to convert
- Review the Word document after conversion for formatting adjustments