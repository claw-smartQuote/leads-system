#!/usr/bin/env python3
"""
Global Session Context Manager
周期性檢查所有會話，自動壓縮過長的會話
"""
import json
import sys
import subprocess
import os

def get_sessions():
    """獲取所有活躍會話"""
    try:
        result = subprocess.run(
            ["openclaw", "sessions", "list", "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting sessions: {e}", file=sys.stderr)
    return None

def should_compact(session_info):
    """判斷會話是否需要壓縮"""
    if not session_info:
        return False
    
    # 檢查消息數量（如果可見）
    messages = session_info.get("messages", [])
    total_tokens = session_info.get("totalTokens", 0)
    
    # 阈值：消息 > 20 或 token > 8000
    return len(messages) > 20 or total_tokens > 8000

def main():
    print("=== Session Context Manager ===")
    
    # 獲取會話列表
    sessions_data = get_sessions()
    
    if not sessions_data or "sessions" not in sessions_data:
        print("No sessions found or error getting sessions")
        return
    
    sessions = sessions_data["sessions"]
    print(f"Found {len(sessions)} sessions")
    
    needs_compact = []
    for s in sessions:
        key = s.get("key", "unknown")
        messages = len(s.get("messages", []))
        tokens = s.get("totalTokens", 0)
        channel = s.get("channel", "unknown")
        status = s.get("status", "unknown")
        
        print(f"  - {key}: {messages} msgs, {tokens} tokens, channel={channel}, status={status}")
        
        if should_compact(s):
            needs_compact.append(key)
    
    if needs_compact:
        print(f"\n⚠️  Sessions needing compact: {len(needs_compact)}")
        for key in needs_compact:
            print(f"  → {key}")
            # 發送壓縮命令
            try:
                subprocess.run(
                    ["openclaw", "agent", "--session", key, "--message", "auto-compact"],
                    timeout=60
                )
            except Exception as e:
                print(f"  Error compacting {key}: {e}", file=sys.stderr)
    else:
        print("\n✅ All sessions within limits")

if __name__ == "__main__":
    main()
