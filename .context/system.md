# 项目系统设计与全局约定 (System Context)

## 1. 项目基本信息
- **项目名称**：Context Cockpit
- **项目目标**：打造一个工业级、零污染、具有完备并发保护与无损解析的多 Agent 协同本地驾驶舱，服务于 Git 原生黑板架构。
- **核心技术栈**：
  - 后端：Python 3.11+ / FastAPI / Uvicorn / Pydantic v2 / Watchdog / FileLock / MCP 2.x SDK
  - 前端：现代极简响应式 Web 控制台 (100% 离线脱网架构 / Vue 3 + Marked 本地内嵌 / 纯暗黑 CSS / WebSocket 实时通道)
  - 依赖管理与质量：`uv` / `hatchling` / `ruff` / `pytest`

## 2. 环境与运行方式
- **开发与同步**：`uv sync`
- **运行控制台**：`uv run context-cockpit` 或 `uv run python -m context_cockpit.cli --dir .`
- **运行 MCP 服务**：`uv run context-cockpit --mcp`
- **测试与校验**：`uv run pytest` 与 `uv run ruff check src tests`

## 3. 编码规范与红线约束 (Critical Rules)
- **规则 1：无损持久化（Structure-Preserving）**：对 `.context/` 文件的修改必须保证除被更新的目标（如复选框状态、新任务）外，原始文件的空行、注释、标题与缩进 100% 字节级保留。
- **规则 2：原子写入与并发安全**：所有向磁盘写入文件的操作必须使用临时文件 + `os.replace` 原子替换，且受文件锁保护，严禁直接 `open(..., 'w')` 覆盖。
- **规则 3：分层架构与单一职责**：严格遵循 Clean Architecture（Domain -> Infrastructure -> Services -> API/UI），禁止在路由层直接编写文件读写逻辑。
- **规则 4：不可变性优先**：领域模型采用不可变 Pydantic 模型，数据流动单向清晰。
