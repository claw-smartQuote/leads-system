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
    生成廣東話語音 - 支援長文本分段處理
    
    參數：
        text: 要轉換嘅文字（廣東話）
        output_file: 輸出檔案路徑
        voice: 聲音選項，預設女聲
    """
    import tempfile
    import shutil
    import re
    
    edge_tts_path = "/usr/local/lib/node_modules/openclaw/node_modules/node-edge-tts/bin.js"
    
    # 將長文本分段（每段約 80 字，以句號分隔）
    def split_text(text, max_len=80):
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
            else:
                print(f"  第 {i+1}/{len(chunks)} 段失敗: {result.stderr}")
        
        if not mp3_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        
        # 合併音頻 - 使用 ffmpeg 正確合併
        if len(mp3_files) == 1:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            shutil.copy(mp3_files[0], output_file)
        else:
            # 嘗試使用 ffmpeg 合併
            ffmpeg_path = os.path.expanduser("~/.local/bin/ffmpeg")
            if not os.path.exists(ffmpeg_path):
                ffmpeg_path = "ffmpeg"
            
            try:
                concat_file = os.path.join(temp_dir, "concat_list.txt")
                with open(concat_file, 'w') as f:
                    for mp3 in mp3_files:
                        f.write(f"file '{mp3}'\n")
                
                concat_cmd = [
                    ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file,
                    "-acodec", "copy",
                    output_file
                ]
                
                result = subprocess.run(
                    concat_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    print(f"FFmpeg 合併失敗，回退到二進制拼接: {result.stderr}")
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'wb') as outfile:
                        for mp3 in mp3_files:
                            with open(mp3, 'rb') as infile:
                                outfile.write(infile.read())
            except Exception as e:
                print(f"FFmpeg 錯誤，回退到二進制拼接: {e}")
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'wb') as outfile:
                    for mp3 in mp3_files:
                        with open(mp3, 'rb') as infile:
                            outfile.write(infile.read())
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True
        
    except Exception as e:
        print(f"TTS 生成錯誤: {e}")
        import traceback
        traceback.print_exc()
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
