#!/usr/bin/env python3
"""
Facebook 批量爬蟲 - 交互式URL收集
"""

print('='*60)
print('📋 Facebook 貼文URL收集工具')
print('='*60)
print()
print('步驟：')
print('1. 打開瀏覽器訪問社團:')
print('   https://www.facebook.com/groups/945818406315161')
print()
print('2. 找到感興趣的貼文')
print('3. 複製貼文連結')
print('4. 把URL貼到這裡（每行一個，輸入空行結束）')
print()

urls = []
while True:
    try:
        url = input(f'貼文 {len(urls)+1}: ').strip()
        if not url:
            break
        if 'facebook.com' in url and ('/posts/' in url or '/permalink/' in url or 'pfbid' in url):
            urls.append(url)
            print('  ✅ 已添加')
        else:
            print('  ⚠️  請確保是Facebook貼文連結')
    except EOFError:
        break

if urls:
    print(f'\n共 {len(urls)} 個貼文')
    
    # 生成配置文件
    urls_str = ',\n        '.join([f"'{u}'" for u in urls])
    config_code = f"'POST_URLS': [\n        {urls_str}\n    ],"
    
    # 讀取v5.0並替換
    with open('fb_crawler_final_v5.py', 'r') as f:
        content = f.read()
    
    import re
    content = re.sub(r"'POST_URLS':\s*\[[^\]]+\]", config_code, content)
    
    with open('fb_crawler_batch.py', 'w') as f:
        f.write(content)
    
    print('\n✅ 配置文件已創建: fb_crawler_batch.py')
    print('\n📘 現在可以執行批量爬蟲：')
    print('   python3 fb_crawler_batch.py')
else:
    print('\n⚠️  沒有輸入URL')
