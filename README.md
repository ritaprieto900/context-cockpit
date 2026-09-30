# Context Cockpit 🚀

> **Industrial-Grade Local Developer Cockpit & MCP Server for Multi-Agent Git Blackboard Architecture**  
> 专为基于 **Git 原生黑板架构 (`.context/` + `AGENTS.md`)** 的多 AI Agent 协同开发打造的工业级本地驾驶舱与标准 MCP 服务器。

[![CI](https://github.com/ritaprieto900/context-cockpit/actions/workflows/ci.yml/badge.svg)](https://github.com/ritaprieto900/context-cockpit/actions)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-2.2.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 📖 为什么需要 Context Cockpit？

当前 AI 编程助手（如 Antigravity、Claude Code、Cursor、Windsurf、豆包等）面临著名的 **“初恋 50 次”（50 First Dates / AI Amnesia）** 痛点：
1. **记忆割裂与失忆**：每次会话结束或上下文滑动时，Agent 忘光上一个 Agent 制定的架构决策与未完成半成品；
2. **Markdown 梦魇**：手写 Markdown 容易被大模型胡乱改写，破坏缩进、删掉注释、产生格式漂移；
3. **并发写入丢失（Lost Update）**：多 Agent 或人类在外部编辑器同时修改任务状态时，发生无声覆盖。

**Context Cockpit** 将 Git 原生黑板架构工程化为一套成熟软件体系：
- **纯文件、零数据库**：所有数据直接持久化为仓库根目录下的 `.context/*.md` 与 `AGENTS.md`，与业务代码同分支、同提交、同回滚。
- **ACID 级别并发安全**：全程文件锁覆盖“读-改-写”完整事务周期，结合操作系统原子替换 (`os.replace`)，杜绝并发竞争。
- **双模并存**：既是人类可视化的 **本地实时 Web 驾驶舱**，又是面向大模型的 **标准 Model Context Protocol (MCP) 服务器**。
- **100% 离线脱网可用**：前端零外部 CDN 依赖，内嵌精简资源，毫秒级冷启动，抵御 DNS Rebinding 安全攻击。

---

## 🏗️ 架构全景

```
                  ┌─────────────────────────────────────────┐
                  │          Human Developer (UI)           │
                  └────────────────────┬────────────────────┘
                                       │ HTTP / WebSocket (:8765)
┌───────────────────────┐              ▼              ┌───────────────────────┐
│ External Agents       │     ┌─────────────────┐     │ MCP-enabled Agents    │
│ (Doubao, Web LLMs)    │◄────┤ Context Cockpit ├────►│ (Antigravity, Cursor, │
│ via Synthesized Prompt│     │  Engine (FastAPI│     │  Claude Desktop, etc.)│
└───────────────────────┘     │   + MCP Stdio)  │     │ via MCP Tools/Prompts │
                              └────────┬────────┘     └───────────────────────┘
                                       │
                      Transaction-Level File Locks (.lock)
                        Atomic Swap (.tmp -> os.replace)
                                       │
                                       ▼
                     ┌──────────────────────────────────┐
                     │     Git Blackboard Storage       │
                     │  .context/state.md (Checklist)   │
                     │  .context/decisions.md (ADRs)    │
                     │  .context/system.md (Rules/Tech) │
                     │  AGENTS.md (Coordination SOP)    │
                     └──────────────────────────────────┘
```

---

## ✨ 核心特性

### 1. 事务级文件锁与原子替换 (Transaction Locks)
- 采用 `AtomicStorage.transaction()` 上下文管理器，将“读取旧文件 ➔ 内存变异 ➔ 原子落盘”完整包裹在操作系统级互斥锁内。
- 采用持久化 `.lock` 句柄策略，解决排队进程句柄失效反模式。
- 经 8 协程并发压测验证，保证 **0 丢失更新 (Zero Lost Updates)**。

### 2. 结构无损分块解析器 (Lossless AST Parser)
- 仅重写目标任务的 `[ ]` / `[x]` 标记，100% 字节级保留原有空行、Tab/空格缩进、HTML 注释与扩展文本。
- 任务 ID 采用结合行位与内容的确定性散列算法 (`compute_task_id(text, index)`)，杜绝同名任务连坐打钩。
- 标题严格匹配 `^#{1,3}\s+`，天然支持中英双语标记（`Milestone / Tasks / Blockers / Handover`）。

### 3. 原生 Model Context Protocol (MCP 2.x)
内置 7 大核心协同工具、2 大协同 Prompt 与 3 大实时资源：
- **`cockpit_get_overview`**：获取当前工作区黑板全貌（当前里程碑、任务列表、ADR 决策、Git 状态）；
- **`cockpit_get_ready_tasks`**：检索未阻塞、等待认领的 Ready 状态任务列表；
- **`cockpit_toggle_task`**：原子翻转任务完成状态；
- **`cockpit_add_task`**：结构无损追加新任务项；
- **`cockpit_create_adr`**：结构化创建 ADR 架构决策记录；
- **`cockpit_land_the_plane`**：**飞机安全着陆协议**——完成阶段工作、更新交接便签（Handover Note）、为下一位 Agent 铺平道路；
- **`cockpit_synthesize_prompt`**：跨 Agent 胶水提示词合成引擎（豆包、Cursor、Claude Code、通用 LLM）；
- **MCP Resources**：`cockpit://state`、`cockpit://decisions`、`cockpit://system`。

### 4. 100% 离线脱网 Web 驾驶舱
- 纯本地内嵌资源（Vue 3 + Marked 本地化），无任何外网 CDN，内网/离线/机房环境 100% 正常运行。
- WebSocket 全双工实时同步：任何 Agent 或人类修改 `.context/` 文件，浏览器毫秒级静默刷新。
- **安全加固**：CORS 严格限制 `localhost` / `127.0.0.1`，集成 `TrustedHostMiddleware` 彻底封堵 DNS Rebinding 攻击。

---

## 🚀 快速上手

### 环境要求
- Python 3.11 或更高版本
- 推荐使用 [uv](https://github.com/astral-sh/uv)（极速包管理器）

### 1. 启动 Web 驾驶舱
在你的项目根目录下执行：
```bash
# 使用 uv 一键启动
uv run context-cockpit

# 或指定项目目录
uv run context-cockpit --dir /path/to/your/project

# 自定义端口并禁止自动打开浏览器
uv run context-cockpit --port 9000 --no-open
```
如果当前目录尚未初始化 `.context/`，Context Cockpit 会自动为你安全生成标准的黑板模板。

### 2. 导出并配置 MCP 服务器
Context Cockpit 支持作为标准 stdio MCP 服务器接入各类智能体客户端：
```bash
# 查看当前工作区的 MCP 配置片段
uv run context-cockpit --print-mcp-config
```

#### 配置示例：Antigravity / Gemini CLI
在 `~/.gemini/config/mcp_config.json` 中配置：
```json
{
  "mcpServers": {
    "context-cockpit": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\context-cockpit",
        "run",
        "python",
        "-m",
        "context_cockpit.cli",
        "--mcp",
        "C:\\path\\to\\your\\workspace"
      ]
    }
  }
}
```

#### 配置示例：Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "context-cockpit": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/context-cockpit",
        "run",
        "context-cockpit",
        "--mcp",
        "/path/to/your/workspace"
      ]
    }
  }
}
```

#### 配置示例：Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "context-cockpit": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/context-cockpit",
        "run",
        "context-cockpit",
        "--mcp",
        "/path/to/your/workspace"
      ]
    }
  }
}
```

