"""Application service orchestrating context business operations and persistence."""

import asyncio
from pathlib import Path
from typing import Final

from context_cockpit.domain.exceptions import ContextNotFoundError
from context_cockpit.domain.models import (
    ADRRecord,
    AgentType,
    DecisionsContext,
    StateContext,
    SystemContext,
    WorkspaceOverview,
)
from context_cockpit.infrastructure.parser import MarkdownContextParser
from context_cockpit.infrastructure.prompt_engine import PromptEngine
from context_cockpit.infrastructure.storage import AtomicStorage
from context_cockpit.services.event_bus import ContextChangeEvent, EventBus
from context_cockpit.services.workspace import WorkspaceService


class ContextService:
    """Coordinates reading, mutating, and persisting multi-agent blackboard files."""

    def __init__(
        self,
        workspace_service: WorkspaceService,
        storage: AtomicStorage,
        parser: MarkdownContextParser,
        event_bus: EventBus,
    ) -> None:
        self.workspace = workspace_service
        self.storage = storage
        self.parser = parser
        self.event_bus = event_bus

    # -------------------------------------------------------------------------
    # Reads
    # -------------------------------------------------------------------------

    def get_state(self) -> StateContext:
        if not self.workspace.state_file.exists():
            raise ContextNotFoundError(str(self.workspace.state_file))
        content, content_hash = self.storage.read_text(self.workspace.state_file)
        return self.parser.parse_state(content, content_hash=content_hash)

    def get_decisions(self) -> DecisionsContext:
        if not self.workspace.decisions_file.exists():
            raise ContextNotFoundError(str(self.workspace.decisions_file))
        content, content_hash = self.storage.read_text(self.workspace.decisions_file)
        return self.parser.parse_decisions(content, content_hash=content_hash)

    def get_system(self) -> SystemContext:
        if not self.workspace.system_file.exists():
            raise ContextNotFoundError(str(self.workspace.system_file))
        content, content_hash = self.storage.read_text(self.workspace.system_file)
        return self.parser.parse_system(content, content_hash=content_hash)

    def get_overview(self) -> WorkspaceOverview:
        git_meta = self.workspace.get_git_metadata()
        state = self.get_state()
        decisions = self.get_decisions()
        system = self.get_system()

        return WorkspaceOverview(
            workspace_path=str(self.workspace.workspace_path),
            is_git=git_meta.is_git,
            git_branch=git_meta.branch,
            git_commit=git_meta.commit_hash,
            state=state,
            decisions=decisions,
            system=system,
        )

    # -------------------------------------------------------------------------
    # Mutations (Transactional: Read-Modify-Write fully enclosed in file lock)
    # -------------------------------------------------------------------------

    async def toggle_task(self, task_id: str, completed: bool) -> StateContext:
        def _transactional_toggle() -> tuple[str, str]:
            with self.storage.transaction(self.workspace.state_file) as (raw_text, _, save):
                updated_text = self.parser.toggle_task(raw_text, task_id=task_id, completed=completed)
                new_hash = save(updated_text)
                return updated_text, new_hash

        updated_text, new_hash = await asyncio.to_thread(_transactional_toggle)

        await self.event_bus.publish(
            ContextChangeEvent(
                filename="state.md",
                event_type="api_update",
                metadata={"action": "toggle_task", "task_id": task_id, "completed": completed},
            )
        )
        return self.parser.parse_state(updated_text, content_hash=new_hash)

    async def add_task(self, task_text: str) -> StateContext:
        def _transactional_add() -> tuple[str, str]:
            with self.storage.transaction(self.workspace.state_file) as (raw_text, _, save):
                updated_text = self.parser.add_task(raw_text, task_text=task_text)
                new_hash = save(updated_text)
                return updated_text, new_hash

        updated_text, new_hash = await asyncio.to_thread(_transactional_add)

        await self.event_bus.publish(
            ContextChangeEvent(
                filename="state.md",
                event_type="api_update",
                metadata={"action": "add_task", "task_text": task_text},
            )
        )
        return self.parser.parse_state(updated_text, content_hash=new_hash)

    async def update_handover_note(self, author: str, body: str) -> StateContext:
        def _transactional_handover() -> tuple[str, str]:
            with self.storage.transaction(self.workspace.state_file) as (raw_text, _, save):
                updated_text = self.parser.update_handover_note(raw_text, author=author, note_body=body)
                new_hash = save(updated_text)
                return updated_text, new_hash

        updated_text, new_hash = await asyncio.to_thread(_transactional_handover)

        await self.event_bus.publish(
            ContextChangeEvent(
                filename="state.md",
                event_type="api_update",
                metadata={"action": "update_handover", "author": author},
            )
        )
        return self.parser.parse_state(updated_text, content_hash=new_hash)

    async def create_decision(
        self,
        title: str,
        proposer: str,
        context: str,
        decision: str,
        consequence: str,
    ) -> DecisionsContext:
        def _transactional_decision() -> tuple[str, str]:
            with self.storage.transaction(self.workspace.decisions_file) as (raw_text, _, save):
                updated_text = self.parser.append_decision(
                    raw_text,
                    title=title,
                    proposer=proposer,
                    context=context,
                    decision=decision,
                    consequence=consequence,
                )
                new_hash = save(updated_text)
                return updated_text, new_hash

        updated_text, new_hash = await asyncio.to_thread(_transactional_decision)

        await self.event_bus.publish(
            ContextChangeEvent(
                filename="decisions.md",
                event_type="api_update",
                metadata={"action": "create_decision", "title": title},
            )
        )
        return self.parser.parse_decisions(updated_text, content_hash=new_hash)

    def generate_prompt(self, agent_type: AgentType, instruction: str = "") -> str:
        system = self.get_system()
        state = self.get_state()
        decisions = self.get_decisions()

        return PromptEngine.generate(
            agent_type=agent_type,
            system=system,
            state=state,
            decisions=decisions,
            instruction=instruction,
        )
