#!/usr/bin/env python3
import os
import sys
import json
import re
from pathlib import Path

try:
    import PyPDF2
except:
    print("PyPDF2 not available")
    sys.exit(1)

try:
    import pandas as pd
except:
    pd = None

def extract_pdf_text(filepath, max_chars=5000):
    """Extract text from PDF file"""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text_parts = []
            for i, page in enumerate(reader.pages[:10]):  # Max 10 pages
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except:
                    pass
            full_text = '\n'.join(text_parts)
            return full_text[:max_chars]
    except Exception as e:
        return f"Error: {e}"

def extract_xlsx_content(filepath):
    """Extract content from Excel file"""
    if pd is None:
        return "pandas not available"
    try:
        # Try to read all sheets
        xl = pd.ExcelFile(filepath)
        result = []
        for sheet in xl.sheet_names:
            df = pd.read_excel(filepath, sheet_name=sheet)
            result.append(f"=== Sheet: {sheet} ===")
            result.append(df.to_string(max_rows=50))
        return '\n'.join(result)[:8000]
    except Exception as e:
        return f"Error: {e}"

def sanitize_filename(name):
    """Remove UUID from filename for cleaner naming"""
    return re.sub(r'---[\w-]+$', '', name)

def get_file_category(filepath):
    """Categorize file based on path"""
    path = str(filepath)
    if '保險條款' in path or '條款' in path:
        return 'insurance_clauses'
    elif '投保表格' in path or '投保書' in path:
        return 'application_forms'
    elif '保單樣本' in path:
        return 'policy_samples'
    elif '費率表' in path:
        return 'rate_tables'
    elif 'IIQE' in path or 'IIQE' in Path(filepath).stem:
        return 'iqe_exam'
    elif '潛客' in path:
        return 'leads'
    elif '保單管理' in path or '管理' in path:
        return 'policy_management'
    elif '蘇黎世' in path:
        return 'zurich'
    elif '大新' in path:
        return 'dashin'
    elif '安聯' in path:
        return 'alliance'
    elif '立橋' in path:
        return '立橋'
    else:
        return 'other'

def main():
    base_dirs = [
        "/Users/claw/Desktop/🦞 龙虾文件",
        "/Users/claw/Desktop/IIQE"
    ]
    
    files = []
    for base_dir in base_dirs:
        if os.path.exists(base_dir):
            for root, dirs, filenames in os.walk(base_dir):
                for filename in filenames:
                    if filename.endswith(('.pdf', '.xlsx', '.xls')):
                        filepath = os.path.join(root, filename)
                        files.append(filepath)
    
    print(f"Found {len(files)} files to process")
    
    knowledge_base = {
        'files_processed': 0,
        'files_failed': 0,
        'content': {}
    }
    
    for filepath in files:
        try:
            category = get_file_category(filepath)
            filename_clean = sanitize_filename(Path(filepath).stem)
            
            print(f"Processing: {filename_clean} ({category})")
            
            if filepath.endswith('.pdf'):
                content = extract_pdf_text(filepath)
            elif filepath.endswith(('.xlsx', '.xls')):
                content = extract_xlsx_content(filepath)
            else:
                content = "Unsupported format"
            
            key = f"{category}/{filename_clean}"
            knowledge_base['content'][key] = {
                'filepath': filepath,
                'category': category,
                'filename': filename_clean,
                'content_preview': content[:2000] if len(content) > 2000 else content,
                'full_content': content
            }
            knowledge_base['files_processed'] += 1
            
        except Exception as e:
            print(f"Failed: {filepath} - {e}")
            knowledge_base['files_failed'] += 1
    
    # Save to file
    output_path = '/Users/claw/.openclaw/workspace/memory/knowledge_base_raw.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Processed: {knowledge_base['files_processed']}")
    print(f"Failed: {knowledge_base['files_failed']}")
    print(f"Output: {output_path}")
    
    # Also create a readable summary
    summary_path = '/Users/claw/.openclaw/workspace/memory/knowledge_summary.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# 保險知識庫摘要\n\n")
        f.write(f"總共處理: {knowledge_base['files_processed']} 個文件\n\n")
        
        # Group by category
        categories = {}
        for key, data in knowledge_base['content'].items():
            cat = data['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(data)
        
        for cat, items in sorted(categories.items()):
            f.write(f"\n## {cat}\n")
            for item in items:
                f.write(f"- {item['filename']}\n")

if __name__ == '__main__':
    main()
