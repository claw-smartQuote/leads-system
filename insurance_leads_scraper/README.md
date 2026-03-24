# 整合爬蟲系統 - 使用說明

## 📦 系統概述

全自動爬蟲系統，每日自動從 28car.com 和 Facebook 抓取潛在客戶數據。

---

## ✅ 已完成功能

### 1. 定時任務 (Cron Job)
- **執行時間**: 每天上午 9:00
- **自動觸發**: 無需人工干預
- **日誌記錄**: 每次執行都有詳細日誌

### 2. 數據量保證
- **目標**: 每天至少 100 條有效數據
- **自動翻頁**: 28car 自動翻頁直到達標
- **多源整合**: 28car (電話) + Facebook (潛客名單)

### 3. 28car.com 模塊
- ✅ 抓取最新車源
- ✅ 提取 8 位數香港電話
- ✅ 識別車型
- ✅ 自動去重

### 4. Facebook 模塊
- ✅ 訪問指定社團
- ✅ 關鍵詞識別（車險、買車、賣車等）
- ✅ 使用 undetected-chromedriver
- ✅ 加載本地 Chrome 登錄狀態

### 5. 防封鎖機制
- ✅ 自動重試 (錯誤重試 3 次)
- ✅ 錯誤恢復 (瀏覽器崩潰自動重啟)
- ✅ 隨機等待 (2-5 秒隨機延遲)
- ✅ 模擬真人行為

### 6. 數據輸出
- **原始數據_YYYYMMDD.xlsx**: 包含所有字段
- **清洗後電話_YYYYMMDD.xlsx**: 僅包含 8 位數電話

---

## 📁 文件結構

```
insurance_leads_scraper/
├── daily_scraper.py      # 主爬蟲腳本
├── install.sh            # 安裝腳本
├── run_now.sh            # 手動執行腳本
├── logs/                 # 日誌目錄
└── README.md             # 本文件
```

---

## 🚀 使用方法

### 方法一：自動執行（推薦）
系統會在每天 9:00 自動執行，無需人工干預。

### 方法二：手動執行
```bash
cd /Users/claw/.openclaw/workspace/insurance_leads_scraper
./run_now.sh
```

或直接運行：
```bash
python3 daily_scraper.py
```

---

## ⚙️ 管理定時任務

### 查看當前任務
```bash
crontab -l
```

### 編輯定時任務
```bash
crontab -e
```

### 刪除定時任務
```bash
crontab -r
```

---

## 📊 輸出文件位置

所有 Excel 文件保存在：
```
~/Desktop/汽車保險潛客數據/
├── 原始數據_YYYYMMDD.xlsx
├── 清洗後電話_YYYYMMDD.xlsx
└── daily_scraper_YYYYMMDD.db
```

---

## 🔧 故障排除

### 問題 1: Playwright 未安裝
```bash
pip3 install playwright
python3 -m playwright install chromium
```

### 問題 2: undetected-chromedriver 未安裝
```bash
pip3 install undetected-chromedriver
```

### 問題 3: 瀏覽器啟動失敗
- 確保 Chrome 已安裝
- 首次運行需要登錄 Facebook

---

## 📋 首次運行檢查清單

- [ ] 安裝 Python 依賴 (pandas, playwright, undetected-chromedriver)
- [ ] 設置 Cron Job
- [ ] 登錄 Facebook (保存登錄狀態)
- [ ] 測試運行一次
- [ ] 檢查輸出文件

---

## 🎯 數據流程

1. **啟動** → 初始化數據庫
2. **爬取 28car** → 收集電話直到達標或無更多數據
3. **爬取 Facebook** → 補充數據（如未達標）
4. **去重清洗** → 去除重複數據
5. **導出 Excel** → 生成兩個 Excel 文件
6. **完成** → 記錄日誌

---

系統版本: 2.0
最後更新: 2026-03-17
