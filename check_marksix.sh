#!/bin/bash
# 六合彩票檢查腳本
# 執行時間: 星期二、四、六 晚上 9:00

LOG_FILE="/Users/claw/.openclaw/workspace/logs/marksix_$(date +%Y%m%d).log"
RESULT_FILE="/Users/claw/.openclaw/workspace/logs/marksix_latest.txt"

echo "========================================" >> "$LOG_FILE"
echo "🌟 六合彩票檢查: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 當天的日期
TODAY=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 2=Tuesday, ...

# 檢查今天是否是星期二(2)、四(4)或六(6)
if [ "$DAY_OF_WEEK" != "2" ] && [ "$DAY_OF_WEEK" != "4" ] && [ "$DAY_OF_WEEK" != "6" ]; then
    echo "今日不是開獎日（只在星期二、四、六）" >> "$LOG_FILE"
    exit 0
fi

echo "今天是開獎日，獲取最新結果..." >> "$LOG_FILE"

# 使用 curl 獲取彩票結果
curl -s --max-time 15 "https://www.hkjc.com/chinese/results/results.asp?date=${TODAY}" > "$LOG_FILE" 2>&1

# 如果上面的不行，嘗試備用方法
if ! grep -q "mark six" "$LOG_FILE" 2>/dev/null; then
    echo "嘗試備用來源..." >> "$LOG_FILE"
    curl -s --max-time 15 "https://bet.hkjc.com/marksix/Results.aspx" >> "$LOG_FILE" 2>&1
fi

echo "✅ 檢查完成: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 保存最新結果到單獨文件
tail -50 "$LOG_FILE" > "$RESULT_FILE"
