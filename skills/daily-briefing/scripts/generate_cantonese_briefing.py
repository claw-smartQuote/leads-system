#!/usr/bin/env python3
"""
每日晨報廣東話語音發送器
生成晨報並以廣東話語音發送到 WhatsApp
"""

import subprocess
import os
import sys

# 添加腳本目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_briefing import generate_briefing

def generate_cantonese_tts(text, output_file, voice="zh-HK-HiuMaanNeural"):
    """生成廣東話語音"""
    try:
        # 使用 OpenClaw 內置的 node-edge-tts
        edge_tts_path = "/usr/local/lib/node_modules/openclaw/node_modules/node-edge-tts/bin.js"
        
        cmd = [
            "node", edge_tts_path,
            "-t", text,
            "-f", output_file,
            "-v", voice,
            "-l", "zh-HK",
            "-o", "audio-24khz-48kbitrate-mono-mp3"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.expanduser("~/.openclaw/workspace")
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"TTS 錯誤: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("TTS 生成超時")
        return False
    except Exception as e:
        print(f"TTS 生成錯誤: {e}")
        return False

def main():
    # 生成晨報內容
    print("正在生成晨報內容...")
    briefing_text = generate_briefing()
    
    # 輸出檔案路徑（放到 outbound 目錄）
    output_mp3 = os.path.expanduser("~/.openclaw/media/outbound/daily_briefing_cantonese.mp3")
    
    print("正在生成廣東話語音...")
    if generate_cantonese_tts(briefing_text, output_mp3, "zh-HK-HiuMaanNeural"):
        print(f"語音已生成: {output_mp3}")
        print(f"\n晨報內容:\n{briefing_text}")
        return output_mp3
    else:
        print("語音生成失敗")
        return None

if __name__ == "__main__":
    mp3_file = main()
    if mp3_file:
        print(f"\n輸出檔案: {mp3_file}")
    else:
        sys.exit(1)
