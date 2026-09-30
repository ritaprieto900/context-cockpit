"""Workspace and Git metadata resolution service."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitMetadata:
    """Current Git workspace status."""
    is_git: bool
    branch: str | None = None
    commit_hash: str | None = None
    dirty: bool = False


class WorkspaceService:
    """Provides project workspace context and Git repository awareness."""

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path.resolve()

    @property
    def context_dir(self) -> Path:
        return self.workspace_path / ".context"

    @property
    def state_file(self) -> Path:
        return self.context_dir / "state.md"

    @property
    def decisions_file(self) -> Path:
        return self.context_dir / "decisions.md"

    @property
    def system_file(self) -> Path:
        return self.context_dir / "system.md"

    @property
    def agents_file(self) -> Path:
        return self.workspace_path / "AGENTS.md"

    def is_initialized(self) -> bool:
        """Returns True if the .context/ directory exists with core files."""
        return (
            self.context_dir.exists()
            and self.state_file.exists()
            and self.decisions_file.exists()
            and self.system_file.exists()
        )

    def get_git_metadata(self) -> GitMetadata:
        """Inspects Git repository information in a robust, non-blocking manner."""
        try:
            # Check if inside git work tree
            res_tree = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res_tree.returncode != 0:
                return GitMetadata(is_git=False)

            # Get current branch
            res_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=2,
            )
            branch = res_branch.stdout.strip() or "HEAD (detached)"

            # Get short commit hash
            res_commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=2,
            )
            commit = res_commit.stdout.strip() if res_commit.returncode == 0 else None

            # Check dirty
            res_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=2,
            )
            dirty = bool(res_status.stdout.strip())

            return GitMetadata(
                is_git=True,
                branch=branch,
                commit_hash=commit,
                dirty=dirty,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return GitMetadata(is_git=False)
