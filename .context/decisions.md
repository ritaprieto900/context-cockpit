# 架构决策记录 (Architecture Decision Records - ADR)

本文件用于记录 Context Cockpit 项目中的重大技术决策与设计理由。所有 Agent 必须遵守已有决策，不得擅自逆转既定架构。

---

### [ADR-001] 项目初始化与分层整洁架构确立
- **日期**：2026-09-30
- **提议 Agent**：Antigravity
- **背景**：项目定位为真正有用、成熟完善的本地工业级开发工具，拒绝拼凑玩具代码。
- **决策内容**：
  1. 采用整洁架构（Clean Architecture）：
     - `domain`: 纯领域模型与强类型异常；
     - `infrastructure`: 结构无损解析引擎（AST/Section Tokenizer）、原子写入器、文件监听器、多 Agent 提示词策略适配器；
     - `services`: 领域业务编排与事件总线（Event Bus）；
     - `api`: FastAPI 路由控制器与全双工 WebSocket 同步接口；
     - `ui`: 现代化内嵌式高保真控制台；
     - `cli`: 命令行自启动器。
  2. 采用 `uv` 作为依赖管理与虚拟环境工具，保证极速且确定的依赖构建。
- **影响**：所有后续功能开发必须遵守分层边界，业务逻辑不得穿透到路由控制器。

---

### [ADR-002] 采用无损分块解析 (Block-Aware AST) 与原子替换写入
- **日期**：2026-09-30
- **提议 Agent**：Antigravity
- **背景**：传统正则全文替换极易破坏用户的注释、格式和缩进；直接写入文件在断电或多工具并发时会导致文件截断损坏。
- **决策内容**：
  1. 构建块级别（Block-level）的解析器，只对目标行做状态切换（In-place mutation），保持未变更块原始字节不变；
  2. 所有写操作采用 `filelock` 互斥保护，并写入 `path.with_suffix('.tmp.PID.UUID')`，通过 `os.replace` 原子替换原文件。
- **影响**：彻底杜绝文件损坏风险，保证与外部编辑器（VS Code, Cursor 等）的并发共存安全。

---

### [ADR-003] 引入 Model Context Protocol (MCP) 统一 Agent 交互接口
- **日期**：2026-09-30
- **提议 Agent**：Antigravity
- **背景**：为使 AI Agent（Cursor、Claude Desktop、Windsurf、Antigravity）能够程序化、强类型地读取与修改黑板，避免大模型直接拼写 Markdown 产生幻觉与格式漂移。
- **决策内容**：
  1. 引入官方 `mcp` 2.x SDK，构建高内聚的 `MCPServer`；
  2. 暴露 7 个核心工具函数：`cockpit_get_overview`、`cockpit_get_ready_tasks`、`cockpit_toggle_task`、`cockpit_add_task`、`cockpit_create_adr`、`cockpit_land_the_plane`、`cockpit_synthesize_prompt`；
  3. 暴露 3 个黑板实时只读资源：`cockpit://state`、`cockpit://decisions`、`cockpit://system`；
  4. CLI 增加 `--mcp`（运行 stdio 模式）与 `--print-mcp-config`（一键输出客户端配置）。
- **影响**：AI Agent 可直接通过函数调用精准操控黑板，变更瞬间通过 WebSocket 同步到人类的 Web 驾驶舱大屏。
