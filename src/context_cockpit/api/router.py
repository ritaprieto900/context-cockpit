"""FastAPI REST router for Context Cockpit endpoints."""

import asyncio
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from context_cockpit.api.schemas import (
    AddTaskRequest,
    CreateADRRequest,
    GeneratePromptRequest,
    GeneratePromptResponse,
    ToggleTaskRequest,
    UpdateHandoverRequest,
)
from context_cockpit.domain.exceptions import CockpitError, ContextNotFoundError, TaskNotFoundError
from context_cockpit.domain.models import (
    DecisionsContext,
    StateContext,
    SystemContext,
    WorkspaceOverview,
)
from context_cockpit.services.context_service import ContextService

router = APIRouter(prefix="/api", tags=["context"])


def get_context_service() -> ContextService:
    """Dependency provider placeholder overridden at app creation time."""
    raise NotImplementedError("ContextService dependency must be overridden by app factory")


ServiceDep = Annotated[ContextService, Depends(get_context_service)]


@router.get("/overview", response_model=WorkspaceOverview)
async def get_workspace_overview(service: ServiceDep) -> WorkspaceOverview:
    try:
        return await asyncio.to_thread(service.get_overview)
    except ContextNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.get("/state", response_model=StateContext)
async def get_state(service: ServiceDep) -> StateContext:
    try:
        return await asyncio.to_thread(service.get_state)
    except ContextNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/decisions", response_model=DecisionsContext)
async def get_decisions(service: ServiceDep) -> DecisionsContext:
    try:
        return await asyncio.to_thread(service.get_decisions)
    except ContextNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/system", response_model=SystemContext)
async def get_system(service: ServiceDep) -> SystemContext:
    try:
        return await asyncio.to_thread(service.get_system)
    except ContextNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/tasks/toggle", response_model=StateContext)
async def toggle_task(payload: ToggleTaskRequest, service: ServiceDep) -> StateContext:
    try:
        return await service.toggle_task(task_id=payload.task_id, completed=payload.completed)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.post("/tasks", response_model=StateContext)
async def add_task(payload: AddTaskRequest, service: ServiceDep) -> StateContext:
    try:
        return await service.add_task(task_text=payload.text)
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.post("/handover", response_model=StateContext)
async def update_handover(payload: UpdateHandoverRequest, service: ServiceDep) -> StateContext:
    try:
        return await service.update_handover_note(author=payload.author, body=payload.body)
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.post("/adrs", response_model=DecisionsContext)
async def create_adr(payload: CreateADRRequest, service: ServiceDep) -> DecisionsContext:
    try:
        return await service.create_decision(
            title=payload.title,
            proposer=payload.proposer,
            context=payload.context,
            decision=payload.decision,
            consequence=payload.consequence,
        )
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.post("/prompt", response_model=GeneratePromptResponse)
async def generate_prompt(payload: GeneratePromptRequest, service: ServiceDep) -> GeneratePromptResponse:
    try:
        result = await asyncio.to_thread(
            service.generate_prompt,
            agent_type=payload.agent_type,
            instruction=payload.instruction,
        )
        return GeneratePromptResponse(agent_type=payload.agent_type, prompt=result)
    except CockpitError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
