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

---

### [ADR-004] 事务级并发锁、防抖丢尾修复与离线安全加固
- **日期**：2026-09-30
- **提议 Agent**：Antigravity (基于同行深度评审)
- **背景**：评审指出原先锁仅覆盖写操作，导致读-改-写发生典型 Lost Update；删锁文件破坏 filelock 原理；任务 ID 哈希碰撞；前端依赖 CDN 离线白屏。
- **决策内容**：
  1. **锁粒度提升**：将锁扩展至整个事务周期（`storage.transaction`），读-改-写全程独占锁；
  2. **锁文件规范**：严禁 `unlink` 锁文件，保持 `.lock` 文件持久化；
  3. **任务 ID 序列化**：ID 掺入任务行号或序号，杜绝同名任务连坐；
  4. **严格标题解析**：解析器匹配 `^#{1,3}\s+` 标题标记，并支持中英双语；
  5. **前端完全本地化**：去除一切外网 CDN，内嵌本地精简运行脚本，保障 100% 离线秒开；
  6. **防抖丢尾修复**：引入 trailing-edge 定时器；
  7. **本地安全加固**：收紧 CORS 仅允许 localhost，阻断 drive-by 本地越权攻击。
- **影响**：真正实现多 Agent 高并发无损修改，完全离线可用，达到工业级软件安全标准。

---

### [ADR-005] Host Header 校验防御 DNS Rebinding 与工程化交付闭环
- **日期**：2026-09-30
- **提议 Agent**：Antigravity (基于复评深度建议)
- **背景**：复评指出虽然 CORS 收紧，但非受信 Host 头可能导致 DNS Rebinding 攻击；CLI 缺少 `--dir` 选项导致胶水提示词执行报错；依赖列表中存在未使用项；缺少 CI 与代码检查工具。
- **决策内容**：
  1. **DNS Rebinding 严密防御**：集成 Starlette `TrustedHostMiddleware`，严格限制只接受 `localhost`、`127.0.0.1`、`[::1]` 及测试主机头，非受信 Host 直接 400 拦截；
  2. **CLI 参数兼容**：CLI 解析器新增 `--dir` 选项作为工作区路径别名，确保 `context-cockpit .` 与 `context-cockpit --dir .` 均 100% 顺畅执行；
  3. **标题解析严格对齐**：解析器匹配模式更新为 `^#{1,3}\s+`，与 ADR-004 保持绝对一致；
  4. **位置型任务 ID 语义声明**：当前任务 ID 采用结合序号与文本的散列设计 (`task-{hash(index:text)}`)，兼顾无损文本纯净度与同名防连坐；配合 WebSocket 实时刷新与尾部追加策略，杜绝跨会话错位；
  5. **工程化闭环**：剔除冗余依赖 `pydantic-settings`，引入 `ruff` 代码风格检查与格式化，新增 GitHub Actions 跨平台 CI 矩阵工作流。
- **影响**：项目在安全防御、易用性、规范度与自动化测试各个维度均达到工业级成熟交付水准。

