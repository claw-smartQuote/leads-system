#!/usr/bin/env python3
"""
解析 28car.com index2.php 找買車鏈接
"""

import urllib.request
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

url = "https://www.28car.com/index2.php"
req = urllib.request.Request(url, headers=headers)

with urllib.request.urlopen(req, timeout=15) as resp:
    # 使用 big5 解碼
    content = resp.read().decode('big5', errors='ignore')
    print(f"📄 頁面長度: {len(content)} 字符")
    print(f"\n🔍 搜索所有 .php 鏈接:\n")
    
    # 找到所有 php 鏈接
    links = re.findall(r'href=["\']([^"\']+\.php[^"\']*)["\']', content)
    seen = set()
    for link in links:
        if link not in seen and not link.startswith('http'):
            seen.add(link)
            print(f"   {link}")
    
    print(f"\n🔍 包含 'sell' 的鏈接:")
    for link in seen:
        if 'sell' in link.lower():
            print(f"   -> {link}")
    
    print(f"\n🔍 包含 'buy' 的鏈接:")
    for link in seen:
        if 'buy' in link.lower():
            print(f"   -> {link}")
