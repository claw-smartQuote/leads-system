# Long Term Memory Skill

## Description

本地長期記憶系統，解決 OpenClaw 第二天「失憶」問題。

## Features

- 自動保存重要對話內容到 MEMORY.md
- 會話開始時自動加載記憶
- 支持記憶搜索和檢索
- 無需雲端服務，完全本地運行

## Installation

```bash
# 已內置於工作區，無需額外安裝
```

## Usage

### 自動記憶

系統會自動：
1. 在對話結束時提取關鍵信息
2. 更新 MEMORY.md
3. 下次啟動時自動讀取

### 手動記憶

```
記住：[重要信息]
```

### 搜索記憶

```
搜索記憶：[關鍵詞]
```

## Configuration

記憶文件位置：`~/.openclaw/workspace/MEMORY.md`

## Notes

- 與現有 MEMORY.md 系統兼容
- 支持 Markdown 格式
- 可手動編輯記憶文件
