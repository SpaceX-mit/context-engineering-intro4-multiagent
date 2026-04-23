# PRP: 多Agent协同开发系统 - 代码正确性与质量审查

## Purpose
构建基于 Microsoft Agent Framework 的多Agent协同开发系统，实现代码正确性和质量审查的自动化。系统包含5个专业Agent协同工作，通过迭代改进循环提升代码质量。

## Core Principles
1. **Context is King**: 包含所有必要的文档、示例和注意事项
2. **Validation Loops**: 提供AI可执行测试/检查的验证循环
3. **Information Dense**: 使用代码库中的关键词和模式
4. **Progressive Success**: 从简单开始，验证，然后增强

---

## Goal
创建一个生产级的多Agent代码审查系统，包含：
- **代码正确性检查**: AST分析、语法检查、未使用变量检测
- **代码质量审查**: 复杂度、安全性、可维护性评分
- **测试覆盖分析**: 覆盖率检测、边界条件识别
- **自动修复**: 根据审查结果迭代修复问题
- **多Agent协作**: 5个专业Agent协同工作

## Why
- **业务价值**: 自动化代码审查流程，减少人工审查工作量
- **一致性**: 确保代码质量标准统一执行
- **效率**: 并行多维度审查，加速代码改进周期
- **可扩展性**: 易于添加新的审查规则和Agent类型

## What
CLI驱动的代码审查工具：
- 用户输入待审查的代码路径
- Coordinator解析并分配任务给专业Agent
- 专业Agent并行/串行执行审查
- Fixer Agent自动修复可修复问题
- 生成统一格式的审查报告

### Success Criteria
- [ ] Coordinator成功协调多个专业Agent
- [ ] Linter Agent检测代码规范问题 (未使用变量、导入、风格)
- [ ] Review Agent评估代码质量和安全性
- [ ] Test Agent分析测试覆盖率
- [ ] Fixer Agent自动修复可修复问题
- [ ] 迭代改进循环正常运作 (Review → Fix → Review)
- [ ] 输出符合规范的JSON格式报告
- [ ] 所有测试通过，代码符合质量标准

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

- url: https://github.com/SpaceX-mit/agent-framework
  why: Multi-agent orchestration patterns, SequentialBuilder, ConcurrentBuilder

- file: examples/agent-framework/python/samples/autogen-migration/orchestrations/01_round_robin_group_chat.py
  why: SequentialBuilder pattern for linear workflow (Linter → Review → Fix)
  critical: 展示了SequentialBuilder和WorkflowBuilder with cycles的使用方式

- file: examples/agent-framework/python/samples/autogen-migration/orchestrations/04_magentic_one.py
  why: MagenticBuilder pattern for coordinator-based multi-agent system
  critical: Manager agent协调多个专业agent的完整示例

- file: examples/agent-framework/python/samples/03-workflows/orchestrations/concurrent_agents.py
  why: ConcurrentBuilder pattern for parallel multi-agent execution
  critical: 并行审查多个维度的工作流示例

- file: examples/agent-framework/python/samples/03-workflows/control-flow/simple_loop.py
  why: WorkflowBuilder with loop for iterative improvement (Review → Fix → Review)
  critical: Agent作为judge的循环模式，用于质量验证

- file: use-cases/agent-factory-with-subagents/agents/rag_agent/
  why: Agent模块结构模式 (agent.py, tools.py, prompts.py, providers.py)
  critical: 每个agent的标准化文件组织

- file: examples/agent-framework/python/samples/autogen-migration/orchestrations/02_selector_group_chat.py
  why: GroupChatBuilder pattern for multi-expert discussion
  critical: 多个expert agent讨论并达成共识的模式

- url: https://docs.python.org/3/library/ast.html
  why: AST module for code analysis
  section: AST node types and visitor pattern

- url: https://docs.astral.sh/ruff/
  why: Ruff for fast Python linting
  section: Rule categories and configuration

- url: https://bandit.readthedocs.io/
  why: Bandit for security issue detection
  section: Built-in test plugins
```

### Current Codebase tree
```bash
context-engineering-intro/
├── CLAUDE.md                 # Global rules for AI assistant
├── INITIAL.md               # Feature request
├── PLANNING.md              # Project architecture plan
├── TASK.md                  # Task tracking
├── examples/
│   └── agent-framework/     # Microsoft Agent Framework reference
│       └── python/
│           ├── packages/    # Core framework packages
│           └── samples/     # Sample implementations
│               ├── autogen-migration/  # Migration examples
│               │   ├── orchestrations/ # Multi-agent patterns
│               │   └── single_agent/  # Single agent patterns
│               └── 03-workflows/      # Workflow examples
├── use-cases/
│   ├── agent-factory-with-subagents/  # Agent factory patterns
│   └── build-with-agent-team/          # Multi-agent team patterns
└── PRPs/
    └── templates/
        └── prp_base.md      # PRP template
