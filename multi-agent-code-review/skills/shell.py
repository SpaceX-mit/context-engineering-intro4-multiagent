"""Shell skill - Execute shell commands safely.

Based on OpenAI Codex shell skill.
"""

from __future__ import annotations

import asyncio
import shlex
from typing import List, Optional

from . import Context, Skill, SkillError, SkillResult


# Whitelist of allowed commands (security)
ALLOWED_COMMANDS = {
    "ls", "cat", "grep", "find", "echo", "pwd", "cd",
    "git", "npm", "pip", "uv", "python", "python3",
    "ruff", "mypy", "black", "pytest", "curl", "head",
    "tail", "sort", "uniq", "wc", "mkdir", "cp", "mv", "rm",
}

# Dangerous commands to block
BLOCKED_COMMANDS = {
    "sudo", "chmod", "chown", "rm -rf", "dd", "mkfs",
    ":(){:|:&};:",  # Fork bomb
}


class ShellSkill(Skill):
    """Execute shell commands in a controlled environment.

    Based on Codex shell skill with security restrictions.
    """

    name = "shell"
    description = "Execute shell commands safely"
    timeout = 60

    def __init__(
        self,
        allowed_commands: Optional[List[str]] = None,
        blocked_commands: Optional[List[str]] = None,
        workspace_path: str = ".",
    ):
        super().__init__()
        self.allowed_commands = allowed_commands or list(ALLOWED_COMMANDS)
        self.blocked_commands = blocked_commands or list(BLOCKED_COMMANDS)
        self.workspace_path = workspace_path

    def _is_command_allowed(self, cmd: str) -> bool:
        """Check if command is allowed."""
        # Check blocked patterns
        for blocked in self.blocked_commands:
            if blocked in cmd:
                return False

        # Check if command is in allowed list
        first_word = cmd.split()[0] if cmd.split() else ""
        return first_word in self.allowed_commands

    async def execute(self, context: Context, command: str, **kwargs) -> SkillResult:
        """Execute shell command.

        Args:
            context: Execution context
            command: Shell command to execute

        Returns:
            SkillResult with command output
        """
        start_time = time.time()

        # Security check
        if not self._is_command_allowed(command):
            return SkillResult(
                success=False,
                error=f"Command not allowed: {command}",
                execution_time=time.time() - start_time,
            )

        # Change to workspace directory
        cwd = context.workspace_path or self.workspace_path
        if not os.path.exists(cwd):
            cwd = "."

        try:
            # Use asyncio for non-blocking execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, **context.environment},
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            return SkillResult(
                success=process.returncode == 0,
                output=output,
                error=error if process.returncode != 0 else None,
                execution_time=time.time() - start_time,
                metadata={
                    "return_code": process.returncode,
                    "command": command,
                }
            )

        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Command timed out after {self.timeout}s: {command}",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def execute_batch(
        self,
        context: Context,
        commands: List[str],
    ) -> List[SkillResult]:
        """Execute multiple commands sequentially.

        Args:
            context: Execution context
            commands: List of commands to execute

        Returns:
            List of SkillResults
        """
        results = []
        for cmd in commands:
            result = await self.execute(context, command=cmd)
            results.append(result)
            if not result.success:
                break  # Stop on first error
        return results