---

## 🛠️ CLI 命令行参数

```text
usage: context-cockpit [-h] [--dir DIR_OPT] [--mcp] [--print-mcp-config]
                       [--port PORT] [--host HOST] [--no-open]
                       [path]

Context Cockpit - Industrial Multi-Agent Developer Cockpit & MCP Server

positional arguments:
  path                  Workspace directory (default: current directory)

options:
  -h, --help            Show help message and exit
  --dir DIR_OPT         Explicit workspace directory path
  --mcp                 Run as stdio MCP server for AI agents
  --print-mcp-config    Print JSON config snippet for Cursor/Claude/Antigravity
  --port PORT           Port for web dashboard (default: 8765)
  --host HOST           Host to bind server (default: 127.0.0.1)
  --no-open             Do not open browser automatically upon launch
```

---

## 🧪 测试与质量保证

Context Cockpit 遵循极高标准的工程纪律与防御性编程规范：
- **测试框架**：`pytest` + `pytest-asyncio` + `httpx ASGITransport`
- **代码规范**：`ruff` 全面代码风格与导入自动检查
- **持续集成**：GitHub Actions 多平台矩阵测试（Ubuntu, Windows / Python 3.11, 3.12, 3.13）

运行回归测试套件：
```bash
# 运行全部 20 项单元测试与并发压力测试
uv run pytest

# 运行代码规范检查
uv run ruff check src tests
```

---

## 📑 架构决策记录 (ADR)

本项目的所有重大架构演进均经过完整论证并以 ADR 形式保存在 [`.context/decisions.md`](.context/decisions.md)：
- **[ADR-001]** 项目初始化与分层整洁架构确立 (Domain / Infrastructure / Services / API)
- **[ADR-002]** 结构无损分块解析 (Block-Aware AST) 与原子替换写入
- **[ADR-003]** 引入 Model Context Protocol (MCP) 统一 Agent 交互接口
- **[ADR-004]** 事务级并发锁、防抖丢尾修复与离线安全加固
- **[ADR-005]** Host Header 校验防御 DNS Rebinding 与多重 CLI 参数兼容

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。
