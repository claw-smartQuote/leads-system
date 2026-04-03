#!/usr/bin/env python3
"""Brave Search API 配額管理器 - 每月 800 請求限制"""

import json
import os
import sys
from datetime import datetime

QUOTA_FILE = os.path.expanduser("~/.openclaw/.brave_quota.json")
MONTHLY_LIMIT = 800

THRESHOLDS = {
    "normal": 0.50,   # < 50%
    "caution": 0.75,  # 50-75%
    "warning": 0.90,  # 75-90%
    # > 90% = critical
}

def load_quota():
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    default = {"month": current_month, "count": 0, "limit": MONTHLY_LIMIT, "log": []}

    if not os.path.exists(QUOTA_FILE):
        return default

    try:
        with open(QUOTA_FILE, "r") as f:
            data = json.load(f)
        # Auto-reset if new month
        if data.get("month") != current_month:
            data["month"] = current_month
            data["count"] = 0
            data["log"] = []
            data["limit"] = MONTHLY_LIMIT
            save_quota(data)
        return data
    except (json.JSONDecodeError, KeyError):
        return default

def save_quota(data):
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_status_emoji(usage_ratio):
    if usage_ratio < THRESHOLDS["normal"]:
        return "🟢"
    elif usage_ratio < THRESHOLDS["caution"]:
        return "🟡"
    elif usage_ratio < THRESHOLDS["warning"]:
        return "🟠"
    else:
        return "🔴"

def status():
    data = load_quota()
    count = data["count"]
    limit = data.get("limit", MONTHLY_LIMIT)
    remaining = max(0, limit - count)
    ratio = count / limit if limit > 0 else 1.0
    emoji = get_status_emoji(ratio)

    print(f"{emoji} Brave Search 配額狀態 ({data['month']})")
    print(f"   已使用: {count}/{limit} ({ratio:.1%})")
    print(f"   剩餘:   {remaining}")

    if ratio >= THRESHOLDS["warning"]:
        print(f"   ⚠️  配額即將用盡！建議減少搜索頻率")
    elif ratio >= THRESHOLDS["caution"]:
        print(f"   ℹ️  已超過 75%，請注意使用量")

    return {"count": count, "limit": limit, "remaining": remaining, "ratio": ratio, "blocked": count >= limit}

def log_request(query=""):
    data = load_quota()
    limit = data.get("limit", MONTHLY_LIMIT)

    if data["count"] >= limit:
        print(f"🔴 配額已用盡！本月已達 {limit} 次上限")
        return False

    data["count"] += 1
    data["log"].append({
        "time": datetime.now().isoformat(),
        "query": query[:100] if query else ""
    })
    # Keep only last 50 log entries to save space
    if len(data["log"]) > 50:
        data["log"] = data["log"][-50:]

    save_quota(data)

    remaining = limit - data["count"]
    ratio = data["count"] / limit
    emoji = get_status_emoji(ratio)
    print(f"{emoji} 搜索已記錄 ({data['count']}/{limit}，剩餘 {remaining})")
    return True

def check():
    """Check if quota allows a request. Returns exit code 0 if OK, 1 if blocked."""
    data = load_quota()
    limit = data.get("limit", MONTHLY_LIMIT)
    if data["count"] >= limit:
        print(f"BLOCKED: {data['count']}/{limit}")
        sys.exit(1)
    else:
        remaining = limit - data["count"]
        print(f"OK: {data['count']}/{limit} (remaining: {remaining})")
        sys.exit(0)

def reset():
    now = datetime.now()
    data = {"month": now.strftime("%Y-%m"), "count": 0, "limit": MONTHLY_LIMIT, "log": []}
    save_quota(data)
    print(f"✅ 配額已重置 (0/{MONTHLY_LIMIT})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "status":
        status()
    elif cmd == "log":
        log_request(query)
    elif cmd == "check":
        check()
    elif cmd == "reset":
        reset()
    else:
        print(f"用法: {sys.argv[0]} [status|log|check|reset]")
