"""Skills system - Reusable capabilities for AI Coder.

Based on OpenAI Codex skills architecture.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

# Token estimation (rough approximation)
AVG_CHARS_PER_TOKEN = 4


class SkillError(Exception):
    """Base exception for skill errors."""
    pass


class SkillTimeoutError(SkillError):
    """Skill execution timed out."""
    pass


class SkillPermissionError(SkillError):
    """Skill operation not permitted."""
    pass


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Context:
    """Context passed to skill execution."""

    def __init__(
        self,
        workspace_path: str = ".",
        environment: Optional[Dict[str, str]] = None,
        session_id: Optional[str] = None,
    ):
        self.workspace_path = workspace_path
        self.environment = environment or {}
        self.session_id = session_id or "default"
        self.variables: Dict[str, Any] = {}

    def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)


class Skill(ABC):
    """Base class for all skills.

    Skills are reusable capabilities that agents can use.
    Based on OpenAI Codex skills architecture.
    """

    name: str = "base"
    description: str = "Base skill"
    enabled: bool = True
    timeout: int = 30  # seconds

    def __init__(self):
        self._last_result: Optional[SkillResult] = None

    @abstractmethod
    async def execute(self, context: Context, **kwargs) -> SkillResult:
        """Execute the skill.

        Args:
            context: Execution context
            **kwargs: Skill-specific parameters

        Returns:
            SkillResult with execution results
        """
        pass

    async def execute_with_timeout(self, context: Context, **kwargs) -> SkillResult:
        """Execute with timeout protection."""
        try:
            result = await asyncio.wait_for(
                self.execute(context, **kwargs),
                timeout=self.timeout
            )
            self._last_result = result
            return result
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Skill '{self.name}' timed out after {self.timeout}s",
            )

    @property
    def last_result(self) -> Optional[SkillResult]:
        return self._last_result

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // AVG_CHARS_PER_TOKEN


class SkillRegistry:
    """Registry for all available skills.

    Provides skill lookup and management.
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_classes: Dict[str, type] = {}

    def register(self, skill: Skill):
        """Register a skill instance."""
        self._skills[skill.name] = skill

    def register_class(self, skill_class: type):
        """Register a skill class by name."""
        instance = skill_class()
        self._skill_classes[skill_class.__name__] = skill_class
        self._skills[instance.name] = instance

    def get(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def get_enabled_skills(self) -> List[Skill]:
        """Get all enabled skills."""
        return [s for s in self._skills.values() if s.enabled]

    def create_skill(self, name: str, **kwargs) -> Optional[Skill]:
        """Create a new skill instance by name."""
        skill_class = self._skill_classes.get(name)
        if skill_class:
            return skill_class(**kwargs)
        return None


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """Get the global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _register_default_skills()
    return _registry


def _register_default_skills():
    """Register all default skills."""
    from .shell import ShellSkill
    from .code_runner import CodeRunnerSkill
    from .file_search import FileSearchSkill
    from .linter import LinterSkill

    registry = get_registry()
    registry.register_class(ShellSkill)
    registry.register_class(CodeRunnerSkill)
    registry.register_class(FileSearchSkill)
    registry.register_class(LinterSkill)
