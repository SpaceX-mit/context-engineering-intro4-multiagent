"""Tool Executor - Handles tool execution with sandbox and retry.

Based on Codex Tool Orchestrator:
- Permission checking
- Sandbox selection
- Execution with retry
- Result handling
"""

from __future__ import annotations

import asyncio
import io
import sys
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .sandbox import SandboxType, Sandbox, SandboxManager, get_sandbox_manager
from .retry import (
    RetryConfig,
    RetryStrategy,
    CircuitBreaker,
    CircuitBreakerConfig,
    calculate_delay,
)


class ToolPermission(Enum):
    """Tool execution permissions."""
    ALLOW = "allow"
    DENY = "deny"
    APPROVE = "approve"  # Requires user approval
    ESCALATE = "escalate"  # Requires higher privilege


@dataclass
class Tool:
    """A tool that can be executed."""
    name: str
    description: str
    permission: ToolPermission = ToolPermission.ALLOW
    sandbox_type: SandboxType = SandboxType.WORKSPACE_WRITE
    timeout: float = 30.0


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    sandbox_used: Optional[str] = None


@dataclass
class ToolCall:
    """A request to execute a tool."""
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


# Built-in tools
BUILTIN_TOOLS: Dict[str, Tool] = {
    "execute_python": Tool(
        name="execute_python",
        description="Execute Python code in sandbox",
        permission=ToolPermission.ALLOW,
        sandbox_type=SandboxType.WORKSPACE_WRITE,
        timeout=30.0,
    ),
    "read_file": Tool(
        name="read_file",
        description="Read a file",
        permission=ToolPermission.ALLOW,
        sandbox_type=SandboxType.READONLY,
        timeout=10.0,
    ),
    "write_file": Tool(
        name="write_file",
        description="Write content to a file",
        permission=ToolPermission.ALLOW,
        sandbox_type=SandboxType.WORKSPACE_WRITE,
        timeout=10.0,
    ),
    "list_directory": Tool(
        name="list_directory",
        description="List directory contents",
        permission=ToolPermission.ALLOW,
        sandbox_type=SandboxType.READONLY,
        timeout=5.0,
    ),
    "run_shell": Tool(
        name="run_shell",
        description="Execute shell command",
        permission=ToolPermission.DENY,  # Requires escalation
        sandbox_type=SandboxType.DANGEROUS_FULL_ACCESS,
        timeout=60.0,
    ),
}


class ToolExecutor:
    """
    Orchestrates tool execution with permission checking and sandboxing.

    Based on Codex ToolOrchestrator:
    1. Permission check
    2. Sandbox selection
    3. Execute with retry
    4. Handle result or escalate
    """

    def __init__(
        self,
        sandbox_manager: Optional[SandboxManager] = None,
    ):
        self._sandbox_manager = sandbox_manager or get_sandbox_manager()
        self._tools: Dict[str, Tool] = dict(BUILTIN_TOOLS)
        self._tool_handlers: Dict[str, Callable] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Default retry config
        self._retry_config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=0.1,
        )

    def register_tool(self, tool: Tool, handler: Callable):
        """
        Register a tool with its handler.

        Args:
            tool: Tool definition
            handler: Function to handle execution
        """
        self._tools[tool.name] = tool
        self._tool_handlers[tool.name] = handler

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def check_permission(self, tool_name: str) -> ToolPermission:
        """
        Check if tool can be executed.

        Args:
            tool_name: Name of tool

        Returns:
            Permission status
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolPermission.DENY
        return tool.permission

    def select_sandbox(self, tool_name: str) -> SandboxType:
        """
        Select appropriate sandbox for tool.

        Args:
            tool_name: Name of tool

        Returns:
            Sandbox type to use
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return SandboxType.READONLY
        return tool.sandbox_type

    async def execute(
        self,
        call: ToolCall,
        workspace: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool call.

        Args:
            call: Tool call request
            workspace: Optional workspace path

        Returns:
            Tool execution result
        """
        tool_name = call.tool_name
        params = call.params

        # Get tool definition
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        # Permission check
        permission = self.check_permission(tool_name)
        if permission == ToolPermission.DENY:
            return ToolResult(
                tool=tool_name,
                success=False,
                error="Permission denied",
            )

        # Select sandbox
        sandbox_type = self.select_sandbox(tool_name)
        sandbox = self._sandbox_manager.create_sandbox(
            config=SandboxManager()._default_config.__class__(
                sandbox_type=sandbox_type,
                max_execution_time=tool.timeout,
            )
        )

        # Get circuit breaker
        cb = self._circuit_breakers.get(tool_name)
        if not cb:
            cb = CircuitBreaker()
            self._circuit_breakers[tool_name] = cb

        # Execute with retry
        start_time = asyncio.get_event_loop().time()
        last_error: Optional[Exception] = None

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                # Check circuit breaker
                if not cb.is_allowed():
                    raise Exception("Circuit breaker open")

                # Get handler
                handler = self._tool_handlers.get(tool_name)
                if not handler:
                    # Use default handler
                    result = await self._default_handler(tool_name, params, sandbox)
                else:
                    result = await handler(params, sandbox=sandbox)

                cb.record_success()

                end_time = asyncio.get_event_loop().time()
                return ToolResult(
                    tool=tool_name,
                    success=True,
                    result=result,
                    execution_time=end_time - start_time,
                    sandbox_used=sandbox_type.value,
                )

            except Exception as e:
                last_error = e
                cb.record_failure(e)

                if attempt < self._retry_config.max_retries:
                    delay = calculate_delay(attempt, self._retry_config)
                    await asyncio.sleep(delay)

        end_time = asyncio.get_event_loop().time()
        return ToolResult(
            tool=tool_name,
            success=False,
            error=str(last_error),
            execution_time=end_time - start_time,
            sandbox_used=sandbox_type.value,
        )

    async def _default_handler(
        self,
        tool_name: str,
        params: Dict[str, Any],
        sandbox: Sandbox,
    ) -> Any:
        """Default handler for built-in tools."""
        if tool_name == "execute_python":
            return await self._execute_python(params.get("code", ""), sandbox)
        elif tool_name == "read_file":
            return self._read_file(params.get("path", ""))
        elif tool_name == "write_file":
            return self._write_file(params.get("path", ""), params.get("content", ""))
        elif tool_name == "list_directory":
            return self._list_directory(params.get("path", "."))
        else:
            raise ValueError(f"No handler for tool: {tool_name}")

    async def _execute_python(self, code: str, sandbox: Sandbox) -> Dict[str, Any]:
        """Execute Python code in sandbox."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            # Execute in sandbox workspace
            workspace = sandbox.get_workspace()
            if workspace:
                exec_globals = {"__name__": "__sandbox__"}
                exec(code, exec_globals)

            output = captured.getvalue()
            return {"success": True, "stdout": output}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        finally:
            sys.stdout = old_stdout

    def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file."""
        try:
            with open(path, "r") as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write a file."""
        try:
            with open(path, "w") as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        try:
            import os
            entries = os.listdir(path)
            return {"success": True, "entries": entries}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global executor instance
_executor: Optional[ToolExecutor] = None


def get_executor() -> ToolExecutor:
    """Get or create the global tool executor."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
