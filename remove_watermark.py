#!/usr/bin/env python3
"""
PDF 水印去除工具 - 針對 Adobe Watermark
"""

import pikepdf
import sys
from pathlib import Path

def remove_adobe_watermark(input_path, output_path):
    """移除 Adobe 類型的水印"""
    try:
        pdf = pikepdf.open(input_path)
        
        print(f"📄 處理: {input_path}")
        print(f"   總頁數: {len(pdf.pages)}")
        
        removed_count = 0
        
        for page_num, page in enumerate(pdf.pages, 1):
            resources = page.get('/Resources', {})
            xobjects = resources.get('/XObject', {})
            
            objects_to_remove = []
            
            for name, obj in xobjects.items():
                try:
                    # 檢查是否為 Adobe 水印
                    if hasattr(obj, 'get'):
                        piece_info = obj.get('/PieceInfo', {})
                        if hasattr(piece_info, 'get'):
                            adobe_type = piece_info.get('/ADBE_CompoundType', {})
                            if hasattr(adobe_type, 'get'):
                                private = adobe_type.get('/Private', '')
                                if private == '/Watermark':
                                    print(f"   第{page_num}頁: 發現水印 {name}")
                                    objects_to_remove.append(name)
                                    removed_count += 1
                        
                        # 也檢查 OCG 名稱
                        oc = obj.get('/OC', {})
                        if hasattr(oc, 'get'):
                            ocgs = oc.get('/OCGs', {})
                            if hasattr(ocgs, 'get'):
                                oc_name = ocgs.get('/Name', '')
                                if oc_name == 'Watermark':
                                    if name not in objects_to_remove:
                                        print(f"   第{page_num}頁: 發現 OCG 水印 {name}")
                                        objects_to_remove.append(name)
                                        removed_count += 1
                except Exception as e:
                    pass
            
            # 移除找到的水印
            for name in objects_to_remove:
                try:
                    del xobjects[name]
                except:
                    pass
        
        # 保存處理後的 PDF
        pdf.save(output_path)
        pdf.close()
        
        print(f"✅ 完成！移除 {removed_count} 個水印")
        print(f"   輸出: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 remove_watermark.py <input_pdf> <output_pdf>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    remove_adobe_watermark(input_file, output_file)
