#!/usr/bin/env python3
"""
測試 28car.com - 詳細診斷 (使用內置庫)
"""

import urllib.request
import urllib.error
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
}

urls_to_test = [
    "https://www.28car.com",
    "https://www.28car.com/",
    "https://www.28car.com/index2.php",
    "https://www.28car.com/buycar.php",
]

for url in urls_to_test:
    print(f"\n{'='*60}")
    print(f"🌐 測試: {url}")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            print(f"📊 狀態碼: {resp.status}")
            print(f"📊 內容長度: {len(content)} 字符")
            print(f"📄 內容前 800 字符:")
            print(content[:800])
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP 錯誤: {e.code} - {e.reason}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    time.sleep(1)

print("\n" + "="*60)
print("✅ 測試完成")
