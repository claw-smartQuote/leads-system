#!/usr/bin/env python3
"""
每日晨報廣東話語音發送器
生成晨報並以廣東話語音發送
"""

import subprocess
import os
import sys
import tempfile

# 添加腳本目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_briefing import generate_briefing
from cantonese_tts import generate_cantonese_tts

def main():
    # 生成晨報內容
    briefing_text = generate_briefing()
    
    # 創建臨時檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(briefing_text)
        text_file = f.name
    
    # 生成語音檔案
    output_mp3 = "/tmp/daily_briefing_cantonese.mp3"
    
    print("正在生成廣東話語音...")
    if generate_cantonese_tts(briefing_text, output_mp3, "zh-HK-HiuMaanNeural"):
        print(f"語音已生成: {output_mp3}")
        print(f"\n晨報內容:\n{briefing_text}")
        return output_mp3
    else:
        print("語音生成失敗")
        return None
    finally:
        # 清理臨時檔案
        if os.path.exists(text_file):
            os.unlink(text_file)

if __name__ == "__main__":
    mp3_file = main()
    if mp3_file:
        print(f"\n輸出檔案: {mp3_file}")
    else:
        sys.exit(1)
