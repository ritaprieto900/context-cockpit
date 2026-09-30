"""Watchdog-based debounced file system observer for .context/ directory."""

import asyncio
import hashlib
from pathlib import Path
import threading
import time
from typing import Callable
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from context_cockpit.services.event_bus import ContextChangeEvent, EventBus


class ContextFileEventHandler(FileSystemEventHandler):
    """Handles file modification events with debouncing and content hash verification."""

    def __init__(
        self,
        context_dir: Path,
        event_bus: EventBus,
        loop: asyncio.AbstractEventLoop,
        debounce_seconds: float = 0.25,
    ) -> None:
        super().__init__()
        self.context_dir = context_dir
        self.event_bus = event_bus
        self.loop = loop
        self.debounce_seconds = debounce_seconds

        self._last_event_time: dict[str, float] = {}
        self._last_hashes: dict[str, str] = {}
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        # Only watch .md files in the context directory (ignore lock or temp files)
        if file_path.suffix != ".md" or file_path.name.startswith("."):
            return

        now = time.time()
        with self._lock:
            last_time = self._last_event_time.get(file_path.name, 0.0)
            if now - last_time < self.debounce_seconds:
                return
            self._last_event_time[file_path.name] = now

        # Read content and compute hash to verify real change
        try:
            content = file_path.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        except (OSError, UnicodeDecodeError):
            return

        with self._lock:
            prev_hash = self._last_hashes.get(file_path.name)
            if prev_hash == content_hash:
                return
            self._last_hashes[file_path.name] = content_hash

        # Dispatch event to the async event loop
        evt = ContextChangeEvent(
            filename=file_path.name,
            event_type="disk_modified",
            metadata={"hash": content_hash},
        )
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.event_bus.publish(evt), self.loop)


class ContextDirectoryWatcher:
    """Manages the background Watchdog observer lifecycle."""

    def __init__(
        self,
        context_dir: Path,
        event_bus: EventBus,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.context_dir = context_dir
        self.event_bus = event_bus
        self.loop = loop
        self._observer: Observer | None = None

    def start(self) -> None:
        if not self.context_dir.exists():
            return

        handler = ContextFileEventHandler(
            context_dir=self.context_dir,
            event_bus=self.event_bus,
            loop=self.loop,
        )
        self._observer = Observer()
        self._observer.schedule(handler, str(self.context_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2.0)
