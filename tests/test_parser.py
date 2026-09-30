"""Unit tests for MarkdownContextParser verifying structure preservation and accurate extraction."""

import pytest

from context_cockpit.domain.exceptions import TaskNotFoundError
from context_cockpit.infrastructure.parser import MarkdownContextParser

SAMPLE_STATE_MD = """# 项目当前工作看板 (Dynamic State)

## 1. 当前里程碑
- **当前阶段目标**：完成核心架构与测试
- **当前负责人 (Active Agent)**：Antigravity

## 2. 任务清单 (Task Checklist)
- [x] 初始化项目黑板架构
- [ ] 实现 Domain 模型
- [ ] 实现无损解析器

## 3. 当前阻塞与风险 (Blockers)
- 依赖网络环境不稳定

---

## 4. 上一个 Agent 的交接便签 (Handover Note)
> **交接记录人**：Antigravity
> **交接时间**：2026-09-30 22:00
> **本次产出**：
> - 初始原型完成
"""

SAMPLE_DECISIONS_MD = """# 架构决策记录 (ADR)

### [ADR-001] 采用轻量黑板模式
- **日期**：2026-09-30
- **提议 Agent**：Antigravity
- **背景**：解决多 Agent 记忆割裂
- **决策内容**：使用 .context/ 目录存储状态
- **影响**：所有 Agent 开工前必须读取
"""

SAMPLE_SYSTEM_MD = """# 项目系统设计与全局约定 (System Context)

## 1. 项目基本信息
- **项目名称**：Context Cockpit
- **项目目标**：多 Agent 协同本地驾驶舱
- **核心技术栈**：Python / FastAPI / Vue 3

## 2. 环境与运行方式
- **启动命令**：`uv run python -m context_cockpit.cli`
- **测试命令**：`uv run pytest`

## 3. 编码规范与红线约束 (Critical Rules)
- **规则 1**：所有写入操作必须是原子的。
- **规则 2**：领域模型必须不可变。
"""


def test_parse_state_extracts_all_fields():
    # Arrange
    parser = MarkdownContextParser()

    # Act
    state = parser.parse_state(SAMPLE_STATE_MD, content_hash="hash123")

    # Assert
    assert state.milestone.title == "完成核心架构与测试"
    assert state.milestone.active_agent == "Antigravity"
    assert len(state.tasks) == 3
    assert state.tasks[0].completed is True
    assert state.tasks[0].text == "初始化项目黑板架构"
    assert state.tasks[1].completed is False
    assert state.tasks[1].text == "实现 Domain 模型"
    assert state.blockers == ("依赖网络环境不稳定",)
    assert state.handover_note is not None
    assert state.handover_note.author == "Antigravity"
    assert "2026-09-30 22:00" in state.handover_note.timestamp


def test_toggle_task_preserves_structure_and_switches_state():
    # Arrange
    parser = MarkdownContextParser()
    state_init = parser.parse_state(SAMPLE_STATE_MD)
    task_id = state_init.tasks[1].id

    # Act: toggle from [ ] to [x]
    updated_md = parser.toggle_task(SAMPLE_STATE_MD, task_id, completed=True)
    state = parser.parse_state(updated_md)

    # Assert
    assert "- [x] 实现 Domain 模型" in updated_md
    assert state.tasks[1].completed is True
    # Ensure other parts remain unchanged
    assert "## 1. 当前里程碑" in updated_md
    assert "> **交接记录人**：Antigravity" in updated_md


def test_identical_task_names_do_not_collide():
    parser = MarkdownContextParser()
    sample = """## 2. 任务清单
- [ ] 编写测试
- [ ] 编写测试
"""
    state = parser.parse_state(sample)
    assert len(state.tasks) == 2
    # Ensure distinct IDs
    assert state.tasks[0].id != state.tasks[1].id

    # Toggle only the first one
    toggled = parser.toggle_task(sample, state.tasks[0].id, completed=True)
    state_after = parser.parse_state(toggled)
    assert state_after.tasks[0].completed is True
    assert state_after.tasks[1].completed is False


def test_toggle_task_raises_on_invalid_id():
    # Arrange
    parser = MarkdownContextParser()

    # Act & Assert
    with pytest.raises(TaskNotFoundError):
        parser.toggle_task(SAMPLE_STATE_MD, "nonexistent-task-id", completed=True)


def test_add_task_inserts_at_checklist_end():
    # Arrange
    parser = MarkdownContextParser()

    # Act
    updated_md = parser.add_task(SAMPLE_STATE_MD, "编写完整端到端测试")
    state = parser.parse_state(updated_md)

    # Assert
    assert len(state.tasks) == 4
    assert state.tasks[-1].text == "编写完整端到端测试"
    assert state.tasks[-1].completed is False
    # Ensure section headers after tasks are intact
    assert "## 3. 当前阻塞与风险 (Blockers)" in updated_md


def test_update_handover_note():
    # Arrange
    parser = MarkdownContextParser()

    # Act
    updated_md = parser.update_handover_note(
        SAMPLE_STATE_MD,
        author="豆包",
        note_body="完成了前端组件库封装，下一步请测试路由。",
        timestamp="2026-09-30 22:30",
    )
    state = parser.parse_state(updated_md)

    # Assert
    assert state.handover_note is not None
    assert state.handover_note.author == "豆包"
    assert "2026-09-30 22:30" in state.handover_note.timestamp
    assert "完成了前端组件库封装" in state.handover_note.body


def test_parse_and_append_decisions():
    # Arrange
    parser = MarkdownContextParser()

    # Act: Parse existing
    decisions = parser.parse_decisions(SAMPLE_DECISIONS_MD)
    assert len(decisions.records) == 1
    assert decisions.records[0].id == "ADR-001"
    assert decisions.records[0].title == "采用轻量黑板模式"

    # Act: Append new
    appended_md = parser.append_decision(
        SAMPLE_DECISIONS_MD,
        title="引入 FastAPI 异步路由",
        proposer="Antigravity",
        context="需要高性能 REST API 与 WebSocket 支持",
        decision="采用 FastAPI 作为核心后端服务",
        consequence="提供标准 OpenAPI 文档与高并发处理能力",
        date="2026-09-30",
    )
    new_decisions = parser.parse_decisions(appended_md)

    # Assert
    assert len(new_decisions.records) == 2
    assert new_decisions.records[1].id == "ADR-002"
    assert new_decisions.records[1].title == "引入 FastAPI 异步路由"


def test_parse_system():
    # Arrange
    parser = MarkdownContextParser()

    # Act
    system = parser.parse_system(SAMPLE_SYSTEM_MD)

    # Assert
    assert system.project_name == "Context Cockpit"
    assert system.project_goal == "多 Agent 协同本地驾驶舱"
    assert "Python" in system.tech_stack
    assert "FastAPI" in system.tech_stack
    assert system.run_command == "uv run python -m context_cockpit.cli"
    assert system.test_command == "uv run pytest"
    assert len(system.critical_rules) == 2
