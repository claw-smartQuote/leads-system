# Brave Search 配额管理

## 每月配额
- **限制**: 800 requests/月
- **当前月份**: {current_month}
- **已使用**: 0 requests
- **剩余**: 800 requests

## 使用方法
配额文件位置：`~/.openclaw/.brave_quota`

### 手动检查配额
```bash
python3 ~/.openclaw/workspace/skills/brave-quota/quota_manager.py status
```

### 记录一次搜索请求
```bash
python3 ~/.openclaw/workspace/skills/brave-quota/quota_manager.py log
```

### 重置月度配额（新月）
```bash
python3 ~/.openclaw/workspace/skills/brave-quota/quota_manager.py reset
```

## 配额告警阈值
| 使用率 | 状态 |
|--------|------|
| < 50%  | 🟢 正常 |
| 50-75% | 🟡 注意 |
| 75-90% | 🟠 警告 |
| > 90%  | 🔴 危险 |

## 使用建议
1. 搜索前先用 `status` 检查配额
2. 接近限制时，优先使用 `web_fetch` 获取已知 URL 内容（不消耗配额）
3. 考虑使用 `web_search` 的 `count` 参数减少结果数量

## 配置说明
本配额管理器通过记录搜索请求来监控使用量。
实际配额限制由 Brave Search API 控制，此处仅作监控提醒用途。
