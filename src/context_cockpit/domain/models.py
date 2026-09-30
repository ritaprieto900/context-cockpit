"""Domain entities and value objects for Context Cockpit."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgentType(StrEnum):
    """Known agent types for optimized prompt strategy synthesis."""
    ANTIGRAVITY = "antigravity"
    DOUBAO = "doubao"
    CURSOR = "cursor"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GENERIC = "generic"


class TaskItem(BaseModel):
    """Represents a discrete task item within the checklist."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique deterministic ID of the task")
    text: str = Field(description="Display text of the task without checkbox")
    completed: bool = Field(default=False, description="Whether the task is checked")
    line_number: int = Field(description="1-based original line number in file")
    indent_level: int = Field(default=0, description="Indent spaces prefixing the bullet")


class Milestone(BaseModel):
    """Current milestone summary from state.md."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(default="", description="Description of the active milestone")
    active_agent: str = Field(default="", description="Name of the currently responsible agent")


class HandoverNote(BaseModel):
    """Latest handover note left by the outgoing agent."""
    model_config = ConfigDict(frozen=True)

    author: str = Field(default="", description="Agent who wrote the note")
    timestamp: str = Field(default="", description="Date/time timestamp string")
    body: str = Field(default="", description="Full markdown body of the note")


class StateContext(BaseModel):
    """Complete parsed domain representation of .context/state.md."""
    model_config = ConfigDict(frozen=True)

    milestone: Milestone = Field(default_factory=Milestone)
    tasks: tuple[TaskItem, ...] = Field(default_factory=tuple)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    handover_note: HandoverNote | None = Field(default=None)
    content_hash: str = Field(default="", description="SHA-256 hash of raw file content")
    raw_content: str = Field(default="", description="Full unmodified text")


class ADRRecord(BaseModel):
    """Single Architecture Decision Record from .context/decisions.md."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Identifier e.g. ADR-001")
    title: str = Field(description="Title of the decision")
    date: str = Field(default="", description="Date of decision")
    proposer: str = Field(default="", description="Agent or engineer who proposed it")
    context: str = Field(default="", description="Context and background problem")
    decision: str = Field(default="", description="Decision summary")
    consequence: str = Field(default="", description="Consequences and trade-offs")
    raw_content: str = Field(default="")


class DecisionsContext(BaseModel):
    """Complete parsed domain representation of .context/decisions.md."""
    model_config = ConfigDict(frozen=True)

    records: tuple[ADRRecord, ...] = Field(default_factory=tuple)
    content_hash: str = Field(default="")
    raw_content: str = Field(default="")


class SystemContext(BaseModel):
    """Complete parsed domain representation of .context/system.md."""
    model_config = ConfigDict(frozen=True)

    project_name: str = Field(default="")
    project_goal: str = Field(default="")
    tech_stack: tuple[str, ...] = Field(default_factory=tuple)
    run_command: str = Field(default="")
    test_command: str = Field(default="")
    critical_rules: tuple[str, ...] = Field(default_factory=tuple)
    content_hash: str = Field(default="")
    raw_content: str = Field(default="")


class WorkspaceOverview(BaseModel):
    """Aggregate domain view of a project's complete multi-agent context."""
    model_config = ConfigDict(frozen=True)

    workspace_path: str
    is_git: bool = False
    git_branch: str | None = None
    git_commit: str | None = None
    state: StateContext
    decisions: DecisionsContext
    system: SystemContext