```

### Desired Codebase tree with files to be added
```bash
multi-agent-code-review/
├── __init__.py                      # Package init
├── agents/                          # Agent modules
│   ├── __init__.py
│   ├── coordinator/
│   │   ├── __init__.py
│   │   ├── agent.py               # Coordinator agent definition
│   │   ├── tools.py               # Coordination tools
│   │   └── prompts.py             # Coordinator prompts
│   ├── linter/
│   │   ├── __init__.py
│   │   ├── agent.py               # Linter agent
│   │   ├── tools.py               # AST analysis, style check
│   │   └── prompts.py
│   ├── reviewer/
│   │   ├── __init__.py
│   │   ├── agent.py               # Review agent
│   │   ├── tools.py               # Quality analysis tools
│   │   └── prompts.py
│   ├── test_agent/
│   │   ├── __init__.py
│   │   ├── agent.py               # Test coverage agent
│   │   ├── tools.py               # Coverage analysis
│   │   └── prompts.py
│   └── fixer/
│       ├── __init__.py
│       ├── agent.py               # Auto-fix agent
│       ├── tools.py               # Code modification tools
│       └── prompts.py
├── core/                           # Core modules
│   ├── __init__.py
│   ├── models.py                  # Pydantic models for data validation
│   ├── config.py                  # Configuration management
│   └── workflow.py                # Workflow orchestration
├── tools/                          # Analysis tools
│   ├── __init__.py
│   ├── ast_analyzer.py            # AST-based code analysis
│   ├── linter_tools.py            # Ruff integration
│   ├── security_scanner.py        # Bandit integration
│   └── coverage_analyzer.py       # Coverage.py integration
├── providers.py                    # LLM provider configuration
├── cli.py                          # CLI interface
├── main.py                         # Main entry point
├── settings.py                     # Settings with pydantic-settings
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── README.md                       # Documentation
└── tests/                          # Test suite
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── test_coordinator.py         # Coordinator tests
    ├── test_linter.py              # Linter tests
    ├── test_reviewer.py            # Reviewer tests
    ├── test_fix_agent.py           # Fixer tests
    ├── test_workflow.py            # Workflow tests
    └── test_cli.py                 # CLI tests
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: agent-framework requires async throughout - no sync functions in async context
# CRITICAL: Agent creation requires client parameter - see examples/agent-framework/python/samples/
# CRITICAL: WorkflowBuilder requires start_executor parameter - cannot be None
# CRITICAL: Use agent.as_tool() for Agent-as-Tool pattern
# CRITICAL: MagenticBuilder requires manager_agent with specific instructions
# CRITICAL: SequentialBuilder/ConcurrentBuilder participants must be Agents
# CRITICAL: Executor handlers must use correct type hints for WorkflowContext

# CRITICAL: ruff/mypy require proper project configuration
# CRITICAL: Bandit requires proper rule configuration to avoid false positives
# CRITICAL: AST analysis must handle syntax errors gracefully

# CRITICAL: File operations require proper encoding handling
# CRITICAL: Code modification must preserve original formatting when possible
```

## Implementation Blueprint

### Data models and structure

```python
# core/models.py - Core data structures for code review

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum
from datetime import datetime

class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class IssueType(Enum):
    """Type of code issue."""
    LINT = "lint"           # Style/formatting
    CORRECTNESS = "correctness"  # Logic errors
    SECURITY = "security"   # Vulnerability
    COMPLEXITY = "complexity"   # Maintainability
    TEST = "test"          # Test coverage

class CodeIssue(BaseModel):
    """Single code issue."""
    file: str = Field(..., description="File path")
    line: Optional[int] = Field(None, description="Line number")
    column: Optional[int] = Field(None, description="Column number")
    severity: Severity
    issue_type: IssueType
    message: str = Field(..., description="Issue description")
    suggestion: Optional[str] = Field(None, description="Fix suggestion")
    auto_fixable: bool = Field(False, description="Can be auto-fixed")
    rule_id: Optional[str] = Field(None, description="Rule identifier")

