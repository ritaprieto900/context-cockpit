"""Command-line interface (CLI) and server launcher for Context Cockpit."""

import argparse
import asyncio
import json
from pathlib import Path
import socket
import sys
import threading
import time
import webbrowser
import uvicorn

from context_cockpit import __version__
from context_cockpit.app import create_app
from context_cockpit.mcp.server import create_mcp_server
from context_cockpit.services.workspace import WorkspaceService

BANNER = rf"""
   ______            __            __     ______           __            _ __ 
  / ____/___  ____  / /____  _  __/ /_   / ____/___  _____/ /______  (_) /_
 / /   / __ \/ __ \/ __/ _ \| |/_/ __/  / /   / __ \/ ___/ //_/ __ \/ / __/
/ /___/ /_/ / / / / /_/  __/>  </ /_   / /___/ /_/ / /__/ ,< / /_/ / / /_  
\____/\____/_/ /_/\__/\___/_/|_|\__/   \____/\____/\___/_/|_/ .___/_/\__/   
                                                           /_/  v{__version__}
      Multi-Agent Collaboration Cockpit for Git Blackboard Architecture
"""


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks whether a TCP port is currently occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int, host: str = "127.0.0.1") -> int:
    """Finds the first free port starting from start_port."""
    port = start_port
    while is_port_in_use(port, host):
        port += 1
    return port


def ensure_workspace_initialized(workspace: Path) -> None:
    """Initializes .context/ directory if not present using atomic storage."""
    context_dir = workspace / ".context"
    if not context_dir.exists():
        print(f"📦 Initializing .context/ architecture at: {workspace}", file=sys.stderr)
        context_dir.mkdir(parents=True, exist_ok=True)

    from context_cockpit.infrastructure.storage import AtomicStorage
    storage = AtomicStorage(lock_timeout=5.0)

    state_file = context_dir / "state.md"
    if not state_file.exists():
        storage.write_text_atomic(
            state_file,
            """# 项目当前工作看板 (Dynamic State)

## 1. 当前里程碑
- **当前阶段目标**：项目原型与核心功能开发
- **当前负责人 (Active Agent)**：Antigravity

## 2. 任务清单 (Task Checklist)
- [x] 初始化项目骨架与 .context/ 黑板规范
- [ ] 开展第一阶段核心功能开发

## 3. 当前阻塞与风险 (Blockers)
- 无

---

## 4. 上一个 Agent 的交接便签 (Handover Note)
> **交接记录人**：Antigravity
> **交接时间**：初始创建
> **本次产出**：
> - 初始化了项目黑板协作环境
""",
        )

    decisions_file = context_dir / "decisions.md"
    if not decisions_file.exists():
        storage.write_text_atomic(
            decisions_file,
            """# 架构决策记录 (Architecture Decision Records - ADR)

本文件用于记录项目中的重大技术决策与设计理由。所有 Agent 必须遵守已有决策，不得擅自逆转既定架构。

---

### [ADR-001] 初始化黑板架构
- **日期**：初始创建
- **提议 Agent**：Antigravity
- **背景**：需要多 Agent 无缝协作。
- **决策内容**：采用 Git 原生黑板模式，通过 .context/ 共享状态。
- **影响**：所有 Agent 在工作前后均需同步 state.md。
""",
        )

    system_file = context_dir / "system.md"
    if not system_file.exists():
        proj_name = workspace.name
        storage.write_text_atomic(
            system_file,
            f"""# 项目系统设计与全局约定 (System Context)

## 1. 项目基本信息
- **项目名称**：{proj_name}
- **项目目标**：描述业务核心目标
- **核心技术栈**：Python / Node.js

## 2. 环境与运行方式
- **启动命令**：`待配置`
- **测试命令**：`待配置`

## 3. 编码规范与红线约束 (Critical Rules)
- **规则 1**：所有涉及公共接口的变更，必须同步更新相关文档。
""",
        )



def print_mcp_config(workspace_path: Path) -> None:
    """Outputs copy-pastable MCP client JSON configuration."""
    project_root = Path(__file__).parent.parent.parent.resolve()
    config = {
        "mcpServers": {
            "context-cockpit": {
                "command": "uv",
                "args": [
                    "--directory",
                    str(project_root),
                    "run",
                    "python",
                    "-m",
                    "context_cockpit.cli",
                    "--mcp",
                    str(workspace_path),
                ],
            }
        }
    }
    print(json.dumps(config, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Context Cockpit - Industrial Multi-Agent Developer Cockpit & MCP Server",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Workspace directory containing or to host .context/ (default: current directory)",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run as an MCP (Model Context Protocol) stdio server for AI agents",
    )
    parser.add_argument(
        "--print-mcp-config",
        action="store_true",
        help="Print JSON configuration for Cursor / Claude Desktop / Antigravity MCP settings",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Preferred port for the web dashboard (default: 8765)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open browser automatically upon launch",
    )

    args = parser.parse_args()

    workspace_path = Path(args.path).resolve()

    if args.print_mcp_config:
        print_mcp_config(workspace_path)
        return

    # Ensure .context/ directory exists
    ensure_workspace_initialized(workspace_path)

    # MCP Mode
    if args.mcp:
        server = create_mcp_server(workspace_path)
        asyncio.run(server.run_stdio_async())
        return

    # Web Dashboard Mode
    print(BANNER)
    print(f"📁 Workspace: {workspace_path}")

    port = find_available_port(args.port, args.host)
    if port != args.port:
        print(f"⚠️ Port {args.port} was busy. Switched to available port: {port}")

    url = f"http://{args.host}:{port}"
    print(f"🚀 Context Cockpit Web Console is running at: {url}")
    print("💡 Press Ctrl+C to terminate cleanly.\n")

    # Schedule browser opening
    if not args.no_open:
        def _open():
            time.sleep(1.0)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    app = create_app(workspace_path)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
