# Daily Briefing Skill

每日晨報自動生成與語音播報（廣東話版）

## 功能

- 自動生成每日晨報內容
- **天氣預報**：香港當日天氣、溫度、降雨機率（廣東話描述）
- **待辦清單**：從記憶文件讀取待辦事項
- **保單提醒**：即將到期嘅保單
- **潛客系統提示**：提醒檢查潛客資料
- **✅ 廣東話語音**：使用 Microsoft Edge TTS (zh-HK-HiuMaanNeural)

## 技術實現

**TTS 引擎：**
- 使用 Microsoft Edge TTS (node-edge-tts)
- 聲音：`zh-HK-HiuMaanNeural`（女聲，廣東話）
- 語言代碼：`zh-HK`
- 中間格式：`audio-24khz-48kbitrate-mono-mp3`

**WhatsApp 語音格式（重要！）：**
- 格式：**OGG/Opus**
- 取樣率：48000 Hz
- 聲道：Mono（單聲道）
- 位元率：~16 kbps
- Application: voip
- 轉換命令：
  ```bash
  ffmpeg -i input.mp3 -c:a libopus -b:a 16k -ar 48000 -ac 1 -application voip output.ogg
  ```

**相關檔案：**
- `scripts/generate_briefing.py` - 生成晨報文字內容
- `scripts/generate_cantonese_briefing.py` - 生成廣東話語音（OGG/Opus 格式）
- `scripts/cantonese_tts.py` - 廣東話 TTS 引擎

**長文本處理：**
- node-edge-tts 對長文本會超時，需分段生成（每段約 80 字）
- 使用 ffmpeg concat 合併多段音頻
- 最終轉換為 WhatsApp 相容的 OGG/Opus 格式

---

## ⚠️ 重要提醒：語音格式規範

**所有生成發送的語音檔案必須使用 OGG/Opus 格式！**

| 項目 | 規格 |
|------|------|
| 容器格式 | OGG |
| 音頻編碼 | Opus |
| 取樣率 | 48000 Hz |
| 聲道 | Mono（單聲道）|
| 位元率 | ~16 kbps |
| Application | voip |

**為何不能用 MP3/M4A：**
- WhatsApp 原生語音格式為 OGG/Opus
- MP3/M4A 在 WhatsApp 上可能無法播放或顯示為檔案而非語音消息
- 內置 `tts` 工具生成的 MP3 可以播放（因為系統會自動轉換）
- **但手動生成的語音必須使用 OGG/Opus 格式**

**快速轉換命令：**
```bash
ffmpeg -i input.mp3 -c:a libopus -b:a 16k -ar 48000 -ac 1 -application voip output.ogg
```

## 晨報內容結構

1. 問候語（根據時間自動調整：早晨/午安/你好）
2. 今日日期與星期
3. **天氣預報**（香港）- 廣東話描述
4. **待辦清單**（最近3項）
5. 即將到期保單提醒
6. 潛客系統提示
7. 祝語

## 使用方式

### 手動生成文字版
```bash
python3 ~/.openclaw/workspace/skills/daily-briefing/scripts/generate_briefing.py
```

### 手動生成廣東話語音
```bash
python3 ~/.openclaw/workspace/skills/daily-briefing/scripts/generate_cantonese_briefing.py
```

### 自動排程
已設定 cron job 每日早上 8:00 執行，自動發送廣東話語音晨報到 WhatsApp

## 待辦事項來源

- `~/.openclaw/workspace/memory/todo.json` - 待辦清單 JSON 文件
- `~/.openclaw/workspace/MEMORY.md` - 「待學習/改進項目」章節

## 天氣資料來源

- wttr.in API（香港）
- 天氣描述自動翻譯為廣東話
