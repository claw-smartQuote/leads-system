#!/bin/bash
# 每日記憶備份腳本
# Daily Memory Backup Script

set -e

# 配置
WORKSPACE_DIR="$HOME/.openclaw/workspace"
BACKUP_DIR="$HOME/.openclaw/backups"
DATE=$(date +"%Y%m%d")
TIME=$(date +"%H%M%S")
BACKUP_NAME="lobster_memory_${DATE}_${TIME}"
RETENTION_DAYS=30

# 創建備份目錄
mkdir -p "$BACKUP_DIR/daily"
mkdir -p "$BACKUP_DIR/monthly"
mkdir -p "$BACKUP_DIR/gold"

echo "🦞 開始備份記憶..."
echo "📂 源目錄: $WORKSPACE_DIR"
echo "💾 備份名: $BACKUP_NAME"

# 創建備份
cd "$WORKSPACE_DIR"

# 使用 tar 創建壓縮備份
tar -czf "$BACKUP_DIR/daily/${BACKUP_NAME}.tar.gz" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='temp/' \
    --exclude='tmp/' \
    .

# 檢查是否為每月1號，如果是則保留月度備份
if [ "$(date +%d)" = "01" ]; then
    cp "$BACKUP_DIR/daily/${BACKUP_NAME}.tar.gz" "$BACKUP_DIR/monthly/monthly_${DATE}.tar.gz"
    echo "📅 月度備份已創建"
fi

# 清理舊的每日備份（保留30天）
find "$BACKUP_DIR/daily" -name "lobster_memory_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# 清理舊的月度備份（保留12個月）
find "$BACKUP_DIR/monthly" -name "monthly_*.tar.gz" -mtime +365 -delete 2>/dev/null || true

# 顯示備份結果
BACKUP_SIZE=$(du -h "$BACKUP_DIR/daily/${BACKUP_NAME}.tar.gz" | cut -f1)
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR/daily"/*.tar.gz 2>/dev/null | wc -l)

echo "✅ 備份完成！"
echo "📦 文件大小: $BACKUP_SIZE"
echo "📊 保留備份: $BACKUP_COUNT 個"
echo "📍 備份位置: $BACKUP_DIR/daily/${BACKUP_NAME}.tar.gz"

# 記錄備份日誌
echo "[$(date)] Backup created: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})" >> "$BACKUP_DIR/backup.log"

exit 0