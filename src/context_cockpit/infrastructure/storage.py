"""Thread-safe and process-safe atomic storage layer with transactional locking."""

import hashlib
import os
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout

from context_cockpit.domain.exceptions import ConcurrencyLockError, StorageError


class AtomicStorage:
    """Provides atomic read and write operations with transaction-level file locking.

    Guarantees ACID-like consistency for plain Markdown files without external database,
    preventing Lost Updates and race conditions across multiple AI Agents and editors.
    """

    def __init__(self, lock_timeout: float = 10.0) -> None:
        self.lock_timeout = lock_timeout

    def _get_lock(self, file_path: Path) -> FileLock:
        """Returns FileLock for target path.
        Note: Lock files are permanently retained on disk to preserve OS-level lock handles.
        """
        target_dir = file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        lock_path = target_dir / f".{file_path.name}.lock"
        return FileLock(str(lock_path), timeout=self.lock_timeout)

    def read_text(self, file_path: Path) -> tuple[str, str]:
        """Reads file content and returns (content, sha256_hash).

        Raises:
            StorageError: If file cannot be read.
        """
        if not file_path.exists():
            raise StorageError(str(file_path), "File does not exist")

        try:
            content = file_path.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            return content, content_hash
        except Exception as exc:
            raise StorageError(str(file_path), f"Failed to read file: {exc}") from exc

    def _write_atomic_unlocked(self, file_path: Path, content: str) -> str:
        """Internal helper to atomically write and fsync file via temporary swap without acquiring lock."""
        target_dir = file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        temp_filename = f".{file_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
        temp_path = target_dir / temp_filename

        try:
            with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Atomic replacement on POSIX and Windows (Python 3.3+)
            os.replace(temp_path, file_path)
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except Exception as exc:
            raise StorageError(str(file_path), f"Atomic write failed: {exc}") from exc
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    @contextmanager
    def transaction(
        self, file_path: Path
    ) -> Generator[tuple[str, str, Callable[[str], str]], None, None]:
        """Context manager covering the entire Read-Modify-Write cycle under an exclusive file lock.

        Yields:
            tuple of (current_content, current_hash, save_callback)
            where save_callback(new_content) performs the atomic write before releasing the lock.

        Raises:
            ConcurrencyLockError: If acquiring the lock times out.
            StorageError: If read or write fails.
        """
        lock = self._get_lock(file_path)
        try:
            with lock:
                if file_path.exists():
                    content, content_hash = self.read_text(file_path)
                else:
                    content, content_hash = "", hashlib.sha256(b"").hexdigest()

                def save(new_content: str) -> str:
                    return self._write_atomic_unlocked(file_path, new_content)

                yield content, content_hash, save
        except Timeout as exc:
            raise ConcurrencyLockError(str(file_path), self.lock_timeout) from exc

    def write_text_atomic(self, file_path: Path, content: str) -> str:
        """Writes content atomically under an exclusive lock."""
        lock = self._get_lock(file_path)
        try:
            with lock:
                return self._write_atomic_unlocked(file_path, content)
        except Timeout as exc:
            raise ConcurrencyLockError(str(file_path), self.lock_timeout) from exc
