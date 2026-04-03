#!/usr/bin/env python3
"""
Personal Assistant Memory Manager
==================================
个人助理记忆管理器 - 使用 Mem0 增强记忆

功能:
- 命令行记忆管理
- 自动记忆重要对话
- 搜索记忆历史
- 记忆客户和报价信息
"""

import sys
import os
import json
import argparse

# 添加脚本目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mem0_integration import (
    add_memory, search_memories, get_all_memories,
    remember_client, remember_quote_result, remember_preference,
    search_client_history, search_quote_history,
    check_status, MEM0_AVAILABLE
)

def cmd_add(args):
    """添加记忆"""
    metadata = {}
    if args.category:
        metadata["category"] = args.category
    if args.client:
        metadata["client_name"] = args.client
    
    success = add_memory(args.content, metadata=metadata if metadata else None)
    if success:
        print("✅ 记忆已添加")
    else:
        print("⚠️ 记忆已保存到本地存储（mem0 未可用）")

def cmd_search(args):
    """搜索记忆"""
    results = search_memories(args.query, limit=args.limit)
    
    if not results:
        print("沒有找到相關記憶")
        return
    
    print(f"找到 {len(results)} 條記憶:\n")
    for i, r in enumerate(results, 1):
        memory = r.get("memory", "")
        cat = r.get("metadata", {}).get("category", "general")
        print(f"{i}. [{cat}] {memory}")
        print()

def cmd_list(args):
    """列出所有记忆"""
    memories = get_all_memories()
    
    if not memories:
        print("暫無記憶")
        return
    
    print(f"共有 {len(memories)} 條記憶:\n")
    for i, m in enumerate(memories, 1):
        cat = m.get("metadata", {}).get("category", "general")
        mem = m.get("memory", "")[:80]
        created = m.get("created_at", "")[:10]
        print(f"{i}. [{cat}] {mem}... ({created})")

def cmd_client(args):
    """记忆客户信息"""
    preferences = {}
    if args.vehicle_type:
        preferences["vehicle_type"] = args.vehicle_type
    if args.preferred_coverage:
        preferences["preferred_coverage"] = args.preferred_coverage
    
    notes = args.notes or ""
    remember_client(args.name, preferences, notes)
    print(f"✅ 客户 {args.name} 的信息已记忆")

def cmd_quote(args):
    """记忆报价结果"""
    quote_data = {
        "vehicle_type": args.vehicle_type,
        "total_premium": args.total,
        "coverage": args.coverage
    }
    remember_quote_result(args.plate, quote_data)
    print(f"✅ 车牌 {args.plate} 报价已记忆")

def cmd_status(args):
    """检查状态"""
    status = check_status()
    print("📊 Mem0 集成状态:\n")
    for key, value in status.items():
        key_name = key.replace("_", " ").title()
        print(f"  {key_name}: {value}")

def cmd_history(args):
    """搜索历史"""
    if args.type == "client":
        results = search_client_history(args.name)
        print(f"📋 客户 {args.name} 的历史记录:\n")
    elif args.type == "plate":
        results = search_quote_history(args.plate)
        print(f"🚗 车牌 {args.plate} 的报价历史:\n")
    
    if not results:
        print("沒有找到記錄")
        return
    
    for r in results:
        print(f"  • {r.get('memory', '')[:100]}...")

def main():
    parser = argparse.ArgumentParser(description="Personal Assistant Memory Manager")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # add - 添加记忆
    add_parser = subparsers.add_parser("add", help="添加新记忆")
    add_parser.add_argument("content", help="记忆内容")
    add_parser.add_argument("-c", "--category", help="分类 (client/quote/preference/general)")
    add_parser.add_argument("-C", "--client", help="关联客户名")
    
    # search - 搜索记忆
    search_parser = subparsers.add_parser("search", help="搜索记忆")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("-l", "--limit", type=int, default=5, help="返回数量")
    
    # list - 列出所有记忆
    list_parser = subparsers.add_parser("list", help="列出所有记忆")
    
    # client - 记忆客户
    client_parser = subparsers.add_parser("client", help="记忆客户信息")
    client_parser.add_argument("name", help="客户名称")
    client_parser.add_argument("-v", "--vehicle-type", help="车辆类型")
    client_parser.add_argument("-p", "--preferred-coverage", help="偏好险种")
    client_parser.add_argument("-n", "--notes", help="备注")
    
    # quote - 记忆报价
    quote_parser = subparsers.add_parser("quote", help="记忆报价结果")
    quote_parser.add_argument("plate", help="车牌")
    quote_parser.add_argument("-t", "--total", help="总保费")
    quote_parser.add_argument("-T", "--vehicle-type", help="车辆类型")
    quote_parser.add_argument("-c", "--coverage", help="险种详情")
    
    # status - 检查状态
    subparsers.add_parser("status", help="检查 mem0 状态")
    
    # history - 搜索历史
    history_parser = subparsers.add_parser("history", help="搜索客户/车牌历史")
    history_parser.add_argument("type", choices=["client", "plate"], help="类型")
    history_parser.add_argument("name", help="客户名或车牌")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行对应命令
    commands = {
        "add": cmd_add,
        "search": cmd_search,
        "list": cmd_list,
        "client": cmd_client,
        "quote": cmd_quote,
        "status": cmd_status,
        "history": cmd_history
    }
    
    commands[args.command](args)

if __name__ == "__main__":
    main()
