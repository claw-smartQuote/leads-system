# 港車北上資料庫歸檔流程

**技能位置**: `~/.openclaw/workspace/skills/hk-north-insurance-filing/SKILL.md`

**工作流程**:
1. 監控 `~/Desktop/等待命名的/` 發現臨時資料夾自動執行
2. 從 PDF 識別：車牌、客戶名（簡體）、到期月份
3. 建立 `到期月份_車牌_客戶名` 資料夾
4. 複製檔案後**清空臨時資料夾**
5. 移回桌面，權限設為 777

**命名格式**: `02_JC829_赵克宏`（簡體中文）

---

# 客戶資料庫

**位置**: `~/Desktop/港車北上客戶資料庫/`

**命名格式**: `到期月份_車牌號碼_客戶名字`
例如：`03_ABC123_陳大文`

**每個客戶資料夾內容**:
- 投保申請表.pdf
- 保單.pdf
- 報價單.pdf
- 身份證副本.pdf
- 行車証副本.pdf
- 強保險副本.pdf
- 溝通記錄/（跟進WhatsApp記錄）
- 臨時文件/

---

# 知識庫

**本地知識庫**: `/Users/claw/.openclaw/workspace/knowledge_base/`
- 收錄保險條款、投保表格、IIQE教材、費率表、潛客資料等
- 總計 2.3MB+，覆蓋大新/蘇黎世/安聯/立橋保險
- 詳見 `knowledge_base/README.md` 索引

---

# 潛客系統

**線上潛客系統**
- **前台**: https://leads-system.onrender.com/
- **後台**: https://leads-system.onrender.com/admin
- **GitHub**: https://github.com/claw-smartQuote/leads-system
- **部署平台**: Render

---

**FB 爬蟲狀態**
- ❌ 登入狀態過期（權限問題已修復）
- 28car 爬蟲： 110 筆，無需手動登入

---

**長效記憶機制**
- 核心狀態存放於: `long_term_memory.json`
- 每次對話開始先讀取，快速恢復狀態
- 上下文過長時自動觸發代謝壓縮
## 知識庫更新 (2026-03-30)

**已完成學習：**
- 50份文件（PDF + XLSX）已學習並存入知識庫
- 知識庫位置: `memory/knowledge_base_raw.json`
- 摘要位置: `memory/knowledge_summary.md`

**檔案分類：**
- 保險條款（insurance_clauses）: 3份
- 投保表格（application_forms）: 5份
- IIQE考試資料（iqe_exam）: 12份
- 費率表（rate_tables）: 2份
- 保單管理表格（policy_management）: 5份
- 保單樣本（policy_samples）: 1份
- 潛客資料（leads）: 1份
- 其他文件（other）: 15份

**合作保險公司：**
- 大新保險（汽車保險）
- 蘇黎世保險（汽車、電車、電動車、勞工）
- 安聯保險（電動車）
- 立橋保險（汽車）

**IIQE考試覆蓋：**
- Paper 1, Paper 2, Paper 3 試題及精華筆記

## ⚠️ 重要：每日工作流程 (2026-03-30 新增)

**必須熟讀**: `memory/DAILY_WORKFLOW.md`

**每日固定流程**:
1. **FB 爬蟲**: `python3 fb_crawler_final_v5.py`
   - 自動檢查登入狀態
   - 如果過期/超時：運行 `python3 fb_auto_login.py`
2. **Excel 輸出**: 自動生成到 `~/.openclaw/workspace/fb_潛客名單_final.xlsx`
3. **桌面備份**: `cp ~/.openclaw/workspace/fb_潛客名單_final.xlsx ~/Desktop/`
4. **潛客系統**: 同步到 https://leads-system.onrender.com/admin

**FB 登入問題解決方案**:
- 加載超時/登入過期 → `python3 fb_auto_login.py`
- CAPTCHA → 等用戶手動完成
- 備用方案 → 28car 爬蟲（110筆數據，無需登入）

---

# FB 爬蟲核心學習（2026-04-03）

## 關鍵發現

### Facebook 群組帖子結構
1. **帖子以對話框形式打開**
   - CSS selector: `[role="dialog"]`
   - 關閉按鈕: `[aria-label="關閉"]`

2. **留言定位**
   - 留言區塊: `[role="article"]`
   - 用戶連結: `a[href*="/groups/"]` (群組成員)
   - 留言內容: `div[dir="auto"]`

3. **回覆展開**
   - 按鈕文字: `查看 X 則回覆`
   - 正則: `r'查看\s*\d+\s*則回覆'`

4. **對話框內滾動**
   - ❌ `window.scrollTo()` 無效
   - ✅ `page.keyboard.press('ArrowDown')`
   - ✅ 對話框元素聚焦後滾動

### Browser 工具使用技巧
- 重啟瀏覽器: `browser action=stop` → `browser action=start`
- 查找元素: `browser action=snapshot refs=aria`
- 對話框內按鍵: `kind=press key=ArrowDown`

### 替代爬蟲方案
| 方案 | 狀態 | 特點 |
|------|------|------|
| httpx+BeautifulSoup | ✅ 可用 | 簡單頁面、無反機器人 |
| Browser 工具 | ✅ 最佳 | Facebook、需要登入 |
| simple_scraper.py | ✅ 已創建 | 輕量替代方案 |

## 已更新文件
- `skills/browser-automation/SKILL.md` - 加入 FB 爬蟲流程
- `fb_crawler_final_v5.py` - v5.2 版本
- `skills/simple-web-scraper/SKILL.md` - 新技能
- `memory/DAILY_WORKFLOW.md` - 加入學習要點
