#!/usr/bin/env python3
"""
測試 28car.com - 詳細診斷
"""

import requests
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
    "https://28car.com",
]

for url in urls_to_test:
    print(f"\n{'='*60}")
    print(f"🌐 測試: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print(f"📊 狀態碼: {resp.status_code}")
        print(f"📊 內容長度: {len(resp.text)} 字符")
        print(f"📊 最終 URL: {resp.url}")
        print(f"📄 內容前 500 字符:")
        print(resp.text[:500])
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    time.sleep(1)

print("\n" + "="*60)
print("✅ 測試完成")
