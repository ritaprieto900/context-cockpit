# Context Cockpit 🚀

> 工业级多 Agent 协同本地驾驶舱 (Industrial-Grade Multi-Agent Local Cockpit)

Context Cockpit 专为基于 **Git 原生黑板架构 (`.context/`)** 的多 Agent 协同开发而设计。它消除了不同 AI 编码助手（如 Antigravity、豆包、Cursor、Claude、ChatGPT）之间的记忆孤岛与上下文割裂，提供无损 Markdown 同步、原子并发写入、实时状态监控与智能胶水提示词生成。

## 核心特性
- **无损分块解析 (Structure-Preserving Parser)**：精确变异任务状态，100% 字节级保留用户注释与缩进。
- **并发与存储安全 (Atomic & Concurrency Safe)**：基于文件锁与操作系统级原子替换 (`os.replace`)，杜绝多进程/编辑器写冲突。
- **响应式文件监听 (Debounced File Watcher)**：基于 Watchdog + 防抖，毫秒级响应外部编辑并通过 WebSocket 实时推流。
- **多 Agent 策略适配 (Prompt Strategy Engine)**：一键拼装针对豆包、Cursor、Claude Code 的最佳投喂提示词。
- **开箱即用**：零额外数据库依赖，单命令行快速拉起。
