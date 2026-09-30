"""Model Context Protocol (MCP) server for Context Cockpit."""

import json
from pathlib import Path
from mcp.server.mcpserver import MCPServer

from context_cockpit.domain.models import AgentType
from context_cockpit.infrastructure.parser import MarkdownContextParser
from context_cockpit.infrastructure.storage import AtomicStorage
from context_cockpit.services.context_service import ContextService
from context_cockpit.services.event_bus import global_event_bus
from context_cockpit.services.workspace import WorkspaceService


def create_mcp_server(workspace_path: Path | None = None) -> MCPServer:
    """Builds and returns an MCPServer exposing Context Cockpit tools to AI agents."""
    root_path = (workspace_path or Path.cwd()).resolve()

    workspace_service = WorkspaceService(root_path)
    storage = AtomicStorage(lock_timeout=5.0)
    parser = MarkdownContextParser()
    service = ContextService(
        workspace_service=workspace_service,
        storage=storage,
        parser=parser,
        event_bus=global_event_bus,
    )

    mcp = MCPServer(
        name="context-cockpit",
        version="0.1.0",
        description="Local Developer Cockpit & Shared Blackboard for Multi-Agent Collaboration",
    )

    # -------------------------------------------------------------------------
    # Tools
    # -------------------------------------------------------------------------

    @mcp.tool()
    def cockpit_get_overview() -> str:
        """Returns the full project overview, active milestone, git status, and recent ADRs."""
        overview = service.get_overview()
        return json.dumps(overview.model_dump(), ensure_ascii=False, indent=2)

    @mcp.tool()
    def cockpit_get_ready_tasks() -> str:
        """Returns only uncompleted tasks that are currently unblocked and ready to work on."""
        state = service.get_state()
        ready = [
            {"id": t.id, "text": t.text, "line_number": t.line_number}
            for t in state.tasks
            if not t.completed
        ]
        return json.dumps(
            {
                "active_milestone": state.milestone.title,
                "responsible_agent": state.milestone.active_agent,
                "ready_tasks_count": len(ready),
                "tasks": ready,
            },
            ensure_ascii=False,
            indent=2,
        )

    @mcp.tool()
    async def cockpit_toggle_task(task_id: str, completed: bool = True) -> str:
        """Marks a task as completed or pending in the project checklist."""
        updated = await service.toggle_task(task_id=task_id, completed=completed)
        completed_count = sum(1 for t in updated.tasks if t.completed)
        total_count = len(updated.tasks)
        return json.dumps(
            {
                "success": True,
                "task_id": task_id,
                "completed": completed,
                "progress": f"{completed_count}/{total_count} ({int(completed_count / total_count * 100) if total_count else 0}%)",
            },
            ensure_ascii=False,
        )

    @mcp.tool()
    async def cockpit_add_task(task_text: str) -> str:
        """Adds a new actionable task to the active project checklist."""
        updated = await service.add_task(task_text=task_text)
        new_task = updated.tasks[-1] if updated.tasks else None
        return json.dumps(
            {
                "success": True,
                "task_id": new_task.id if new_task else None,
                "text": task_text,
                "total_tasks": len(updated.tasks),
            },
            ensure_ascii=False,
        )

    @mcp.tool()
    async def cockpit_create_adr(
        title: str,
        context: str,
        decision: str,
        consequence: str,
        proposer: str = "Agent",
    ) -> str:
        """Records a new Architecture Decision Record (ADR) in decisions.md to prevent conflicting implementations."""
        updated = await service.create_decision(
            title=title,
            proposer=proposer,
            context=context,
            decision=decision,
            consequence=consequence,
        )
        newest = updated.records[-1] if updated.records else None
        return json.dumps(
            {
                "success": True,
                "adr_id": newest.id if newest else "ADR-???",
                "title": title,
                "proposer": proposer,
            },
            ensure_ascii=False,
        )

    @mcp.tool()
    async def cockpit_land_the_plane(author: str, handover_note: str) -> str:
        """Session Handover Protocol ('Landing the plane'): Saves the handover note before concluding an agent session."""
        updated = await service.update_handover_note(author=author, body=handover_note)
        return json.dumps(
            {
                "success": True,
                "message": "Handover note persisted successfully to blackboard state.md",
                "author": author,
                "timestamp": updated.handover_note.timestamp if updated.handover_note else "",
            },
            ensure_ascii=False,
        )

    @mcp.tool()
    def cockpit_synthesize_prompt(target_agent: str, instruction: str = "") -> str:
        """Synthesizes an optimal handover prompt for another agent (e.g. 'doubao', 'cursor', 'claude')."""
        try:
            agent_type = AgentType(target_agent.lower())
        except ValueError:
            agent_type = AgentType.GENERIC
        return service.generate_prompt(agent_type=agent_type, instruction=instruction)

    # -------------------------------------------------------------------------
    # Resources
    # -------------------------------------------------------------------------

    @mcp.resource("cockpit://state")
    def get_state_resource() -> str:
        """Live content of .context/state.md."""
        return service.get_state().raw_content

    @mcp.resource("cockpit://decisions")
    def get_decisions_resource() -> str:
        """Live content of .context/decisions.md."""
        return service.get_decisions().raw_content

    @mcp.resource("cockpit://system")
    def get_system_resource() -> str:
        """Live content of .context/system.md."""
        return service.get_system().raw_content

    return mcp
