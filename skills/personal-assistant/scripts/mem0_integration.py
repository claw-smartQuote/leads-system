"""
Mem0 Integration for Personal Assistant
=========================================
Mem0 记忆层整合 - 增强个人助理的记忆能力

功能:
- 存储重要对话摘要
- 记忆客户偏好和历史
- 自然语言搜索记忆
- 与现有 reminder 系统协同工作
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# Mem0 imports (需要安装: pip install mem0ai)
try:
    from mem0 import Memory
    from mem0.configs.base import MemoryConfig
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None

# ============================================================
# 配置
# ============================================================

MEMORY_STORE_PATH = os.path.expanduser("~/.openclaw/workspace/memory/personal_memories.json")

# 默认用户 ID (用于 mem0)
DEFAULT_USER_ID = "smartQuote_personal_assistant"

# ============================================================
# 记忆客户端初始化
# ============================================================

def get_memory_client() -> Optional['Memory']:
    """初始化并返回 mem0 记忆客户端"""
    if not MEM0_AVAILABLE:
        print("⚠️ mem0ai 未安装. 运行: pip install mem0ai")
        return None
    
    # 检查 API key
    api_key = os.environ.get("MEM0_API_KEY")
    if not api_key:
        print("⚠️ MEM0_API_KEY 未设置")
        return None
    
    try:
        config = MemoryConfig()
        client = Memory(config)
        return client
    except Exception as e:
        print(f"❌ Mem0 初始化失败: {e}")
        return None

# ============================================================
# 核心功能
# ============================================================

def add_memory(content: str, user_id: str = DEFAULT_USER_ID, metadata: Optional[Dict] = None) -> bool:
    """
    添加一条记忆
    
    Args:
        content: 记忆内容
        user_id: 用户标识
        metadata: 额外元数据 (category, source, etc.)
    
    Returns:
        bool: 是否成功
    """
    if not MEM0_AVAILABLE:
        save_to_local_storage(content, metadata)
        return False
    
    try:
        client = get_memory_client()
        if client is None:
            save_to_local_storage(content, metadata)
            return False
        
        # 格式化消息
        messages = [{"role": "user", "content": content}]
        
        # 添加记忆
        result = client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        print(f"✅ 记忆已添加: {content[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ 添加记忆失败: {e}")
        save_to_local_storage(content, metadata)
        return False


def search_memories(query: str, user_id: str = DEFAULT_USER_ID, limit: int = 5) -> List[Dict[str, Any]]:
    """
    搜索相关记忆
    
    Args:
        query: 搜索查询
        user_id: 用户标识
        limit: 返回数量限制
    
    Returns:
        List[Dict]: 匹配的记忆列表
    """
    # 先尝试 mem0
    if MEM0_AVAILABLE:
        try:
            client = get_memory_client()
            if client:
                results = client.search(query=query, user_id=user_id, limit=limit)
                return results.get("results", [])
        except Exception as e:
            print(f"⚠️ Mem0 搜索失败，回退到本地存储: {e}")
    
    # 回退到本地存储搜索
    return search_local_storage(query)


def get_all_memories(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    """获取用户的所有记忆"""
    if MEM0_AVAILABLE:
        try:
            client = get_memory_client()
            if client:
                # Mem0 没有直接的 get_all，需要用空查询
                return client.search(query="", user_id=user_id, limit=100).get("results", [])
        except Exception as e:
            print(f"⚠️ Mem0 获取失败: {e}")
    
    return get_local_memories()


def delete_memory(memory_id: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """删除指定记忆"""
    if not MEM0_AVAILABLE:
        return False
    
    try:
        client = get_memory_client()
        if client:
            client.delete(memory_id=memory_id, user_id=user_id)
            return True
    except Exception as e:
        print(f"❌ 删除记忆失败: {e}")
    
    return False


def clear_all_memories(user_id: str = DEFAULT_USER_ID) -> bool:
    """清除用户所有记忆（谨慎使用）"""
    if not MEM0_AVAILABLE:
        return False
    
    try:
        client = get_memory_client()
        if client:
            # 获取所有记忆然后删除
            memories = get_all_memories(user_id)
            for mem in memories:
                client.delete(memory_id=mem.get("id"), user_id=user_id)
            return True
    except Exception as e:
        print(f"❌ 清除记忆失败: {e}")
    
    return False

# ============================================================
# 本地存储回退 (当 mem0 不可用时)
# ============================================================

def save_to_local_storage(content: str, metadata: Optional[Dict] = None):
    """保存到本地 JSON 存储"""
    os.makedirs(os.path.dirname(MEMORY_STORE_PATH), exist_ok=True)
    
    memories = []
    if os.path.exists(MEMORY_STORE_PATH):
        try:
            with open(MEMORY_STORE_PATH, 'r', encoding='utf-8') as f:
                memories = json.load(f)
        except:
            memories = []
    
    new_memory = {
        "id": f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "memory": content,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat()
    }
    
    memories.append(new_memory)
    
    with open(MEMORY_STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def search_local_storage(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """在本地存储中搜索"""
    if not os.path.exists(MEMORY_STORE_PATH):
        return []
    
    try:
        with open(MEMORY_STORE_PATH, 'r', encoding='utf-8') as f:
            memories = json.load(f)
        
        # 简单关键词匹配 (生产环境应该用 embedding)
        query_lower = query.lower()
        scored = []
        
        for mem in memories:
            # 简单的相关性评分
            content = mem.get("memory", "").lower()
            score = sum(1 for word in query_lower.split() if word in content)
            if score > 0:
                scored.append((score, mem))
        
        # 按分数排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:limit]]
        
    except Exception as e:
        print(f"❌ 本地搜索失败: {e}")
        return []


def get_local_memories() -> List[Dict[str, Any]]:
    """获取所有本地记忆"""
    if not os.path.exists(MEMORY_STORE_PATH):
        return []
    
    try:
        with open(MEMORY_STORE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

# ============================================================
# 便捷函数
# ============================================================

def remember_client(client_name: str, preferences: Dict[str, Any], notes: str = ""):
    """记忆客户信息"""
    content = f"客户 {client_name}: {json.dumps(preferences, ensure_ascii=False)}"
    if notes:
        content += f"。备注: {notes}"
    add_memory(content, metadata={"category": "client", "client_name": client_name})


def remember_quote_result(license_plate: str, quote_data: Dict[str, Any]):
    """记忆报价结果"""
    content = f"车牌 {license_plate} 报价: {json.dumps(quote_data, ensure_ascii=False)}"
    add_memory(content, metadata={"category": "quote", "license_plate": license_plate})


def remember_preference(preference_type: str, details: str):
    """记忆用户偏好"""
    content = f"用户偏好 [{preference_type}]: {details}"
    add_memory(content, metadata={"category": "preference", "type": preference_type})


def search_client_history(client_name: str) -> List[Dict[str, Any]]:
    """搜索客户历史"""
    return search_memories(f"客户 {client_name}", limit=10)


def search_quote_history(license_plate: str) -> List[Dict[str, Any]]:
    """搜索车牌报价历史"""
    return search_memories(f"车牌 {license_plate} 报价", limit=10)


# ============================================================
# 状态检查
# ============================================================

def check_status() -> Dict[str, Any]:
    """检查 mem0 集成状态"""
    status = {
        "mem0_installed": MEM0_AVAILABLE,
        "api_key_set": bool(os.environ.get("MEM0_API_KEY")),
        "local_storage_exists": os.path.exists(MEMORY_STORE_PATH),
        "local_storage_count": 0
    }
    
    if status["local_storage_exists"]:
        local_memories = get_local_memories()
        status["local_storage_count"] = len(local_memories)
    
    return status


# ============================================================
# 主函数 - 测试
# ============================================================

if __name__ == "__main__":
    print("🔍 Mem0 集成状态检查:")
    status = check_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n📝 测试添加记忆...")
    add_memory("测试记忆：香港保險代理人，主要銷售汽車保險", metadata={"test": True})
    
    print("\n🔍 测试搜索...")
    results = search_memories("香港保險")
    print(f"  找到 {len(results)} 条相关记忆")
    
    if results:
        for r in results:
            print(f"  - {r.get('memory', '')[:60]}...")
