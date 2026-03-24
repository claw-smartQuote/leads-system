#!/bin/bash
# 創建金牌初始檔
# Create Gold Master Backup

set -e

WORKSPACE_DIR="$HOME/.openclaw/workspace"
BACKUP_DIR="$HOME/.openclaw/backups"

echo "⭐ 創建金牌初始檔"
echo "=================="
echo ""
echo "這將保存當前狀態作為「完美調教初期」的備份。"
echo ""

read -p "請為這個金牌檔本命名 (例如: v1.0_perfect): " GOLD_NAME

if [ -z "$GOLD_NAME" ]; then
    GOLD_NAME="gold_master_$(date +%Y%m%d)"
fi

mkdir -p "$BACKUP_DIR/gold"

cd "$WORKSPACE_DIR"
tar -czf "$BACKUP_DIR/gold/${GOLD_NAME}.tar.gz" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='temp/' \
    --exclude='tmp/' \
    .

SIZE=$(du -h "$BACKUP_DIR/gold/${GOLD_NAME}.tar.gz" | cut -f1)

echo ""
echo "✅ 金牌初始檔已創建！"
echo "📦 文件名: ${GOLD_NAME}.tar.gz"
echo "💾 大小: $SIZE"
echo "📍 位置: $BACKUP_DIR/gold/"
echo ""
echo "💡 這個備份將永久保留，不會被自動清理。"

exit 0