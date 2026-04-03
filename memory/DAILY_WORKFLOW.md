# 🦞 AI小龍蝦 - 每日工作流程

_最後更新: 2026-03-30_

---

## ⚠️ 核心優先序

**每次對話開始，必須第一時間讀取呢個文件！**

---

## 🔄 每日固定工作流程

### 1. FB 爬蟲執行流程

**目標**: 每日執行一次 FB 爬蟲，目標 50 個潛客

**完整流程**:

```
1. 執行 FB 爬蟲（自動檢查登入狀態）:
   cd ~/.openclaw/workspace && python3 fb_crawler_final_v5.py

2. 如果提示「登入狀態過期」或「加載超時」:
   → 運行自動登入腳本: python3 fb_auto_login.py
   → 如果有 CAPTCHA，停低等用戶完成
   → 無 CAPTCHA 就自動完成

3. 爬蟲完成後，自動生成 Excel（日期命名）:
   → 輸出位置: ~/.openclaw/workspace/fb_潛客_YYYYMMDD.xlsx
   → 例如: fb_潛客_20260330.xlsx

4. 匯出到桌面備份:
   → 指令: cp ~/.openclaw/workspace/fb_潛客_$(date +%Y%m%d).xlsx ~/Desktop/
```

**Excel 命名格式**: `fb_潛客_YYYYMMDD.xlsx`（加入年月日在文件名）

---

### 1.1 FB 爬蟲核心學習（2026-04-03 更新）

**Facebook 頁面結構關鍵發現**:

1. **群組帖子打開為對話框**
   - 特徵：`[role="dialog"]` 覆蓋層
   - 關閉按鈕：`[aria-label="關閉"]`

2. **留言在 article 元素內**
   - 定位：`[role="article"]` = 留言區塊
   - 用戶連結：`a[href*="/groups/"]` 或 `a[href*="facebook.com"]`
   - 留言內容：`div[dir="auto"]`

3. **需要展開回覆**
   - 按鈕文字：`查看 X 則回覆`、`View X replies`
   - 正則匹配：`r'查看\s*\d+\s*則回覆'`

4. **對話框內滾動**
   - ❌ 不能用 `window.scrollTo()` 
   - ✅ 用鍵盤：`page.keyboard.press('ArrowDown')`
   - 對話框元素用 `locator('[role="dialog"]')` 定位

5. **動態加載**
   - 等待 1-2 秒讓內容加載
   - 觀察 "載入中..." 提示消失

**手動提取流程（Browser 工具）**:
```
1. browser action=open targetUrl=<post_url>
2. browser action=snapshot refs=aria  (找到 dialog ref)
3. 點擊 "查看 X 則回覆" 按鈕
4. 對話框內多次按 ArrowDown
5. 重複 3-4 直到所有留言加載
6. 提取 [role="article"] 內容保存
```

**FB 爬蟲相關檔案**:
| 檔案 | 用途 |
|------|------|
| `fb_crawler_final_v5.py` | 主爬蟲腳本 |
| `fb_auto_login.py` | 自動登入 |
| `fb_login.py` | 手動登入（備用）|
| `~/.fb_crawler/fb_storage_state.json` | FB cookies（登入狀態）|
| `~/.fb_crawler/fb_credentials.json` | FB 憑證（電郵/密碼）|

**已知問題及解決方案**:
- ❌ **「加載超時」** → cookies 過期，運行 `python3 fb_auto_login.py` 刷新
- ❌ **「登入狀態過期」** → 同上，刷新 cookies
- ❌ **CAPTCHA** → 瀏覽器彈出，等用戶手動完成後自動繼續
- ❌ **FB 拒絕訪問** → IP 或賬號被限流，等 24 小時后再试

---

### 2. 潛客系統同步

**爬蟲完成後，同步到線上系統**:

```
前端: https://leads-system.onrender.com/
後台: https://leads-system.onrender.com/admin
```

**同步方法**:
1. 打開後台 admin 頁面
2. 手動上傳 Excel 或使用 API
3. 確認數據入庫

---

### 3. 28car 爬蟲（備用方案）

如果 FB 爬蟲無法使用，採用 28car 備用:

**狀態**: 110 筆資料，無需登入，可直接使用

**匯出**:
```bash
sqlite3 ~/.openclaw/workspace/fb_leads_final.db "SELECT * FROM fb_leads;" > ~/Desktop/28car_leads.csv
```

---

### 4. 記憶備份

**每日必須執行**:
```bash
bash ~/.openclaw/workspace/backup_memory.sh
```

**備份時間**: 凌晨 2:00（自動）, 或手動觸發

---

## 📁 關鍵配置位置

| 項目 | 位置 |
|------|------|
| FB 登入狀態 | `~/.fb_crawler/fb_storage_state.json` |
| FB 憑證 | `~/.fb_crawler/fb_credentials.json` |
| 爬蟲腳本 | `~/.openclaw/workspace/fb_crawler_final_v5.py` |
| 自動登入 | `~/.openclaw/workspace/fb_auto_login.py` |
| 知識庫 | `~/.openclaw/workspace/memory/knowledge_base_raw.json` |
| 每日工作記錄 | `~/.openclaw/workspace/memory/YYYY-MM-DD.md` |
| 長期記憶 | `~/.openclaw/workspace/MEMORY.md` |

---

## 🤖 自動化了嗎？

| 任務 | 自動化狀態 |
|------|-----------|
| 整合爬蟲 (28car+FB) | ✅ 每日 8:00 AM 自動執行 |
| FB 爬蟲 | ⚠️ Facebook 封鎖伺服器 IP，28car 為主 |
| 28car 爬蟲 | ✅ 每日 8:00 AM 自動執行（~125筆/日）|
| 潛客系統同步 | ✅ API 自動上傳（每日 23:00）|
| 港車北上報價健康檢查 | ✅ 每日 9:00 AM |
| 六合彩票檢查 | ✅ 星期二/四/六 21:00 (web_search) |
| 每日晨報 | ✅ 每日 10:30 AM |
| 記憶備份 | ✅ 凌晨 2:00 自動 |

---

## 🔧 常見問題解決

### FB 爬蟲超時
```
原因: cookies 過期或 FB 拒絕連接
解決: python3 fb_auto_login.py
```

### FB 頁面加載失敗
```
原因: 網絡問題或 FB 限制
解決: 
1. 等待幾分鐘後重試
2. 檢查 ~/.fb_crawler/fb_storage_state.json 是否存在
3. 使用 28car 備用
```

### 登入後立即過期
```
原因: FB 檢測到異常登入
解決: 
1. 手動登入一次: python3 fb_login.py
2. 完成後等待幾分鐘再執行爬蟲
```

---

*記住：呢個文件係你嘅生存指南，每日對話開始必須讀取！*
