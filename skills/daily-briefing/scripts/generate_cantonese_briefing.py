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
    """生成廣東話語音 - 支援長文本分段處理"""
    import tempfile
    import shutil
    import re
    
    edge_tts_path = "/usr/local/lib/node_modules/openclaw/node_modules/node-edge-tts/bin.js"
    
    # 將長文本分段（每段約 100 字，以句號分隔）
    def split_text(text, max_len=100):
        sentences = re.split('([。！？])', text)
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punct = sentences[i+1] if i+1 < len(sentences) else ""
            full_sentence = sentence + punct
            
            if len(current_chunk) + len(full_sentence) <= max_len:
                current_chunk += full_sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = full_sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text]
    
    try:
        # 創建臨時目錄
        temp_dir = tempfile.mkdtemp()
        
        # 分段處理
        chunks = split_text(text, max_len=80)
        print(f"文本已分段: {len(chunks)} 段")
        
        mp3_files = []
        for i, chunk in enumerate(chunks):
            temp_output = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            
            cmd = [
                "node", edge_tts_path,
                "-t", chunk,
                "-f", temp_output,
                "-v", voice,
                "-l", "zh-HK",
                "-o", "audio-24khz-48kbitrate-mono-mp3"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir
            )
            
            if result.returncode == 0:
                mp3_files.append(temp_output)
                print(f"  第 {i+1}/{len(chunks)} 段完成")
            else:
                print(f"  第 {i+1}/{len(chunks)} 段失敗: {result.stderr}")
        
        if not mp3_files:
            print("所有分段都生成失敗")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        
        # 合併音頻 - 使用 ffmpeg 正確合併並轉換為 OGG/Opus 格式
        if len(mp3_files) == 1:
            # 只有一段，直接複製
            temp_combined = mp3_files[0]
        else:
            # 先合併 MP3
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, 'w') as f:
                for mp3 in mp3_files:
                    f.write(f"file '{mp3}'\n")
            
            ffmpeg_path = os.path.expanduser("~/.local/bin/ffmpeg")
            if not os.path.exists(ffmpeg_path):
                ffmpeg_path = "ffmpeg"
            
            temp_combined = os.path.join(temp_dir, "combined.mp3")
            concat_cmd = [
                ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-acodec", "copy", temp_combined
            ]
            
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"FFmpeg 合併失敗: {result.stderr}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False
        
        # 轉換為 OGG/Opus (WhatsApp 語音格式)
        # 規格: Opus, 48kHz, mono, ~16kbps, voip application
        ffmpeg_path = os.path.expanduser("~/.local/bin/ffmpeg")
        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = "ffmpeg"
        
        convert_cmd = [
            ffmpeg_path, "-y", "-i", temp_combined,
            "-c:a", "libopus",
            "-b:a", "16k",
            "-ar", "48000",
            "-ac", "1",
            "-application", "voip",
            output_file
        ]
        
        result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"轉換 OGG/Opus 失敗: {result.stderr}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        
        print(f"已合併 {len(mp3_files)} 段音頻並轉換為 OGG/Opus")
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"語音已生成: {output_file}")
        return True
        
    except Exception as e:
        print(f"TTS 生成錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # 生成晨報內容
    print("正在生成晨報內容...")
    briefing_text = generate_briefing()
    
    # 輸出檔案路徑（放到 outbound 目錄，使用 OGG/Opus 格式）
    output_ogg = os.path.expanduser("~/.openclaw/media/outbound/daily_briefing_cantonese.ogg")
    
    print("正在生成廣東話語音...")
    if generate_cantonese_tts(briefing_text, output_ogg, "zh-HK-HiuMaanNeural"):
        print(f"語音已生成: {output_ogg}")
        print(f"\n晨報內容:\n{briefing_text}")
        return output_ogg
    else:
        print("語音生成失敗")
        return None

if __name__ == "__main__":
    ogg_file = main()
    if ogg_file:
        print(f"\n輸出檔案: {ogg_file}")
    else:
        sys.exit(1)
