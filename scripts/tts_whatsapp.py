#!/usr/bin/env python3
"""
WhatsApp TTS 助手 - 廣東話女聲
用法: python3 tts_whatsapp.py "要說的話" [output.ogg]
"""

import subprocess
import tempfile
import os
import sys
import imageio_ffmpeg

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = 'zh-HK-HiuMaanNeural'  # 廣東話女聲

def text_to_whatsapp_voice(text, output_path=None):
    """將文字轉換為 WhatsApp 語音格式 (OGG/Opus 16kHz)"""
    
    # 創建臨時文件
    tmp_mp3 = tempfile.mktemp(suffix='.mp3')
    
    try:
        # 1. 用 edge-tts 生成 MP3
        print(f"🔊 生成語音: {text[:30]}...")
        result = subprocess.run([
            'edge-tts',
            '--voice', VOICE,
            '--text', text,
            '--write-media', tmp_mp3
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ TTS 失敗: {result.stderr}")
            return None
        
        # 2. 轉換為 WhatsApp 格式
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.ogg')
        
        result = subprocess.run([
            FFMPEG_PATH,
            '-i', tmp_mp3,
            '-c:a', 'libopus',
            '-b:a', '12k',
            '-ar', '16000',
            '-ac', '1',
            '-application', 'voip',
            output_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 轉換失敗: {result.stderr}")
            return None
        
        print(f"✅ 完成: {output_path}")
        print(f"   大小: {os.path.getsize(output_path)} bytes")
        return output_path
        
    finally:
        # 清理臨時 MP3
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 tts_whatsapp.py \"文字\" [output.ogg]")
        sys.exit(1)
    
    text = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = text_to_whatsapp_voice(text, output)
    if result:
        print(result)

if __name__ == '__main__':
    main()
