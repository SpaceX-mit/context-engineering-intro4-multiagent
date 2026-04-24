"""Linter skill - Run code linters and formatters.

Based on OpenAI Codex linting capabilities.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from . import Context, Skill, SkillResult


class LintLevel(Enum):
    """Severity levels for lint issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    """Single linting issue."""
    file: str
    line: int
    column: int
    level: LintLevel
    rule: str
    message: str


@dataclass
class LintReport:
    """Full linting report."""
    issues: List[LintIssue]
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0

    def format(self) -> str:
        """Format report as string."""
        lines = []
        if self.issues:
            for issue in self.issues:
                lines.append(
                    f"{issue.file}:{issue.line}:{issue.column} "
                    f"[{issue.level.value}] {issue.rule}: {issue.message}"
                )
        else:
            return "No issues found."

        lines.append(f"\nSummary: {self.total_errors} errors, {self.total_warnings} warnings, {self.total_info} info")
        return "\n".join(lines)


class LinterSkill(Skill):
    """Run code linters and formatters.

    Supports ruff, mypy, and black.
    Based on Codex code quality tools.
    """

    name = "linter"
    description = "Run code linters (ruff, mypy, black)"
    timeout = 60

    def __init__(
        self,
        tools: Optional[List[str]] = None,
        fix: bool = False,
    ):
        super().__init__()
        self.tools = tools or ["ruff", "mypy"]
        self.fix = fix

    async def execute(self, context: Context, **kwargs) -> SkillResult:
        """Run linter(s) on code.

        Args:
            context: Execution context
            **kwargs: Tool and target parameters

        Returns:
            SkillResult with lint report
        """
        start_time = time.time()
        tool = kwargs.get("tool", "ruff")
        target = kwargs.get("target", context.workspace_path or ".")

        if tool == "ruff":
            return await self._run_ruff(context, target)
        elif tool == "mypy":
            return await self._run_mypy(context, target)
        elif tool == "black":
            return await self._run_black(context, target)
        elif tool == "all":
            return await self._run_all(context, target)
        else:
            return SkillResult(
                success=False,
                error=f"Unknown tool: {tool}",
            )

    async def _run_ruff(self, context: Context, target: str) -> SkillResult:
        """Run ruff linter."""
        cmd = ["ruff", "check", target]
        if self.fix:
            cmd.append("--fix")

        return await self._run_command(context, cmd, "ruff")

    async def _run_mypy(self, context: Context, target: str) -> SkillResult:
        """Run mypy type checker."""
        cmd = ["mypy", target, "--ignore-missing-imports"]
        return await self._run_command(context, cmd, "mypy")

    async def _run_black(self, context: Context, target: str) -> SkillResult:
        """Run black formatter."""
        cmd = ["black", "--check", target]
        if self.fix:
            cmd = ["black", target]

        return await self._run_command(context, cmd, "black")

    async def _run_all(self, context: Context, target: str) -> SkillResult:
        """Run all linters."""
        all_results = []
        all_errors = []

        for tool in self.tools:
            result = await self.execute(context, tool=tool, target=target)
            all_results.append(f"=== {tool.upper()} ===\n{result.output}")
            if not result.success:
                all_errors.append(result.error)

        combined = "\n\n".join(all_results)
        return SkillResult(
            success=len(all_errors) == 0,
            output=combined,
            error="\n".join(all_errors) if all_errors else None,
            execution_time=time.time() - time.time(),
        )

    async def _run_command(
        self,
        context: Context,
        cmd: List[str],
        tool_name: str,
    ) -> SkillResult:
        """Run a linting command."""
        cwd = context.workspace_path or "."

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            # ruff returns 0 for success, 1 for linting errors, 2 for config errors
            success = process.returncode in (0, 1)

            return SkillResult(
                success=success,
                output=output or "(No issues found)",
                error=error if process.returncode == 2 else None,
                execution_time=time.time() - time.time(),
                metadata={"tool": tool_name, "return_code": process.returncode}
            )

        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"{tool_name} timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            return SkillResult(
                success=False,
                error=f"{tool_name} not installed. Install with: pip install {tool_name}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
            )
