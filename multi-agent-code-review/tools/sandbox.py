"""Sandbox isolation for code execution.

Based on Codex tool sandboxing architecture:
- READONLY: Read-only file operations
- WORKSPACE_WRITE: Write to workspace only
- FULL_ACCESS: Full system access (dangerous)
"""

from __future__ import annotations

import os
import tempfile
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SandboxType(Enum):
    """Sandbox isolation levels."""
    READONLY = "readonly"           # Read-only operations
    WORKSPACE_WRITE = "workspace"   # Write to workspace only
    DANGEROUS_FULL_ACCESS = "full"  # Full system access


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    sandbox_type: SandboxType
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    max_execution_time: float = 30.0  # seconds
    max_memory_mb: int = 512


class Sandbox:
    """
    Isolated execution environment for code.

    Provides:
    - Path restrictions
    - Execution time limits
    - Memory limits (via configuration)
    - Temporary workspace isolation
    """

    def __init__(self, config: SandboxConfig):
        self.config = config
        self._workspace: Optional[Path] = None
        self._initialized = False

    def initialize(self) -> Path:
        """
        Initialize the sandbox workspace.

        Returns:
            Path to the sandbox workspace
        """
        if self._initialized:
            return self._workspace

        # Create temporary workspace
        self._workspace = Path(tempfile.mkdtemp(prefix="aicoder_sandbox_"))
        self._initialized = True
        return self._workspace

    def get_workspace(self) -> Optional[Path]:
        """Get the sandbox workspace path."""
        return self._workspace

    def is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is allowed in this sandbox.

        Args:
            path: Path to check

        Returns:
            True if path is allowed
        """
        if self.config.sandbox_type == SandboxType.READONLY:
            # Read-only: allow read, deny write
            return True  # Caller must check operation type

        if self.config.sandbox_type == SandboxType.WORKSPACE_WRITE:
            # Check against allowed paths
            if not self.config.allowed_paths:
                # Default: only workspace
                if self._workspace:
                    try:
                        rel = Path(path).resolve().relative_to(self._workspace.resolve())
                        return True
                    except ValueError:
                        return False

            # Check against explicit allowed paths
            for allowed in self.config.allowed_paths:
                if Path(path).resolve().is_relative_to(Path(allowed).resolve()):
                    return True
            return False

        # FULL_ACCESS: allow everything
        return True

    def can_write(self, path: str) -> bool:
        """Check if writing to path is allowed."""
        if self.config.sandbox_type == SandboxType.READONLY:
            return False
        return self.is_path_allowed(path)

    def cleanup(self):
        """Clean up sandbox resources."""
        if self._workspace and self._workspace.exists():
            shutil.rmtree(self._workspace, ignore_errors=True)
        self._initialized = False
        self._workspace = None

    def __enter__(self) -> "Sandbox":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


class SandboxManager:
    """
    Manages sandbox creation and lifecycle.

    Based on Codex's SandboxManager.
    """

    def __init__(self):
        self._sandboxes: Dict[str, Sandbox] = {}
        self._default_config = SandboxConfig(
            sandbox_type=SandboxType.WORKSPACE_WRITE,
            max_execution_time=30.0,
            max_memory_mb=512,
        )

    def create_sandbox(
        self,
        sandbox_id: Optional[str] = None,
        config: Optional[SandboxConfig] = None,
    ) -> Sandbox:
        """
        Create a new sandbox.

        Args:
            sandbox_id: Optional ID for the sandbox
            config: Optional sandbox configuration

        Returns:
            Created sandbox
        """
        sandbox_id = sandbox_id or f"sandbox_{len(self._sandboxes)}"
        config = config or self._default_config

        sandbox = Sandbox(config)
        sandbox.initialize()

        self._sandboxes[sandbox_id] = sandbox
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> Optional[Sandbox]:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """
        Destroy a sandbox and clean up resources.

        Args:
            sandbox_id: ID of sandbox to destroy

        Returns:
            True if sandbox was found and destroyed
        """
        sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox:
            sandbox.cleanup()
            return True
        return False

    def destroy_all(self):
        """Destroy all sandboxes."""
        for sandbox_id in list(self._sandboxes.keys()):
            self.destroy_sandbox(sandbox_id)


# Global sandbox manager
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get or create the global sandbox manager."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
