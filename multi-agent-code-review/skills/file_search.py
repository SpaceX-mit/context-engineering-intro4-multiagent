"""File Search skill - Search and read files.

Based on OpenAI Codex file search skill.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

from . import Context, Skill, SkillResult


# Default file extensions to include
DEFAULT_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg"}

# Extensions to exclude
EXCLUDED_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".dylib", ".class", ".o", ".obj"}

# Directories to exclude
EXCLUDED_DIRS = {".git", ".svn", "__pycache__", "node_modules", "venv", ".venv", "env", ".env", "dist", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


class FileSearchSkill(Skill):
    """Search files by pattern and read file contents.

    Based on Codex file search with filtering.
    """

    name = "file_search"
    description = "Search and read files in workspace"
    timeout = 30

    def __init__(
        self,
        max_results: int = 50,
        max_file_size_kb: int = 1024,
        include_extensions: Optional[List[str]] = None,
    ):
        super().__init__()
        self.max_results = max_results
        self.max_file_size_kb = max_file_size_kb
        self.include_extensions = set(include_extensions) if include_extensions else DEFAULT_EXTENSIONS

    async def execute(self, context: Context, **kwargs) -> SkillResult:
        """Execute file search operation.

        Supported operations:
        - search(pattern): Search for files matching pattern
        - read(filepath): Read file contents
        - list(dirpath): List directory contents
        - tree(dirpath): Show directory tree

        Args:
            context: Execution context
            **kwargs: Operation and parameters

        Returns:
            SkillResult with search results or file contents
        """
        start_time = time.time()
        operation = kwargs.get("operation", "search")
        path = kwargs.get("path", context.workspace_path or ".")

        try:
            if operation == "search":
                return await self._search(context, **kwargs)
            elif operation == "read":
                return await self._read_file(context, **kwargs)
            elif operation == "list":
                return await self._list_directory(context, **kwargs)
            elif operation == "tree":
                return await self._show_tree(context, **kwargs)
            else:
                return SkillResult(
                    success=False,
                    error=f"Unknown operation: {operation}",
                    execution_time=time.time() - start_time,
                )
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time=time.time() - start_time,
            )

    async def _search(self, context: Context, **kwargs) -> SkillResult:
        """Search for files matching pattern."""
        pattern = kwargs.get("pattern", "*")
        path = kwargs.get("path", context.workspace_path or ".")

        if not os.path.exists(path):
            return SkillResult(
                success=False,
                error=f"Path not found: {path}",
            )

        results = []
        regex = self._pattern_to_regex(pattern)

        for root, dirs, files in os.walk(path):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

            for filename in files:
                # Skip hidden files and excluded extensions
                if filename.startswith("."):
                    continue
                ext = Path(filename).suffix
                if ext in EXCLUDED_EXTENSIONS:
                    continue
                if ext and ext not in self.include_extensions and "*" not in pattern:
                    continue

                # Check pattern match
                if regex.match(filename):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, path)
                    results.append(rel_path)

                    if len(results) >= self.max_results:
                        break

            if len(results) >= self.max_results:
                break

        return SkillResult(
            success=True,
            output=f"Found {len(results)} files:\n" + "\n".join(results[:self.max_results]),
            artifacts=results[:self.max_results],
            execution_time=time.time() - start_time,
            metadata={"count": len(results), "pattern": pattern}
        )

    async def _read_file(self, context: Context, **kwargs) -> SkillResult:
        """Read file contents."""
        filepath = kwargs.get("filepath")
        max_lines = kwargs.get("max_lines", 500)

        if not filepath:
            return SkillResult(
                success=False,
                error="No filepath provided",
            )

        # Resolve relative paths
        if not os.path.isabs(filepath):
            base_path = context.workspace_path or "."
            filepath = os.path.join(base_path, filepath)

        if not os.path.exists(filepath):
            return SkillResult(
                success=False,
                error=f"File not found: {filepath}",
            )

        # Check file size
        size_kb = os.path.getsize(filepath) / 1024
        if size_kb > self.max_file_size_kb:
            return SkillResult(
                success=False,
                error=f"File too large: {size_kb:.1f}KB (max {self.max_file_size_kb}KB)",
            )

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip())

                content = "\n".join(lines)
                truncated = i > max_lines

                return SkillResult(
                    success=True,
                    output=content,
                    execution_time=time.time() - start_time,
                    metadata={
                        "filepath": filepath,
                        "lines": i + 1,
                        "truncated": truncated,
                    }
                )
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Error reading file: {str(e)}",
            )

    async def _list_directory(self, context: Context, **kwargs) -> SkillResult:
        """List directory contents."""
        path = kwargs.get("path", context.workspace_path or ".")

        if not os.path.exists(path):
            return SkillResult(
                success=False,
                error=f"Path not found: {path}",
            )

        if not os.path.isdir(path):
            return SkillResult(
                success=False,
                error=f"Not a directory: {path}",
            )

        try:
            entries = []
            for name in sorted(os.listdir(path)):
                if name.startswith("."):
                    continue
                full_path = os.path.join(path, name)
                is_dir = os.path.isdir(full_path)
                entries.append(f"{'[DIR]' if is_dir else '[FILE]'} {name}")

            return SkillResult(
                success=True,
                output="\n".join(entries) or "(empty)",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
            )

    async def _show_tree(self, context: Context, **kwargs) -> SkillResult:
        """Show directory tree."""
        path = kwargs.get("path", context.workspace_path or ".")
        max_depth = kwargs.get("max_depth", 3)

        if not os.path.exists(path):
            return SkillResult(
                success=False,
                error=f"Path not found: {path}",
            )

        lines = []
        for root, dirs, files in os.walk(path):
            # Filter
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

            depth = root[len(path):].count(os.sep)
            if depth > max_depth:
                continue

            indent = "  " * depth
            rel_path = os.path.relpath(root, path)
            lines.append(f"{indent}{'[+]' if rel_path != '.' else ''}{rel_path}/")

            if depth < max_depth:
                for filename in sorted(files):
                    if not filename.startswith("."):
                        ext = Path(filename).suffix
                        if ext not in EXCLUDED_EXTENSIONS:
                            lines.append(f"{indent}  {filename}")

        return SkillResult(
            success=True,
            output="\n".join(lines),
            execution_time=time.time() - start_time,
            metadata={"path": path, "depth": max_depth}
        )

    def _pattern_to_regex(self, pattern: str) -> re.Pattern:
        """Convert glob pattern to regex."""
        # Simple glob to regex conversion
        regex = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
        return re.compile(f"^{regex}$")
