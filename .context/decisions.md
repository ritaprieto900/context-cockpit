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
