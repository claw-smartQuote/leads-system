#!/bin/bash

# 🚀 潛客系統一鍵部署腳本
# 使用方法: ./deploy.sh

set -e

echo "🚀 開始部署潛客系統到 Render..."
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 檢查 GitHub SSH key
echo "📋 步驟 1/4: 檢查 GitHub 連接..."
if ! ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "${YELLOW}⚠️  需要配置 GitHub SSH Key${NC}"
    echo ""
    echo "請按以下步驟操作："
    echo ""
    echo "1️⃣  複製你的 SSH 公鑰（已自動生成）："
    echo ""
    cat ~/.ssh/id_ed25519.pub
    echo ""
    echo "2️⃣  訪問 https://github.com/settings/keys"
    echo "3️⃣  點擊 'New SSH key'"
    echo "4️⃣  Title: 填 'MacBook Deploy'"
    echo "5️⃣  Key: 貼上上面的公鑰"
    echo "6️⃣  點擊 'Add SSH key'"
    echo ""
    read -p "完成後按 Enter 繼續..."
    echo ""
fi

# 測試 GitHub 連接
echo "🔍 測試 GitHub 連接..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "${GREEN}✅ GitHub 連接成功！${NC}"
else
    echo "${RED}❌ GitHub 連接失敗，請檢查 SSH Key 設置${NC}"
    exit 1
fi

echo ""

# 詢問 GitHub 用戶名
echo "📋 步驟 2/4: 配置 GitHub 倉庫"
echo ""
read -p "你的 GitHub 用戶名是什麼？ " GITHUB_USER
echo ""

# 檢查倉庫是否存在
echo "🔍 檢查倉庫是否存在..."
if curl -s -o /dev/null -w "%{http_code}" "https://api.github.com/repos/${GITHUB_USER}/leads-system" | grep -q "200"; then
    echo "${YELLOW}⚠️  倉庫已存在，將使用現有倉庫${NC}"
else
    echo "📦 創建 GitHub 倉庫..."
    echo ""
    echo "請手動創建倉庫："
    echo "1. 訪問 https://github.com/new"
    echo "2. Repository name: leads-system"
    echo "3. 選擇 Public（公開）"
    echo "4. 點擊 'Create repository'"
    echo ""
    read -p "完成後按 Enter 繼續..."
fi

echo ""

# 推送代碼
echo "📋 步驟 3/4: 推送代碼到 GitHub..."
cd /Users/claw/.openclaw/workspace/leads_system

# 配置 git
git config user.email "deploy@smartquote.com" 2>/dev/null || true
git config user.name "Deploy Bot" 2>/dev/null || true

# 添加遠程倉庫
git remote remove origin 2>/dev/null || true
git remote add origin "git@github.com:${GITHUB_USER}/leads-system.git"

# 推送
echo "🚀 推送代碼..."
git push -u origin main --force

echo "${GREEN}✅ 代碼推送成功！${NC}"
echo ""

# 生成 Render 部署鏈接
echo "📋 步驟 4/4: 部署到 Render..."
echo ""
echo "${GREEN}🎉 準備完成！${NC}"
echo ""
echo "請點擊以下鏈接完成部署："
echo ""
echo "${YELLOW}https://render.com/deploy?repo=https://github.com/${GITHUB_USER}/leads-system${NC}"
echo ""
echo "點擊鏈接後："
echo "1. 登入 Render（可用 GitHub 賬號）"
echo "2. 點擊 'Apply' 使用配置"
echo "3. 等待 3-5 分鐘部署完成"
echo ""
echo "部署完成後，你會獲得類似這樣的網址："
echo "https://leads-system-xxx.onrender.com"
echo ""
echo "${GREEN}🚀 祝部署順利！${NC}"

# 保存信息
cat > /Users/claw/.openclaw/workspace/leads_system/.deploy_info << EOF
部署信息
========
GitHub 用戶: ${GITHUB_USER}
倉庫地址: https://github.com/${GITHUB_USER}/leads-system
部署鏈接: https://render.com/deploy?repo=https://github.com/${GITHUB_USER}/leads-system
創建時間: $(date)
EOF

echo ""
echo "部署信息已保存到: leads_system/.deploy_info"