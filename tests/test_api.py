"""Integration tests for FastAPI REST endpoints using httpx AsyncClient."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from context_cockpit.app import create_app
from context_cockpit.infrastructure.storage import AtomicStorage
from tests.conftest import SAMPLE_DECISIONS_MD, SAMPLE_STATE_MD, SAMPLE_SYSTEM_MD


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    context_dir = tmp_path / ".context"
    context_dir.mkdir(parents=True)
    storage = AtomicStorage()
    storage.write_text_atomic(context_dir / "state.md", SAMPLE_STATE_MD)
    storage.write_text_atomic(context_dir / "decisions.md", SAMPLE_DECISIONS_MD)
    storage.write_text_atomic(context_dir / "system.md", SAMPLE_SYSTEM_MD)
    return tmp_path


@pytest.mark.asyncio
async def test_get_overview_endpoint(mock_workspace: Path):
    app = create_app(mock_workspace)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        resp = await client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["milestone"]["title"] == "完成核心架构与测试"
        assert len(data["state"]["tasks"]) == 3
        assert len(data["decisions"]["records"]) == 1
        assert data["system"]["project_name"] == "Context Cockpit"


@pytest.mark.asyncio
async def test_toggle_task_endpoint(mock_workspace: Path):
    app = create_app(mock_workspace)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        # Get tasks
        resp = await client.get("/api/state")
        task_id = resp.json()["tasks"][1]["id"]

        # Toggle to completed
        patch_resp = await client.post(
            "/api/tasks/toggle",
            json={"task_id": task_id, "completed": True},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["tasks"][1]["completed"] is True


@pytest.mark.asyncio
async def test_add_task_endpoint(mock_workspace: Path):
    app = create_app(mock_workspace)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        resp = await client.post(
            "/api/tasks",
            json={"text": "测试新增任务接口"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 4
        assert data["tasks"][-1]["text"] == "测试新增任务接口"


@pytest.mark.asyncio
async def test_generate_prompt_endpoint(mock_workspace: Path):
    app = create_app(mock_workspace)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        resp = await client.post(
            "/api/prompt",
            json={"agent_type": "doubao", "instruction": "优先优化任务列表"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "豆包" in data["prompt"]
        assert "优先优化任务列表" in data["prompt"]


@pytest.mark.asyncio
async def test_dns_rebinding_rejected_by_host_validation(mock_workspace: Path):
    app = create_app(mock_workspace)
    # Untrusted external host header simulates a DNS rebinding attempt
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://127.0.0.1",
        headers={"Host": "evil.example.com"},
    ) as client:
        resp = await client.get("/api/overview")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ipv6_loopback_host_accepted(mock_workspace: Path):
    app = create_app(mock_workspace)
    # Valid IPv6 loopback [::1] must be accepted cleanly
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://127.0.0.1",
        headers={"Host": "[::1]"},
    ) as client:
        resp = await client.get("/api/overview")
        assert resp.status_code == 200


