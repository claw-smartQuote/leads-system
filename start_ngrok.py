#!/usr/bin/env python3
"""啟動 ngrok 隧道"""
import time
import sys
sys.path.insert(0, '/Users/claw/Library/Python/3.9/lib/python/site-packages')

from pyngrok import ngrok

# 啟動隧道
try:
    public_url = ngrok.connect(8000, "http")
    print(f"🌐 外部訪問網址: {public_url}")
    print("")
    print("📋 系統連結:")
    print(f"   客戶表單: {public_url}")
    print(f"   管理後台: {public_url}/admin")
    print(f"   API 文檔: {public_url}/docs")
    print("")
    print("⏹️  按 Ctrl+C 停止")
    
    # 保持運行
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n🛑 停止 ngrok...")
    ngrok.kill()
except Exception as e:
    print(f"❌ 錯誤: {e}")
    print("💡 提示: 需要在 https://ngrok.com 註冊並獲取 authtoken")