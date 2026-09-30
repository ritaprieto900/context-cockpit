"""Pytest configuration and shared fixtures for Context Cockpit tests."""

from pathlib import Path
import pytest

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