class ReviewResult(BaseModel):
    """Result from a single agent."""
    agent: str = Field(..., description="Agent name")
    issues: List[CodeIssue] = Field(default_factory=list)
    summary: str = Field("", description="Brief summary")
    status: Literal["success", "error", "pending"] = "pending"

class ReviewReport(BaseModel):
    """Final review report."""
    timestamp: datetime = Field(default_factory=datetime.now)
    files_reviewed: int = Field(0, ge=0)
    summary: dict = Field(
        default_factory=lambda: {
            "total_issues": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "auto_fixed": 0,
        }
    )
    details: List[CodeIssue] = Field(default_factory=list)
    agents_used: List[str] = Field(default_factory=list)

class ReviewRequest(BaseModel):
    """User review request."""
    paths: List[str] = Field(..., description="Paths to review")
    include_security: bool = Field(True)
    include_complexity: bool = Field(True)
    auto_fix: bool = Field(True)
    max_iterations: int = Field(3, ge=1, le=10)
```

### List of tasks to be completed

```yaml
Task 1: Setup Project Structure and Configuration
CREATE multi-agent-code-review/ directory structure
CREATE core/models.py with Pydantic models (CodeIssue, ReviewResult, ReviewReport)
CREATE settings.py with pydantic-settings (follow use-cases/agent-factory-with-subagents pattern)
CREATE providers.py with OpenAI/Anthropic LLM client setup
CREATE .env.example with required environment variables

Task 2: Implement Core Analysis Tools
CREATE tools/ast_analyzer.py:
  - PATTERN: Use Python ast module with ASTVisitor
  - Detect: unused imports, unused variables, type annotation issues
  - Handle syntax errors gracefully

CREATE tools/linter_tools.py:
  - PATTERN: Use ruff as the primary linter (fast, Rust-based)
  - Wrap ruff API for programmatic use
  - Parse ruff output into CodeIssue models

CREATE tools/security_scanner.py:
  - PATTERN: Use bandit for security scanning
  - Map bandit results to CodeIssue with SECURITY severity
  - Filter false positives with configurable rules

CREATE tools/coverage_analyzer.py:
  - PATTERN: Use coverage.py for test coverage
  - Generate missing test suggestions
  - Identify uncovered edge cases

Task 3: Implement Linter Agent
CREATE agents/linter/agent.py:
  - PATTERN: Follow examples/agent-framework/python/samples/ pattern
  - Use Agent from agent_framework
  - Register ast_analyzer and linter_tools as tools

CREATE agents/linter/tools.py:
  - Implement lint_file() tool
  - Implement check_style() tool
  - Return ReviewResult with CodeIssue list

CREATE agents/linter/prompts.py:
  - SYSTEM_PROMPT: "You are a code linting expert..."
  - Focus on style, formatting, unused variables

Task 4: Implement Review Agent
CREATE agents/reviewer/agent.py:
  - PATTERN: Follow examples/agent-framework/python/samples/ pattern
  - Use Agent with security_scanner and complexity analysis

CREATE agents/reviewer/tools.py:
  - Implement analyze_complexity() tool
  - Implement detect_security_issues() tool
  - Implement assess_maintainability() tool

CREATE agents/reviewer/prompts.py:
  - SYSTEM_PROMPT: "You are a code quality reviewer..."
  - Focus on security, maintainability, performance

Task 5: Implement Test Agent
CREATE agents/test_agent/agent.py:
  - PATTERN: Follow examples/agent-framework pattern
  - Use coverage_analyzer for test coverage analysis

CREATE agents/test_agent/tools.py:
  - Implement analyze_coverage() tool
  - Implement suggest_tests() tool
  - Return missing test suggestions

CREATE agents/test_agent/prompts.py:
  - SYSTEM_PROMPT: "You are a test coverage analyst..."

Task 6: Implement Fixer Agent
CREATE agents/fixer/agent.py:
  - PATTERN: Use WorkflowBuilder for iteration
  - Implement auto_fix() tool for common issues

CREATE agents/fixer/tools.py:
  - Implement fix_style_issues() tool
  - Implement fix_imports() tool
  - Implement verify_fix() tool

CREATE agents/fixer/prompts.py:
  - SYSTEM_PROMPT: "You are an automatic code fixer..."

Task 7: Implement Coordinator Agent
CREATE agents/coordinator/agent.py:
  - PATTERN: Use MagenticBuilder (see examples/agent-framework/python/samples/autogen-migration/orchestrations/04_magentic_one.py)
  - Create manager_agent as the coordinator
  - Register all specialist agents

