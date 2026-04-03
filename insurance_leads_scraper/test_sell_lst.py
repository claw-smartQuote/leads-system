#!/usr/bin/env python3
"""
測試 sell_lst.php 頁面
"""

import urllib.request

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

url = "https://www.28car.com/sell_lst.php"
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('big5', errors='ignore')
        print(f"✅ 狀態碼: {resp.status}")
        print(f"📄 內容長度: {len(content)} 字符")
        print(f"\n📄 前 1500 字符:")
        print(content[:1500])
        
        # 檢查是否有車輛信息
        if 'sell_detail' in content or 'selldetail' in content:
            print("\n✅ 找到車輛詳情鏈接!")
        
        # 計算表格行數
        import re
        rows = re.findall(r'<tr[^>]*>', content)
        print(f"\n📊 找到 {len(rows)} 個表格行")
        
except Exception as e:
    print(f"❌ 錯誤: {e}")
