#!/bin/bash
# 每日晨報語音發送腳本

BRIEFING=$(python3 ~/.openclaw/workspace/skills/daily-briefing/scripts/generate_briefing.py)

# 使用 TTS 發送語音
# 注意：此腳本需要由 OpenClaw agent 執行才能使用 TTS 功能

echo "$BRIEFING"
