"""Tests for MCP server tools and resources."""

import json
from pathlib import Path
import pytest

from context_cockpit.infrastructure.storage import AtomicStorage
from context_cockpit.mcp.server import create_mcp_server
from tests.conftest import SAMPLE_DECISIONS_MD, SAMPLE_STATE_MD, SAMPLE_SYSTEM_MD


@pytest.fixture
def mcp_workspace(tmp_path: Path) -> Path:
    context_dir = tmp_path / ".context"
    context_dir.mkdir(parents=True)
    storage = AtomicStorage()
    storage.write_text_atomic(context_dir / "state.md", SAMPLE_STATE_MD)
    storage.write_text_atomic(context_dir / "decisions.md", SAMPLE_DECISIONS_MD)
    storage.write_text_atomic(context_dir / "system.md", SAMPLE_SYSTEM_MD)
    return tmp_path


@pytest.mark.asyncio
async def test_mcp_server_lists_all_tools(mcp_workspace: Path):
    server = create_mcp_server(mcp_workspace)
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]

    expected = [
        "cockpit_get_overview",
        "cockpit_get_ready_tasks",
        "cockpit_toggle_task",
        "cockpit_add_task",
        "cockpit_create_adr",
        "cockpit_land_the_plane",
        "cockpit_synthesize_prompt",
    ]
    for exp in expected:
        assert exp in tool_names


@pytest.mark.asyncio
async def test_mcp_get_ready_tasks(mcp_workspace: Path):
    server = create_mcp_server(mcp_workspace)
    res = await server.call_tool("cockpit_get_ready_tasks", {})
    text_content = res.content[0].text
    data = json.loads(text_content)

    assert data["active_milestone"] == "完成核心架构与测试"
    assert data["ready_tasks_count"] == 2
    assert data["tasks"][0]["text"] == "实现 Domain 模型"


@pytest.mark.asyncio
async def test_mcp_land_the_plane(mcp_workspace: Path):
    server = create_mcp_server(mcp_workspace)
    res = await server.call_tool(
        "cockpit_land_the_plane",
        {
            "author": "Cursor",
            "handover_note": "完成了 MCP 适配，已通过全部测试。",
        },
    )
    text_content = res.content[0].text
    data = json.loads(text_content)
    assert data["success"] is True

    # Verify state.md updated on disk
    state_text = (mcp_workspace / ".context" / "state.md").read_text(encoding="utf-8")
    assert "完成了 MCP 适配，已通过全部测试。" in state_text
