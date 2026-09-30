"""Structure-preserving Markdown AST and section parser for .context/ files."""

from datetime import datetime
import hashlib
import re
from typing import Final

from context_cockpit.domain.exceptions import ParseError, TaskNotFoundError
from context_cockpit.domain.models import (
    ADRRecord,
    DecisionsContext,
    HandoverNote,
    Milestone,
    StateContext,
    SystemContext,
    TaskItem,
)

TASK_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^(?P<indent>\s*)-\s*\[(?P<checked>[ xX])\]\s*(?P<text>.+)$"
)


def compute_task_id(text: str) -> str:
    """Computes a stable deterministic task ID based on normalized text."""
    normalized = " ".join(text.strip().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    return f"task-{digest}"


class MarkdownContextParser:
    """Parses and mutates .context/ Markdown files with structure preservation."""

    # -------------------------------------------------------------------------
    # state.md Parsing and Mutation
    # -------------------------------------------------------------------------

    def parse_state(self, raw_text: str, content_hash: str = "") -> StateContext:
        """Parses state.md content into a structured StateContext domain entity."""
        lines = raw_text.splitlines()

        milestone_title = ""
        active_agent = ""
        tasks: list[TaskItem] = []
        blockers: list[str] = []

        current_section = ""
        handover_lines: list[str] = []
        in_handover = False

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Detect section headers
            if stripped.startswith("## 1.") or "当前里程碑" in stripped:
                current_section = "milestone"
                continue
            elif stripped.startswith("## 2.") or "任务清单" in stripped:
                current_section = "tasks"
                continue
            elif stripped.startswith("## 3.") or "当前阻塞" in stripped:
                current_section = "blockers"
                continue
            elif stripped.startswith("## 4.") or "交接便签" in stripped:
                current_section = "handover"
                in_handover = True
                continue
            elif stripped.startswith("## ") and current_section != "":
                current_section = "other"
                in_handover = False

            # Extract by section
            if current_section == "milestone":
                if "当前阶段目标" in line or "里程碑" in line:
                    match = re.search(r"[:：]\s*(.+)$", line)
                    if match:
                        milestone_title = match.group(1).strip()
                elif "负责人" in line or "Active Agent" in line:
                    match = re.search(r"[:：]\s*(.+)$", line)
                    if match:
                        active_agent = match.group(1).strip()

            elif current_section == "tasks":
                match = TASK_REGEX.match(line)
                if match:
                    indent = len(match.group("indent"))
                    checked = match.group("checked").lower() == "x"
                    task_text = match.group("text").strip()
                    task_id = compute_task_id(task_text)
                    tasks.append(
                        TaskItem(
                            id=task_id,
                            text=task_text,
                            completed=checked,
                            line_number=idx,
                            indent_level=indent,
                        )
                    )

            elif current_section == "blockers":
                if stripped.startswith("- "):
                    blocker_text = stripped[2:].strip()
                    if blocker_text and blocker_text != "无":
                        blockers.append(blocker_text)

            elif in_handover:
                handover_lines.append(line)

        # Parse Handover note
        handover_note = None
        if handover_lines:
            author = ""
            timestamp = ""
            clean_body_lines: list[str] = []
            for hline in handover_lines:
                if "交接记录人" in hline or "记录人" in hline:
                    m = re.search(r"[:：]\s*(\S+)", hline)
                    if m:
                        author = m.group(1).strip("*_ >")
                elif "交接时间" in hline or "时间" in hline:
                    m = re.search(r"[:：]\s*(.+)$", hline)
                    if m:
                        timestamp = m.group(1).strip("*_ >")
                else:
                    clean_body_lines.append(hline)

            full_body = "\n".join(clean_body_lines).strip()
            handover_note = HandoverNote(
                author=author or "Agent",
                timestamp=timestamp or "",
                body=full_body,
            )

        return StateContext(
            milestone=Milestone(title=milestone_title, active_agent=active_agent),
            tasks=tuple(tasks),
            blockers=tuple(blockers),
            handover_note=handover_note,
            content_hash=content_hash,
            raw_content=raw_text,
        )

    def toggle_task(self, raw_text: str, task_id: str, completed: bool) -> str:
        """Toggles a task's checkbox status in-place while strictly preserving original formatting."""
        lines = raw_text.splitlines()
        found = False
        new_lines: list[str] = []

        target_mark = "x" if completed else " "

        for line in lines:
            match = TASK_REGEX.match(line)
            if match:
                task_text = match.group("text").strip()
                current_id = compute_task_id(task_text)
                if current_id == task_id:
                    indent = match.group("indent")
                    new_line = f"{indent}- [{target_mark}] {task_text}"
                    new_lines.append(new_line)
                    found = True
                    continue
            new_lines.append(line)

        if not found:
            raise TaskNotFoundError(task_id)

        # Maintain trailing newline if original had it
        ending = "\n" if raw_text.endswith("\n") else ""
        return "\n".join(new_lines) + ending

    def add_task(self, raw_text: str, task_text: str) -> str:
        """Adds a new task to the Task Checklist section while preserving surrounding format."""
        clean_text = task_text.strip()
        lines = raw_text.splitlines()

        # Find the line index of "## 2. 任务清单"
        tasks_header_idx = -1
        next_section_idx = len(lines)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if tasks_header_idx == -1:
                if stripped.startswith("## 2.") or "任务清单" in stripped:
                    tasks_header_idx = i
            else:
                # We are inside the tasks section; look for the next section
                if stripped.startswith("## ") or stripped.startswith("---"):
                    next_section_idx = i
                    break

        if tasks_header_idx == -1:
            raise ParseError("state.md", "Could not locate '## 2. 任务清单' section")

        # Find the last task bullet before next section
        insert_idx = next_section_idx
        for i in range(next_section_idx - 1, tasks_header_idx, -1):
            if TASK_REGEX.match(lines[i]):
                insert_idx = i + 1
                break

        new_task_line = f"- [ ] {clean_text}"
        lines.insert(insert_idx, new_task_line)

        ending = "\n" if raw_text.endswith("\n") else ""
        return "\n".join(lines) + ending

    def update_handover_note(
        self,
        raw_text: str,
        author: str,
        note_body: str,
        timestamp: str | None = None,
    ) -> str:
        """Updates or replaces the Handover Note section in state.md."""
        now_str = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = raw_text.splitlines()

        handover_header_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("## 4.") or "交接便签" in line:
                handover_header_idx = i
                break

        formatted_note = [
            f"> **交接记录人**：{author}",
            f"> **交接时间**：{now_str}",
            "> **本次产出与交接说明**：",
        ]
        for bline in note_body.strip().splitlines():
            formatted_note.append(f"> {bline}")

        if handover_header_idx != -1:
            # Retain everything up to the header line
            prefix = lines[: handover_header_idx + 1]
            return "\n".join(prefix) + "\n" + "\n".join(formatted_note) + "\n"
        else:
            # Append handover note at bottom
            section = [
                "",
                "---",
                "",
                "## 4. 上一个 Agent 的交接便签 (Handover Note)",
                *formatted_note,
                "",
            ]
            return raw_text.rstrip() + "\n" + "\n".join(section)

    # -------------------------------------------------------------------------
    # decisions.md Parsing and Mutation
    # -------------------------------------------------------------------------

    def parse_decisions(self, raw_text: str, content_hash: str = "") -> DecisionsContext:
        """Parses decisions.md into a collection of ADRRecords."""
        records: list[ADRRecord] = []
        blocks = re.split(r"\n(?=###\s+\[ADR-\d+\])", raw_text)

        for block in blocks:
            header_match = re.search(r"###\s+\[(?P<id>ADR-\d+)\]\s*(?P<title>.+)", block)
            if not header_match:
                continue

            adr_id = header_match.group("id").strip()
            adr_title = header_match.group("title").strip()

            date_m = re.search(r"-\s*\*\*日期\*\*\s*[:：]\s*(.+)", block)
            proposer_m = re.search(r"-\s*\*\*提议\s*Agent\*\*\s*[:：]\s*(.+)", block)
            context_m = re.search(r"-\s*\*\*背景\*\*\s*[:：]\s*(.+)", block)
            decision_m = re.search(r"-\s*\*\*决策内容\*\*\s*[:：]\s*([\s\S]+?)(?=\n-\s*\*\*影响|\Z)", block)
            consequence_m = re.search(r"-\s*\*\*影响\*\*\s*[:：]\s*([\s\S]+?)(?=\n---|###|\Z)", block)

            records.append(
                ADRRecord(
                    id=adr_id,
                    title=adr_title,
                    date=date_m.group(1).strip() if date_m else "",
                    proposer=proposer_m.group(1).strip() if proposer_m else "",
                    context=context_m.group(1).strip() if context_m else "",
                    decision=decision_m.group(1).strip() if decision_m else "",
                    consequence=consequence_m.group(1).strip() if consequence_m else "",
                    raw_content=block.strip(),
                )
            )

        return DecisionsContext(
            records=tuple(records),
            content_hash=content_hash,
            raw_content=raw_text,
        )

    def append_decision(
        self,
        raw_text: str,
        title: str,
        proposer: str,
        context: str,
        decision: str,
        consequence: str,
        date: str | None = None,
    ) -> str:
        """Appends a new ADR block into decisions.md with auto-incremented ADR ID."""
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        existing_ids = re.findall(r"\[ADR-(\d+)\]", raw_text)
        next_num = max([int(n) for n in existing_ids], default=0) + 1
        new_id = f"ADR-{next_num:03d}"

        new_adr_block = [
            "",
            "---",
            "",
            f"### [{new_id}] {title.strip()}",
            f"- **日期**：{date_str}",
            f"- **提议 Agent**：{proposer.strip()}",
            f"- **背景**：{context.strip()}",
            f"- **决策内容**：{decision.strip()}",
            f"- **影响**：{consequence.strip()}",
            "",
        ]

        return raw_text.rstrip() + "\n" + "\n".join(new_adr_block)

    # -------------------------------------------------------------------------
    # system.md Parsing
    # -------------------------------------------------------------------------

    def parse_system(self, raw_text: str, content_hash: str = "") -> SystemContext:
        """Parses system.md to extract core project specification."""
        project_name = ""
        project_goal = ""
        tech_stack: list[str] = []
        run_command = ""
        test_command = ""
        rules: list[str] = []

        current_sec = ""
        for line in raw_text.splitlines():
            s = line.strip()
            if "1. 项目基本信息" in s:
                current_sec = "info"
                continue
            elif "2. 环境与运行方式" in s:
                current_sec = "env"
                continue
            elif "3. 编码规范与红线约束" in s:
                current_sec = "rules"
                continue
            elif s.startswith("## "):
                current_sec = "other"

            if current_sec == "info":
                if "项目名称" in s:
                    m = re.search(r"[:：]\s*(.+)", s)
                    if m:
                        project_name = m.group(1).strip()
                elif "项目目标" in s:
                    m = re.search(r"[:：]\s*(.+)", s)
                    if m:
                        project_goal = m.group(1).strip()
                elif "技术栈" in s:
                    m = re.search(r"[:：]\s*(.+)", s)
                    if m:
                        tech_stack = [item.strip() for item in m.group(1).split("/") if item.strip()]

            elif current_sec == "env":
                if "启动命令" in s or "运行命令" in s:
                    m = re.search(r"[:：]\s*`?([^`]+)`?", s)
                    if m:
                        run_command = m.group(1).strip()
                elif "测试命令" in s:
                    m = re.search(r"[:：]\s*`?([^`]+)`?", s)
                    if m:
                        test_command = m.group(1).strip()

            elif current_sec == "rules":
                if s.startswith("- **规则") or s.startswith("- 规则"):
                    m = re.search(r"[:：]\s*(.+)", s)
                    if m:
                        rules.append(m.group(1).strip())

        return SystemContext(
            project_name=project_name,
            project_goal=project_goal,
            tech_stack=tuple(tech_stack),
            run_command=run_command,
            test_command=test_command,
            critical_rules=tuple(rules),
            content_hash=content_hash,
            raw_content=raw_text,
        )
