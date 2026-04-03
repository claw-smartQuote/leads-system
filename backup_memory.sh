#!/bin/bash
# 記憶備份腳本 - 防止失憶
# 每天自動備份 MEMORY.md 和記憶文件

BACKUP_DIR="$HOME/.openclaw/backups/daily"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 備份 MEMORY.md
if [ -f "$HOME/.openclaw/workspace/MEMORY.md" ]; then
    cp "$HOME/.openclaw/workspace/MEMORY.md" "$BACKUP_DIR/MEMORY_${TIMESTAMP}.md"
    echo "[$(date)] MEMORY.md 已備份到 $BACKUP_DIR/MEMORY_${TIMESTAMP}.md" >> "$BACKUP_DIR/backup.log"
fi

# 備份記憶數據庫
if [ -f "$HOME/.openclaw/memory/main.sqlite" ]; then
    cp "$HOME/.openclaw/memory/main.sqlite" "$BACKUP_DIR/memory_${TIMESTAMP}.sqlite"
    echo "[$(date)] 記憶數據庫已備份" >> "$BACKUP_DIR/backup.log"
fi

# 備份工作區
if [ -d "$HOME/.openclaw/workspace" ]; then
    tar -czf "$BACKUP_DIR/workspace_${TIMESTAMP}.tar.gz" -C "$HOME/.openclaw" workspace
    echo "[$(date)] 工作區已備份" >> "$BACKUP_DIR/backup.log"
fi

# 清理舊備份（保留30天）
find "$BACKUP_DIR" -name "*.md" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.sqlite" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] 備份完成" >> "$BACKUP_DIR/backup.log"
