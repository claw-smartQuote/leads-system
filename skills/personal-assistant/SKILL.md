---
name: personal-assistant
description: Personal assistant for managing reminders, todos, bills, account expirations, important dates, and anniversaries. Use when user needs help with personal life management, task reminders, bill payments, subscription renewals, account expiration alerts, important event reminders, or anniversary tracking. Integrates with cron for automated notifications via WhatsApp.
---

# Personal Assistant (私人秘書)

Your personal secretary for managing life's important dates and tasks.

## Capabilities

### 📋 Task Management (待辦事項)
- Create, track, and manage personal todos
- Set priority levels and due dates
- Mark tasks as complete

### 💰 Bill Reminders (帳單到期)
- Credit card payments
- Utility bills (electricity, water, gas)
- Rent/mortgage payments
- Insurance premiums
- Loan payments

### 🔐 Account Expiration (賬號到期)
- Domain renewals
- Software licenses
- Subscription services
- Membership renewals

### ⭐ Important Events (重要事項)
- Medical appointments
- Visa/passport renewals
- Car inspections
- Tax deadlines

### 🎉 Anniversaries (紀念日)
- Birthdays
- Wedding anniversaries
- Special dates

## Data Storage

All reminders are stored in:
```
~/.openclaw/workspace/memory/personal_reminders.json
```

Format:
```json
{
  "tasks": [...],
  "bills": [...],
  "accounts": [...],
  "events": [...],
  "anniversaries": [...]
}
```

## Workflows

### Adding a New Reminder

1. Determine reminder type (task/bill/account/event/anniversary)
2. Collect required information
3. Save to reminders database
4. Set up cron job for notification if needed
5. Confirm with user

### Daily Check

Run every morning to check for upcoming reminders:
```bash
python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/check_reminders.py
```

## Scripts

### `scripts/check_reminders.py`
Daily check script that:
- Reads all reminders from database
- Identifies items due today/tomorrow/this week
- Sends WhatsApp notifications
- Updates reminder status

### `scripts/add_reminder.py`
Add new reminder:
```bash
python3 add_reminder.py --type bill --name "Credit Card" --amount 5000 --due 2026-03-25 --repeat monthly
```

### `scripts/list_reminders.py`
List all reminders:
```bash
python3 list_reminders.py --type all --status pending
```

## Cron Setup

Set up daily check at 9:00 AM:
```json
{
  "schedule": {"expr": "0 9 * * *", "kind": "cron", "tz": "Asia/Shanghai"},
  "payload": {
    "kind": "agentTurn",
    "message": "Run personal assistant daily check: python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/check_reminders.py"
  }
}
```

## Example Interactions

**User:** "提醒我3月25號還信用卡"
→ Add bill reminder for March 25

**User:** "我的域名3個月後到期"
→ Add account expiration reminder

**User:** "下個月15號有醫生預約"
→ Add important event reminder

**User:** "記住我媽媽生日是5月20號"
→ Add anniversary reminder

## Integration with Existing Systems

- Uses `cron` for scheduled notifications
- Sends WhatsApp alerts via `message` tool
- Stores data in `memory/` folder
- Can sync with Apple Reminders via `apple-reminders` skill if needed