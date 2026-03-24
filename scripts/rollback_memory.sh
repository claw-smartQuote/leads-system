#!/bin/bash
# 一鍵回滾腳本
# One-Click Rollback Script

set -e

WORKSPACE_DIR="$HOME/.openclaw/workspace"
BACKUP_DIR="$HOME/.openclaw/backups"

echo "🦞 龍蝦記憶回滾系統"
echo "===================="
echo ""

# 顯示最近的備份
echo "📂 最近的備份文件:"
echo ""

# 每日備份
if [ -d "$BACKUP_DIR/daily" ] && [ "$(ls -A $BACKUP_DIR/daily/*.tar.gz 2>/dev/null)" ]; then
    echo "【每日備份】"
    ls -1t "$BACKUP_DIR/daily"/*.tar.gz 2>/dev/null | head -10 | while read -r file; do
        filename=$(basename "$file")
        size=$(du -h "$file" | cut -f1)
        date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1)
        echo "  • $filename ($size) - $date"
    done
    echo ""
fi

# 月度備份
if [ -d "$BACKUP_DIR/monthly" ] && [ "$(ls -A $BACKUP_DIR/monthly/*.tar.gz 2>/dev/null)" ]; then
    echo "【月度備份】"
    ls -1t "$BACKUP_DIR/monthly"/*.tar.gz 2>/dev/null | head -5 | while read -r file; do
        filename=$(basename "$file")
        size=$(du -h "$file" | cut -f1)
        date=$(stat -f "%Sm" -t "%Y-%m-%d" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1)
        echo "  • $filename ($size) - $date"
    done
    echo ""
fi

# 金牌備份
if [ -d "$BACKUP_DIR/gold" ] && [ "$(ls -A $BACKUP_DIR/gold/*.tar.gz 2>/dev/null)" ]; then
    echo "【金牌初始檔】"
    ls -1t "$BACKUP_DIR/gold"/*.tar.gz 2>/dev/null | while read -r file; do
        filename=$(basename "$file")
        size=$(du -h "$file" | cut -f1)
        echo "  ⭐ $filename ($size)"
    done
    echo ""
fi

# 讓用戶選擇
read -p "請輸入要恢復的備份文件名（或完整路徑）: " BACKUP_FILE

# 如果用戶只輸入文件名，補全路徑
if [ ! -f "$BACKUP_FILE" ]; then
    if [ -f "$BACKUP_DIR/daily/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/daily/$BACKUP_FILE"
    elif [ -f "$BACKUP_DIR/monthly/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/monthly/$BACKUP_FILE"
    elif [ -f "$BACKUP_DIR/gold/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/gold/$BACKUP_FILE"
    fi
fi

# 檢查文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 錯誤: 找不到備份文件: $BACKUP_FILE"
    exit 1
fi

echo ""
echo "⚠️  警告: 這將覆蓋當前的工作空間！"
echo "📦 備份文件: $BACKUP_FILE"
echo "📂 目標目錄: $WORKSPACE_DIR"
echo ""

read -p "確定要回滾嗎？輸入 'ROLLBACK' 確認: " CONFIRM

if [ "$CONFIRM" != "ROLLBACK" ]; then
    echo "❌ 已取消回滾操作"
    exit 0
fi

# 創建當前狀態的緊急備份
echo ""
echo "🔄 正在創建當前狀態的緊急備份..."
EMERGENCY_BACKUP="$BACKUP_DIR/emergency_$(date +%Y%m%d_%H%M%S).tar.gz"
cd "$WORKSPACE_DIR"
tar -czf "$EMERGENCY_BACKUP" . 2>/dev/null || true
echo "✅ 緊急備份已創建: $EMERGENCY_BACKUP"

# 執行回滾
echo ""
echo "🔄 正在回滾..."

# 清空當前目錄（保留備份腳本）
cd "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/.temp_backup"
mv scripts "$WORKSPACE_DIR/.temp_backup/" 2>/dev/null || true
rm -rf * .[^.]* 2>/dev/null || true
mv "$WORKSPACE_DIR/.temp_backup/scripts" . 2>/dev/null || true
rmdir "$WORKSPACE_DIR/.temp_backup" 2>/dev/null || true

# 解壓備份
tar -xzf "$BACKUP_FILE" -C "$WORKSPACE_DIR"

echo ""
echo "✅ 回滾完成！"
echo ""
echo "📝 接下來的操作:"
echo "  1. 重啟 OpenClaw Gateway: openclaw gateway restart"
echo "  2. 檢查系統狀態: openclaw doctor"
echo "  3. 與我對話，確認記憶恢復正常"
echo ""
echo "💡 提示: 如果回滾後有問題，可以從緊急備份恢復:"
echo "  $EMERGENCY_BACKUP"

exit 0