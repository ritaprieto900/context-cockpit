"""Watchdog-based debounced file system observer with trailing-edge timer."""

import asyncio
import hashlib
from pathlib import Path
import threading
from typing import Final
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from context_cockpit.services.event_bus import ContextChangeEvent, EventBus


class ContextFileEventHandler(FileSystemEventHandler):
    """Handles file modification events with true trailing-edge debouncing."""

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

        self._pending_timers: dict[str, threading.Timer] = {}
        self._last_hashes: dict[str, str] = {}
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        # Only watch .md files in the context directory (ignore lock or temp files)
        if file_path.suffix != ".md" or file_path.name.startswith("."):
            return

        filename = file_path.name

        with self._lock:
            # Cancel any existing trailing-edge timer for this file
            if filename in self._pending_timers:
                self._pending_timers[filename].cancel()

            # Schedule a new trailing-edge timer
            timer = threading.Timer(
                self.debounce_seconds,
                self._process_file_change,
                args=[file_path],
            )
            timer.daemon = True
            self._pending_timers[filename] = timer
            timer.start()

    def _process_file_change(self, file_path: Path) -> None:
        """Executed on trailing edge after debounce window has elapsed."""
        filename = file_path.name
        with self._lock:
            self._pending_timers.pop(filename, None)

        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        except (OSError, UnicodeDecodeError):
            return

        with self._lock:
            prev_hash = self._last_hashes.get(filename)
            if prev_hash == content_hash:
                return
            self._last_hashes[filename] = content_hash

        # Dispatch event to the async event loop
        evt = ContextChangeEvent(
            filename=filename,
            event_type="disk_modified",
            metadata={"hash": content_hash},
        )
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.event_bus.publish(evt), self.loop)

    def cancel_all(self) -> None:
        with self._lock:
            for timer in self._pending_timers.values():
                timer.cancel()
            self._pending_timers.clear()


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
        self._handler: ContextFileEventHandler | None = None
        self._observer: Observer | None = None

    def start(self) -> None:
        if not self.context_dir.exists():
            return

        self._handler = ContextFileEventHandler(
            context_dir=self.context_dir,
            event_bus=self.event_bus,
            loop=self.loop,
        )
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.context_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._handler:
            self._handler.cancel_all()
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2.0)
