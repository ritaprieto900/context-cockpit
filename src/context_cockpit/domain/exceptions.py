"""Domain exceptions for Context Cockpit."""

class CockpitError(Exception):
    """Base exception for all domain and infrastructure errors in Context Cockpit."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ContextNotFoundError(CockpitError):
    """Raised when .context/ directory or required context files are missing."""
    def __init__(self, path: str) -> None:
        super().__init__(f"Context resource not found at: {path}", code="NOT_FOUND")
        self.path = path


class ParseError(CockpitError):
    """Raised when parsing a Markdown context file encounters an unrecoverable syntax issue."""
    def __init__(self, filename: str, reason: str, line_number: int | None = None) -> None:
        location = f" at line {line_number}" if line_number is not None else ""
        super().__init__(f"Failed to parse {filename}{location}: {reason}", code="PARSE_ERROR")
        self.filename = filename
        self.reason = reason
        self.line_number = line_number


class StorageError(CockpitError):
    """Raised when atomic write or disk operation fails."""
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Storage failure for {path}: {reason}", code="STORAGE_ERROR")
        self.path = path
        self.reason = reason


class ConcurrencyLockError(CockpitError):
    """Raised when an operation cannot acquire the file lock within the timeout."""
    def __init__(self, path: str, timeout: float) -> None:
        super().__init__(f"Timeout waiting for lock on {path} after {timeout:.1f}s", code="LOCK_TIMEOUT")
        self.path = path
        self.timeout = timeout


class TaskNotFoundError(CockpitError):
    """Raised when attempting to modify a task that does not exist."""
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task not found with ID: {task_id}", code="TASK_NOT_FOUND")
        self.task_id = task_id
