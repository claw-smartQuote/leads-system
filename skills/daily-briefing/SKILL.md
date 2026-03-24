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
- 輸出格式：`audio-24khz-48kbitrate-mono-mp3`

**相關檔案：**
- `scripts/generate_briefing.py` - 生成晨報文字內容
- `scripts/generate_cantonese_briefing.py` - 生成廣東話語音
- `scripts/cantonese_tts.py` - 廣東話 TTS 引擎

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
