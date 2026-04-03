# CONTEXT.md - 上下文管理配置

## 會話長度限制

```yaml
max_messages: 20          # 最多保留消息數
max_tokens_estimate: 8000 # 估計最大 token 數
auto_compact_threshold: 0.8  # 自動壓縮閾值 (80%)
```

## 壓縮策略

### 輕度壓縮 (messages > 15)
- 移除系統工具調用詳情
- 壓縮中間推理步驟

### 中度壓縮 (messages > 25)
- 總結對話主題
- 保留關鍵決策和事實

### 重度壓縮 (messages > 40)
- 僅保留最終結論
- 將詳細信息寫入 memory 文件

## 回复風格

```yaml
style: concise          # concise | detailed | verbose
format: structured      # structured | narrative | bullet
tone: direct            # direct | warm | formal
```

## 工具調用優化

```yaml
batch_similar: true     # 批量執行相似工具
parallel_safe: true     # 安全時並行調用
minimize_confirmations: true  # 最小化確認提問
```

## 監控與警報

當以下情況發生時主動處理：
- 會話長度 > max_messages
- 預計 token 數 > max_tokens_estimate
- 回复延遲 > 5 秒

## 自動行動

```yaml
on_context_high:
  - suggest_compact: true
  - offer_new_session: true
  
on_context_overflow:
  - auto_compact: false  # 不自動，讓用戶決定
  - alert_user: true
```