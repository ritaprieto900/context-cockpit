"""Stress tests for concurrency safety verifying absence of Lost Updates."""

import asyncio
from pathlib import Path

import pytest

from context_cockpit.infrastructure.parser import MarkdownContextParser
from context_cockpit.infrastructure.storage import AtomicStorage
from context_cockpit.services.context_service import ContextService
from context_cockpit.services.event_bus import EventBus
from context_cockpit.services.workspace import WorkspaceService

MULTI_TASK_STATE_MD = """# 项目当前工作看板 (Dynamic State)

## 1. 当前里程碑
- **当前阶段目标**：并发测试专用看板
- **当前负责人**：TestAgent

## 2. 任务清单 (Task Checklist)
- [ ] 并发任务 1
- [ ] 并发任务 2
- [ ] 并发任务 3
- [ ] 并发任务 4
- [ ] 并发任务 5
- [ ] 并发任务 6
- [ ] 并发任务 7
- [ ] 并发任务 8

## 3. 当前阻塞与风险 (Blockers)
- 无

---

## 4. 上一个 Agent 的交接便签 (Handover Note)
> **交接记录人**：TestAgent
> **交接时间**：2026-09-30 22:40
> **本次产出**：初始化并发测试
"""


@pytest.mark.asyncio
async def test_concurrent_task_toggles_no_lost_updates(tmp_path: Path):
    """Verifies that multiple agents toggling different tasks concurrently do NOT lose any updates."""
    # Arrange
    context_dir = tmp_path / ".context"
    context_dir.mkdir(parents=True)
    state_file = context_dir / "state.md"
    state_file.write_text(MULTI_TASK_STATE_MD, encoding="utf-8")

    workspace = WorkspaceService(tmp_path)
    storage = AtomicStorage(lock_timeout=15.0)
    parser = MarkdownContextParser()
    service = ContextService(workspace, storage, parser, EventBus())

    # Get initial task IDs
    state = service.get_state()
    assert len(state.tasks) == 8
    task_ids = [t.id for t in state.tasks]

    # Act: Run 8 concurrent toggles across multiple async tasks
    async def toggle_worker(tid: str):
        await service.toggle_task(task_id=tid, completed=True)

    await asyncio.gather(*[toggle_worker(tid) for tid in task_ids])

    # Assert: All 8 tasks MUST be completed, zero Lost Updates!
    final_state = service.get_state()
    completed_count = sum(1 for t in final_state.tasks if t.completed)
    assert completed_count == 8, f"Expected 8 completed tasks, got {completed_count}. Lost update occurred!"