CREATE agents/coordinator/tools.py:
  - Implement orchestrate_review() tool
  - Implement aggregate_results() tool
  - Implement generate_report() tool

CREATE agents/coordinator/prompts.py:
  - SYSTEM_PROMPT: "You are a code review coordinator..."
  - Instructions for task assignment and result aggregation

Task 8: Implement Workflow Orchestration
CREATE core/workflow.py:
  - PATTERN: Use WorkflowBuilder (see examples/agent-framework/python/samples/03-workflows/control-flow/simple_loop.py)
  - Implement sequential_review_workflow() for Linter → Review → Fix
  - Implement concurrent_review_workflow() for parallel analysis
  - Implement iterative_improvement_workflow() for Review → Fix → Review loop

Task 9: Implement CLI Interface
CREATE cli.py:
  - PATTERN: Follow use-cases/agent-factory-with-subagents/cli.py pattern
  - Implement review command
  - Support path input and options
  - Format and display results

Task 10: Add Comprehensive Tests
CREATE tests/ directory with:
  - conftest.py with fixtures
  - test_coordinator.py
  - test_linter.py
  - test_reviewer.py
  - test_fix_agent.py
  - test_workflow.py
  - test_cli.py

Task 11: Create Documentation
CREATE README.md with:
  - Installation instructions
  - Usage examples
  - Architecture diagram
  - Configuration options
```

### Per task pseudocode

```python
# Task 2: AST Analyzer
# Pattern from Python stdlib docs
import ast

def analyze_python_file(file_path: str) -> List[CodeIssue]:
    issues = []
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read(), filename=file_path)
        
        visitor = UnusedImportVisitor()
        visitor.visit(tree)
        issues.extend(visitor.issues)
        
        # Check for other patterns...
    except SyntaxError as e:
        issues.append(CodeIssue(
            file=file_path,
            line=e.lineno,
            severity=Severity.CRITICAL,
            issue_type=IssueType.CORRECTNESS,
            message=f"Syntax error: {e.msg}",
            rule_id="E999"
        ))
    return issues

class UnusedImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.used_names = set()
        self.imports = []
        self.issues = []
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append((alias.name, node.lineno))
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
    
    def visit_FunctionDef(self, node):
        self.used_names.add(node.name)
        self.generic_visit(node)

# Task 7: Coordinator with MagenticBuilder
# Pattern from 04_magentic_one.py
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import MagenticBuilder

client = OpenAIChatClient(model="gpt-4")

# Create specialist agents
linter_agent = Agent(
    client=client,
    name="linter",
    instructions="You detect code style and formatting issues.",
)

reviewer_agent = Agent(
    client=client,
    name="reviewer", 
    instructions="You evaluate code quality and security.",
)

test_agent = Agent(
    client=client,
    name="test_coverage",
    instructions="You analyze test coverage and suggest improvements.",
)

fixer_agent = Agent(
    client=client,
    name="fixer",
    instructions="You automatically fix code issues.",
)

# Create manager agent (coordinator)
manager = Agent(
    client=client,
    name="coordinator",
    instructions="You coordinate the team to complete code review tasks efficiently.",
)

# Build Magentic workflow
workflow = MagenticBuilder(
    participants=[linter_agent, reviewer_agent, test_agent, fixer_agent],
    manager_agent=manager,
    max_round_count=20,
    max_stall_count=3,
    max_reset_count=1,
).build()

# Task 8: Workflow with iteration loop
# Pattern from simple_loop.py
from agent_framework import (
    WorkflowBuilder,
    WorkflowContext,
    AgentExecutor,
    handler,
    Executor,
)

class CheckQuality(Executor):
    @handler
    async def check(self, issues: List[CodeIssue], ctx: WorkflowContext[bool]) -> None:
        # Judge if issues are fixed
        if len(issues) == 0:
            await ctx.yield_output("Review completed - all issues fixed!")
        else:
            # Continue to fixer
            await ctx.send_message(issues)

# Build workflow with loop
workflow = (
    WorkflowBuilder(start_executor=review_agent)
    .add_edge(review_agent, fixer_agent)
    .add_edge(fixer_agent, check_quality)
    .add_edge(check_quality, review_agent)  # Loop back
    .build()
)
```

### Integration Points
```yaml
ENVIRONMENT:
  - add to: .env
  - vars: |
      # LLM Configuration
      LLM_PROVIDER=openai
      LLM_API_KEY=sk-...
      LLM_MODEL=gpt-4
      
      # Analysis Tools
      RUFF_CONFIG=.ruff.toml
      BANDIT_CONFIG=bandit.yaml

