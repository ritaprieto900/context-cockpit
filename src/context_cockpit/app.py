"""FastAPI application factory and lifecycle management."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from context_cockpit.api.router import get_context_service, router
from context_cockpit.api.websocket import ws_router
from context_cockpit.infrastructure.parser import MarkdownContextParser
from context_cockpit.infrastructure.storage import AtomicStorage
from context_cockpit.infrastructure.watcher import ContextDirectoryWatcher
from context_cockpit.services.context_service import ContextService
from context_cockpit.services.event_bus import global_event_bus
from context_cockpit.services.workspace import WorkspaceService


def create_app(workspace_path: Path | None = None) -> FastAPI:
    """Creates and configures a production-ready FastAPI application."""
    root_path = (workspace_path or Path.cwd()).resolve()

    workspace_service = WorkspaceService(root_path)
    storage = AtomicStorage(lock_timeout=5.0)
    parser = MarkdownContextParser()
    context_service = ContextService(
        workspace_service=workspace_service,
        storage=storage,
        parser=parser,
        event_bus=global_event_bus,
    )

    watcher: ContextDirectoryWatcher | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: start background file observer
        nonlocal watcher
        loop = asyncio.get_running_loop()
        watcher = ContextDirectoryWatcher(
            context_dir=workspace_service.context_dir,
            event_bus=global_event_bus,
            loop=loop,
        )
        watcher.start()
        yield
        # Shutdown: stop observer gracefully
        if watcher:
            watcher.stop()

    app = FastAPI(
        title="Context Cockpit API",
        version="0.1.0",
        description="Local Developer Cockpit for Multi-Agent Collaboration",
        lifespan=lifespan,
    )

    # Prevent DNS rebinding attacks: strictly validate Host header against localhost & loopback
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "*.localhost"],
    )

    # Enable CORS strictly for local dev / localhost origins to prevent drive-by attacks
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inject dependency
    app.dependency_overrides[get_context_service] = lambda: context_service

    # Include REST and WebSocket routers
    app.include_router(router)
    app.include_router(ws_router)

    # Mount UI static directory if built
    dist_dir = Path(__file__).parent / "ui" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="ui")

    return app
