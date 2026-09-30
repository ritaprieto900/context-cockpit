"""Thread-safe and process-safe atomic storage layer."""

import hashlib
import os
from pathlib import Path
import tempfile
import uuid
from filelock import FileLock, Timeout

from context_cockpit.domain.exceptions import ConcurrencyLockError, StorageError


class AtomicStorage:
    """Provides atomic read and write operations with file locking to eliminate corruption."""

    def __init__(self, lock_timeout: float = 5.0) -> None:
        self.lock_timeout = lock_timeout

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

    def write_text_atomic(self, file_path: Path, content: str) -> str:
        """Writes content atomically using a temporary file in the same directory and filelock.

        Returns:
            The sha256 hash of the newly written content.

        Raises:
            ConcurrencyLockError: If lock acquisition times out.
            StorageError: If disk write or replace operation fails.
        """
        target_dir = file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        lock_path = target_dir / f".{file_path.name}.lock"
        lock = FileLock(str(lock_path), timeout=self.lock_timeout)

        try:
            with lock:
                # Use unique temp file on the same filesystem/drive to ensure os.replace is atomic
                temp_filename = f".{file_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
                temp_path = target_dir / temp_filename

                try:
                    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())

                    # Atomic replacement
                    os.replace(temp_path, file_path)
                    return hashlib.sha256(content.encode("utf-8")).hexdigest()
                finally:
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except OSError:
                            pass
        except Timeout as exc:
            raise ConcurrencyLockError(str(file_path), self.lock_timeout) from exc
        except Exception as exc:
            raise StorageError(str(file_path), f"Atomic write failed: {exc}") from exc
        finally:
            # Clean up lock file if not held
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except OSError:
                    pass
