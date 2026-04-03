#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永诚保险 WhatsApp 报价机器人 - OpenClaw 集成版
通过 systemEvent 接收 WhatsApp 消息并回复
"""

import sys
import json
from whatsapp_bot import WhatsAppInsuranceBot

# 全局机器人实例
bot = WhatsAppInsuranceBot()

def handle_incoming_message(user_id: str, message: str) -> str:
    """
    处理接收到的 WhatsApp 消息
    
    此函数被 OpenClaw 的 systemEvent 调用
    """
    try:
        # 处理消息
        reply = bot.handle_message(user_id, message)
        return reply
    except Exception as e:
        return f"❌ 处理消息时出错: {str(e)}"


if __name__ == "__main__":
    # 测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("=== WhatsApp 报价机器人 - 测试模式 ===\n")
        
        test_cases = [
            ("+85212345678", "报价 粤B12345 燃油车 6座以下个人 4人 300万"),
            ("+85287654321", "報價 港車A123 新能源車 6座以下個人 4人 200萬"),
            ("+85211111111", "帮助"),
        ]
        
        for user_id, message in test_cases:
            print(f"来自 {user_id}: {message}")
            print("-" * 50)
            reply = handle_incoming_message(user_id, message)
            print(reply)
            print("\n" + "=" * 60 + "\n")
    
    else:
        print("使用方法:")
        print("  python3 openclaw_bot.py --test    # 运行测试")
        print("")
        print("在 OpenClaw 中配置 systemEvent:")
        print('  payload: { kind: "agentTurn", message: "处理报价请求" }')
