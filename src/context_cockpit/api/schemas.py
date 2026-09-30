"""Pydantic schemas for API request and response contracts."""

from pydantic import BaseModel, Field
from context_cockpit.domain.models import AgentType


class ToggleTaskRequest(BaseModel):
    task_id: str = Field(..., description="ID of the task to toggle")
    completed: bool = Field(..., description="Target completion status")


class AddTaskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Task description text")


class UpdateHandoverRequest(BaseModel):
    author: str = Field(default="Agent", max_length=100, description="Name or role of the author")
    body: str = Field(..., min_length=1, description="Markdown body of the handover note")


class CreateADRRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Title of the architecture decision")
    proposer: str = Field(default="Antigravity", max_length=100)
    context: str = Field(..., min_length=5, description="Background problem context")
    decision: str = Field(..., min_length=5, description="Decision made")
    consequence: str = Field(..., min_length=5, description="Impact and consequences")


class GeneratePromptRequest(BaseModel):
    agent_type: AgentType = Field(default=AgentType.DOUBAO, description="Target AI agent type")
    instruction: str = Field(default="", max_length=2000, description="Optional custom instruction")


class GeneratePromptResponse(BaseModel):
    agent_type: AgentType
    prompt: str
