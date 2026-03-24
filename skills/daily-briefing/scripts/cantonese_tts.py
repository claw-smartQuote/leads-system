#!/usr/bin/env python3
"""
廣東話 TTS 引擎 - 使用 Microsoft Edge TTS
支援語言：zh-HK（廣東話/粵語）
聲音選項：
  - zh-HK-HiuMaanNeural (女聲)
  - zh-HK-WanLungNeural (男聲)
"""

import subprocess
import sys
import os

def generate_cantonese_tts(text, output_file, voice="zh-HK-HiuMaanNeural"):
    """
    生成廣東話語音
    
    參數：
        text: 要轉換嘅文字（廣東話）
        output_file: 輸出檔案路徑
        voice: 聲音選項，預設女聲
    """
    try:
        # 使用 node-edge-tts 生成廣東話語音
        cmd = [
            "npx", "node-edge-tts",
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
    if len(sys.argv) < 3:
        print("用法: python3 cantonese_tts.py '<文字>' <輸出檔案> [聲音]")
        print("聲音選項: zh-HK-HiuMaanNeural (女) 或 zh-HK-WanLungNeural (男)")
        sys.exit(1)
    
    text = sys.argv[1]
    output_file = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "zh-HK-HiuMaanNeural"
    
    if generate_cantonese_tts(text, output_file, voice):
        print(f"語音已生成: {output_file}")
    else:
        print("語音生成失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()
