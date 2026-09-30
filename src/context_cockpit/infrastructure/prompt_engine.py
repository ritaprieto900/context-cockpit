"""Prompt strategy engine synthesizing targeted prompts for different AI agents."""

from abc import ABC, abstractmethod
from typing import Final

from context_cockpit.domain.models import (
    AgentType,
    DecisionsContext,
    StateContext,
    SystemContext,
)


class BasePromptStrategy(ABC):
    """Abstract base class for agent-specific prompt synthesis."""

    @abstractmethod
    def synthesize(
        self,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        """Synthesizes a target-specific prompt string."""
        pass


class DoubaoPromptStrategy(BasePromptStrategy):
    """Generates structured prompts tailored for Doubao (豆包)."""

    def synthesize(
        self,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        rules_text = "\n".join(f"- {r}" for r in system.critical_rules) if system.critical_rules else "- 遵守既定架构，不破坏既有设计。"

        pending_tasks = [t for t in state.tasks if not t.completed]
        tasks_text = "\n".join(f"- [ ] {t.text}" for t in pending_tasks) if pending_tasks else "- 暂无待处理任务"

        recent_adrs = decisions.records[-3:] if decisions.records else []
        adr_text = "\n".join(f"- **{a.id} {a.title}**：{a.decision}" for a in recent_adrs) or "- 无特殊决策约束"

        handover_text = state.handover_note.body if state.handover_note else "无上一个 Agent 的特别留言。"
        handover_author = state.handover_note.author if state.handover_note else "上个 Agent"

        custom_instruction = f"\n### 本次特别要求\n{instruction}\n" if instruction.strip() else ""

        return f"""你好，豆包！你现在正在与团队共同开发【{system.project_name or '本项目'}】。
本项目严格执行 Git 黑板协作模式（通过 `.context/` 共享状态）。请仔细阅读以下上下文并协助推进工作：

---

### 1. 全局规范与工程红线
- **核心技术栈**：{', '.join(system.tech_stack) if system.tech_stack else '参考项目配置'}
- **启动命令**：`{system.run_command or '未指定'}`
- **测试命令**：`{system.test_command or '未指定'}`
- **红线约束**：
{rules_text}

### 2. 关键架构决策 (ADR)
{adr_text}

### 3. 上一个 Agent（{handover_author}）的交接指引
> {handover_text.replace(chr(10), chr(10) + '> ')}

### 4. 当前待办任务清单
{tasks_text}
{custom_instruction}
---

### 任务交付要求
1. 请聚焦处理任务清单中的下一项待办任务；
2. 编码时请严格遵守上述红线约束，不要擅自推翻已有技术选型；
3. 完成后，请按照看板格式输出一段**交接便签（Handover Note）**，说明你修改了哪些内容以及留给下一个 Agent 的建议。
"""


class CursorPromptStrategy(BasePromptStrategy):
    """Generates concise, rule-focused prompts tailored for Cursor Composer / Agent."""

    def synthesize(
        self,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        rules_text = "\n".join(f"- {r}" for r in system.critical_rules)
        pending_tasks = "\n".join(f"- [ ] {t.text}" for t in state.tasks if not t.completed)
        handover = state.handover_note.body if state.handover_note else "Continue task list."

        custom = f"\n[User Directive]: {instruction}\n" if instruction.strip() else ""

        return f"""# Project Context: {system.project_name}
Tech Stack: {', '.join(system.tech_stack)}
Run: `{system.run_command}` | Test: `{system.test_command}`

## Constraints & Rules
{rules_text}

## Handover Instructions from previous agent
{handover}

## Active Tasks
{pending_tasks}
{custom}
Instructions:
- Pick the first uncompleted task and implement it cleanly.
- Respect all rules strictly.
- When done, summarize modified files and provide next step advice.
"""


class ClaudePromptStrategy(BasePromptStrategy):
    """Generates concise, task-driven prompts tailored for Claude Code CLI."""

    def synthesize(
        self,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        rules_text = "\n".join(f"  * {r}" for r in system.critical_rules)
        pending_tasks = "\n".join(f"  * [ ] {t.text}" for t in state.tasks if not t.completed)
        handover = state.handover_note.body if state.handover_note else "No specific handover."

        custom = f"\nSpecific goal: {instruction}\n" if instruction.strip() else ""

        return f"""Context: We are collaborating via .context/ blackboard architecture on {system.project_name}.
Commands: Run via `{system.run_command}`, Test via `{system.test_command}`.

Key Rules:
{rules_text}

Handover note from predecessor:
{handover}

Pending tasks:
{pending_tasks}
{custom}
Please execute the next actionable task, run tests to verify, and output a concise Handover Note for the next session.
"""


class GenericPromptStrategy(BasePromptStrategy):
    """Fallback general-purpose Markdown prompt suitable for ChatGPT, DeepSeek, or web portals."""

    def synthesize(
        self,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        rules_text = "\n".join(f"- {r}" for r in system.critical_rules) or "- 保持既有代码规范"
        pending_tasks = "\n".join(f"- [ ] {t.text}" for t in state.tasks if not t.completed)
        recent_adrs = "\n".join(f"- [{a.id}] {a.title}: {a.decision}" for a in decisions.records[-3:])

        custom = f"\n### 当前指令\n{instruction}\n" if instruction.strip() else ""

        return f"""# 项目协作上下文：{system.project_name}

本项目使用 Git 黑板协作模式，请根据当前项目进展推进任务：

### 系统规范
- **技术栈**：{', '.join(system.tech_stack)}
- **命令**：启动 `{system.run_command}`，测试 `{system.test_command}`
- **红线约束**：
{rules_text}

### 架构决策 (ADR)
{recent_adrs or '暂无'}

### 上一个 Agent 的交接便签
{state.handover_note.body if state.handover_note else '暂无'}

### 待办任务清单
{pending_tasks or '- 任务已全部完成'}
{custom}
请基于上述信息实现对应功能，并更新交接说明。
"""


class PromptEngine:
    """Factory and dispatcher for prompt synthesis strategies."""

    _strategies: Final[dict[AgentType, BasePromptStrategy]] = {
        AgentType.DOUBAO: DoubaoPromptStrategy(),
        AgentType.CURSOR: CursorPromptStrategy(),
        AgentType.CLAUDE: ClaudePromptStrategy(),
        AgentType.GENERIC: GenericPromptStrategy(),
        AgentType.DEEPSEEK: GenericPromptStrategy(),
        AgentType.ANTIGRAVITY: GenericPromptStrategy(),
    }

    @classmethod
    def generate(
        cls,
        agent_type: AgentType,
        system: SystemContext,
        state: StateContext,
        decisions: DecisionsContext,
        instruction: str = "",
    ) -> str:
        strategy = cls._strategies.get(agent_type, cls._strategies[AgentType.GENERIC])
        return strategy.synthesize(system, state, decisions, instruction)
