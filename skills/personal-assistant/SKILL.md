---
name: personal-assistant
description: Personal assistant for managing reminders, todos, bills, account expirations, important dates, and anniversaries. Use when user needs help with personal life management, task reminders, bill payments, subscription renewals, account expiration alerts, or anniversary tracking. Integrates with cron for automated notifications via WhatsApp. Enhanced with Mem0 for intelligent memory management.
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

### 🧠 Intelligent Memory (智能記憶) — NEW!

**Mem0 集成** — 增强的记忆系统，让 AI 记得更多、记得更准。

#### 功能
- 自然语言记忆存储和检索
- 客户偏好和历史自动记忆
- 报价记录永久保存
- 语义搜索，而非关键词匹配

#### 设置 (首次使用)
```bash
# 1. 安装 mem0ai
pip install mem0ai

# 2. 获取 API key
#    访问 https://app.mem0.ai/dashboard/settings?tab=api-keys

# 3. 设置环境变量
export MEM0_API_KEY="your-api-key-here"
```

#### 使用方式

**命令式记忆:**
```
记住：[重要信息]
```

**自动记忆客户:**
```bash
python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/memory_manager.py client "张先生" -v "燃油车" -p "300万三者"
```

**搜索记忆:**
```bash
python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/memory_manager.py search "张先生"
```

**记忆报价:**
```bash
python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/memory_manager.py quote "粤B12345" -t 5000 -T "燃油车" -c "300万三者+医保外"
```

**查看状态:**
```bash
python3 ~/.openclaw/workspace/skills/personal-assistant/scripts/memory_manager.py status
```

## Data Storage

**提醒数据:**
```
~/.openclaw/workspace/memory/personal_reminders.json
```

**记忆数据 (Mem0 Cloud 或本地):**
- 云端: Mem0 托管平台 (需要 API key)
- 本地回退: `~/.openclaw/workspace/memory/personal_memories.json`

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

### `scripts/memory_manager.py` — NEW!
Mem0 记忆管理:
```bash
# 添加记忆
memory_manager.py add "用户喜欢300万三者险" -c preference

# 搜索记忆
memory_manager.py search "客户偏好"

# 列出所有记忆
memory_manager.py list

# 记忆客户
memory_manager.py client "李先生" -v "新能源车" -p "200万"

# 记忆报价
memory_manager.py quote "粤Z8888" -t 6500 -T "燃油车" -c "300万三者"

# 搜索客户历史
memory_manager.py history client "李先生"

# 搜索报价历史
memory_manager.py history plate "粤B12345"

# 检查 mem0 状态
memory_manager.py status
```

### `scripts/mem0_integration.py` — NEW!
Mem0 Python API，可直接在代码中使用:
```python
from mem0_integration import add_memory, search_memories, remember_client

# 添加记忆
add_memory("用户住在香港，主要开粤港两地牌车", metadata={"category": "preference"})

# 搜索
results = search_memories("两地牌车")

# 记忆客户
remember_client("王先生", {"vehicle": "两地牌", "coverage": "300万"}, "有小孩，考虑安全座椅")
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

**User:** "李先生之前问过报价，记得他的偏好"
→ Remember client preferences via mem0

**User:** "之前给张先生报的什么价？"
→ Search quote history via mem0

## Integration with Existing Systems

- Uses `cron` for scheduled notifications
- Sends WhatsApp alerts via `message` tool
- Stores data in `memory/` folder
- **NEW**: Uses Mem0 for semantic memory and intelligent recall
- Can sync with Apple Reminders via `apple-reminders` skill if needed

## Mem0 vs 本地存储

| 功能 | Mem0 (推荐) | 本地 JSON |
|------|-------------|-----------|
| 语义搜索 | ✅ | ❌ (仅关键词) |
| 需要网络 | ✅ | ❌ |
| 需要 API key | ✅ (免费额度) | ❌ |
| 本地离线 | ❌ | ✅ |
| 容量 | 无限制 | 受文件大小限制 |

**推荐**: 使用 Mem0 作为主要记忆存储，本地 JSON 作为离线备份。