DEPENDENCIES:
  - Update requirements.txt with:
    - agent-framework (from examples/agent-framework/python/)
    - ruff>=0.1
    - bandit>=1.7
    - coverage>=7.0
    - pydantic>=2.0
    - pydantic-settings>=2.0
    - python-dotenv>=1.0

CONFIG:
  - Project root for ruff/mypy: pyproject.toml
  - Rules configuration: .ruff.toml, mypy.ini

PACKAGE:
  - Add agent-framework from local path for development
  - Use pip install -e for editable install
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check multi-agent-code-review/ --fix
mypy multi-agent-code-review/

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# test_linter.py
def test_ast_analyzer_detects_unused_import():
    """Test AST analyzer finds unused imports."""
    code = """
import os
import sys

def hello():
    return "hello"
"""
    issues = analyze_python_code(code)
    assert any("os" in i.message and i.issue_type == IssueType.LINT for i in issues)

def test_ast_analyzer_handles_syntax_error():
    """Test AST analyzer handles syntax errors gracefully."""
    code = "def broken(()"
    issues = analyze_python_code(code)
    assert len(issues) == 1
    assert issues[0].severity == Severity.CRITICAL

# test_coordinator.py
async def test_coordinator_creates_workflow():
    """Test coordinator creates Magentic workflow."""
    coordinator = create_coordinator()
    assert coordinator.workflow is not None
    assert len(coordinator.participants) >= 4

# test_workflow.py
async def test_sequential_review_workflow():
    """Test sequential review produces results."""
    workflow = create_sequential_workflow()
    result = await workflow.run("test_file.py")
    assert result is not None
```

```bash
# Run tests iteratively until passing:
python -m pytest tests/ -v --cov=multi_agent_code_review

# If failing: Debug specific test, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test CLI with sample Python file
python -m multi_agent_code_review.cli review tests/sample_code.py

# Expected output:
# {
#   "summary": {
#     "total_issues": 5,
#     "critical": 1,
#     "high": 2,
#     "medium": 2,
#     "low": 0,
#     "auto_fixed": 3
#   },
#   "details": [...]
# }

# Test with auto-fix enabled
python -m multi_agent_code_review.cli review tests/sample_code.py --auto-fix

# Check fixed file
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `ruff check multi-agent-code-review/`
- [ ] No type errors: `mypy multi-agent-code-review/`
- [ ] CLI works correctly: `python -m multi_agent_code_review.cli --help`
- [ ] Coordinator orchestrates agents successfully
- [ ] Linter detects code issues correctly
- [ ] Reviewer evaluates quality and security
- [ ] Fixer auto-fixes appropriate issues
- [ ] Workflow iterations work (Review → Fix → Review)
- [ ] Integration test passes with sample code
- [ ] README includes clear setup instructions

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode API keys - use environment variables
- ❌ Don't use sync functions in async agent context
- ❌ Don't skip error handling for AST parsing
- ❌ Don't forget to handle syntax errors gracefully
- ❌ Don't create monolithic files - split into modules
- ❌ Don't skip test coverage - target 80%+
- ❌ Don't hardcode paths - use configuration

## Confidence Score: 8/10

High confidence due to:
- Clear reference patterns from agent-framework samples
- Established project structure from use-cases
- Comprehensive validation gates
- Well-defined agent collaboration patterns

Minor uncertainty on:
- agent-framework local package installation path
- Complex workflow edge cases in iteration loops

---

## Implementation Notes

### Agent Framework Compatibility
The examples/agent-framework directory contains Microsoft's agent-framework. 
For development, install from local path:
```bash
cd examples/agent-framework/python
pip install -e packages/core
pip install -e packages/openai  # or your preferred provider
pip install -e packages/orchestrations
```

### Fallback Approach
If agent-framework has compatibility issues, implement using:
1. Direct LLM API calls with structured prompts
2. Custom workflow orchestration matching the patterns
3. Preserve the same agent collaboration patterns

### Key Files Reference
- SequentialBuilder: `examples/agent-framework/python/samples/autogen-migration/orchestrations/01_round_robin_group_chat.py` (line 90)
- MagenticBuilder: `examples/agent-framework/python/samples/autogen-migration/orchestrations/04_magentic_one.py` (line 104)
- WorkflowBuilder with loop: `examples/agent-framework/python/samples/03-workflows/control-flow/simple_loop.py` (line 146)
- ConcurrentBuilder: `examples/agent-framework/python/samples/03-workflows/orchestrations/concurrent_agents.py` (line 74)