"""Code Runner skill - Execute Python code in sandbox.

Based on OpenAI Codex code interpreter skill.
"""

from __future__ import annotations

import asyncio
import io
import sys
import time
from typing import Dict, List, Optional

from . import Context, Skill, SkillResult


# Restricted builtins for sandbox
RESTRICTED_BUILTINS = {
    # Safe builtins
    "print": print,
    "len": len,
    "range": range,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "type": type,
    "isinstance": isinstance,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "pow": pow,
    "divmod": divmod,
    "any": any,
    "all": all,
    "ord": ord,
    "chr": chr,
    "hex": hex,
    "oct": oct,
    "bin": bin,
    "id": id,
    "hash": hash,
    "format": format,
    "slice": slice,
    "property": property,
    "staticmethod": staticmethod,
    "classmethod": classmethod,
    "super": super,
    "object": object,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "GeneratorExit": GeneratorExit,
    "True": True,
    "False": False,
    "None": None,
}


class CodeRunnerSkill(Skill):
    """Execute Python code in a sandboxed environment.

    Based on Codex code interpreter with security restrictions.
    """

    name = "code_runner"
    description = "Execute Python code safely in sandbox"
    timeout = 30

    def __init__(
        self,
        timeout: int = 30,
        memory_limit_mb: int = 256,
        network_enabled: bool = False,
    ):
        super().__init__()
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.network_enabled = network_enabled

    async def execute(self, context: Context, code: str, **kwargs) -> SkillResult:
        """Execute Python code in sandbox.

        Args:
            context: Execution context
            code: Python code to execute

        Returns:
            SkillResult with execution output
        """
        start_time = time.time()

        # Create restricted namespace
        namespace = {
            "__name__": "__aicoder_sandbox__",
            "__builtins__": RESTRICTED_BUILTINS,
        }

        # Capture stdout
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Redirect stdout/stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Execute in executor to allow timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._execute_code, code, namespace),
                timeout=self.timeout
            )

            output = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()

            return SkillResult(
                success=True,
                output=output or "(No output)",
                error=stderr if stderr else None,
                execution_time=time.time() - start_time,
                metadata={
                    "result": str(result) if result is not None else None,
                }
            )

        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Code execution timed out after {self.timeout}s",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            return SkillResult(
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time,
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _execute_code(self, code: str, namespace: Dict) -> any:
        """Execute code in restricted namespace."""
        exec(code, namespace)
        return namespace.get("_result")


class InteractiveCodeRunner(CodeRunnerSkill):
    """Code runner with state persistence for multi-turn sessions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._global_state: Dict = {
            "__name__": "__aicoder_sandbox__",
            "__builtins__": RESTRICTED_BUILTINS,
        }

    async def execute(self, context: Context, code: str, **kwargs) -> SkillResult:
        """Execute code, maintaining global state."""
        start_time = time.time()

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._execute_with_state,
                    code
                ),
                timeout=self.timeout
            )

            output = stdout_capture.getvalue()

            return SkillResult(
                success=True,
                output=output or "(No output)",
                execution_time=time.time() - start_time,
                metadata={"result": str(result) if result else None}
            )

        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Timeout after {self.timeout}s",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time=time.time() - start_time,
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _execute_with_state(self, code: str) -> any:
        """Execute code preserving global state."""
        exec(code, self._global_state)
        return self._global_state.get("_result")

    def get_state(self) -> Dict:
        """Get current global state."""
        return self._global_state.copy()

    def set_state(self, state: Dict):
        """Restore global state."""
        self._global_state = state
