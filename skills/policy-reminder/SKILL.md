---
name: policy-reminder
description: Insurance policy management and renewal reminder system. Use when the user needs to (1) Import policy data from Excel files, (2) Add policy expiration dates to calendar, (3) Check upcoming policy renewals, (4) Send WhatsApp reminders for policy renewals, (5) Schedule automated daily checks for expiring policies, or (6) Track insurance policy status.
metadata:
  {
    "openclaw":
      {
        "emoji": "📋",
        "requires": { "bins": ["python3"] },
      },
  }
---

# 保單到期提醒系統

自動化管理保單到期日，並在 WhatsApp 上發送提醒。

## 功能

1. **讀取保單數據** - 從 Excel 文件導入
2. **添加日曆事件** - 將到期日加入 Apple 日曆
3. **檢查即將到期** - 篩選指定天數內到期的保單
4. **發送提醒** - 通過 WhatsApp 發送到期提醒
5. **自動化檢查** - 每天自動檢查並發送提醒

## 使用方式

### 1. 導入保單數據

```bash
python3 {baseDir}/scripts/policy_manager.py import /path/to/policy.xlsx --owner "李先生"
```

### 2. 添加到日曆

```bash
python3 {baseDir}/scripts/policy_manager.py add-to-calendar --days-before 7
```

### 3. 檢查即將到期的保單

```bash
python3 {baseDir}/scripts/policy_manager.py check --days 30
```

### 4. 發送 WhatsApp 提醒

```bash
python3 {baseDir}/scripts/policy_manager.py send-reminders --days 30 --to "+85212345678"
```

### 5. 一鍵執行（檢查+發送）

```bash
python3 {baseDir}/scripts/policy_manager.py auto --days 30 --to "+85212345678"
```

## 數據存儲

保單數據保存在 `memory/policies.json`，格式：
```json
{
  "policies": [
    {
      "id": "uuid",
      "issue_date": "2024-05-22",
      "expiry_date": "2024-06-11",
      "agent": "李先生",
      "insurer": "永城",
      "plate_number": "粤Z17G5港",
      "insured_name": "梁佩仪",
      "reminder_sent": false
    }
  ]
}
```

## 自動化設置

設置每天自動檢查（使用 OpenClaw cron）：

```bash
# 添加到 HEARTBEAT.md 或設置 cron 任務
openclaw cron add policy-check "每天檢查保單到期並發送提醒"
```