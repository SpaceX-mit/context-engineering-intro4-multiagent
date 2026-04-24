# AI Coder Context Engineering Plan

## 基于OpenAI Codex架构的上下文工程

### 1. 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│              (Flask/Gradio/WebSocket)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Session Manager                           │
│              (Thread-based conversation)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Context Manager                            │
│  - Prompt caching                                           │
│  - Context compaction                                        │
│  - Token counting                                           │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Coordinator    │ │   Skills Hub     │ │   Tool Registry  │
│     Agent        │ │                  │ │                  │
│  - Task routing  │ │ - Shell          │ │ - execute_code  │
│  - Response aggr │ │ - Code Runner    │ │ - search_files  │
│  - Error handle  │ │ - Linter         │ │ - run_tests    │
└──────────────────┘ │ - File Search   │ │ - git_operations│
          │           └──────────────────┘ └──────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   Sub-Agents                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Planner  │→ │  Coder   │→ │ Reviewer │→ │ Tester   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Sandbox Executor                           │
│  - Code execution                                           │
│  - Shell commands                                           │
│  - Resource limits                                          │
└─────────────────────────────────────────────────────────────┘
```

### 2. Context Engineering 策略

#### 2.1 Prompt Structure

```python
SYSTEM_PROMPT = """You are {agent_name}, a {role} in the AI Coder team.

## Team Context
{team_members}

## Current Task
{task_description}

## Skills Available
{available_skills}

## Working Directory Context
{file_tree}

## Recent History
{conversation_history}

## Output Format
Always respond with:
1. What you're doing
2. The result
3. Next steps (if any)
"""
```

#### 2.2 Context Windows

| Window | Size | Purpose |
|--------|------|---------|
| System prompt | ~2000 tokens | Agent identity, skills, rules |
| Working context | ~4000 tokens | Current file contents, task |
| History | ~8000 tokens | Conversation history |
| Reserved | ~2000 tokens | Model reasoning |

#### 2.3 Context Compression

触发条件：
- 超过8000 tokens
- 文件超过100个
- 历史超过20轮

压缩策略：
- 保留关键决策
- 简化中间步骤
- 提取模式而非细节

### 3. Skills System (技能系统)

```python
class Skill(ABC):
    name: str
    description: str
    enabled: bool = True

    @abstractmethod
    async def execute(self, context: Context) -> Result:
        ...

# Built-in Skills
class ShellSkill(Skill):
    """Execute shell commands safely"""
    name = "shell"
    commands_whitelist = ["git", "ls", "cat", "grep", ...]

class CodeRunnerSkill(Skill):
    """Execute Python code in sandbox"""
    name = "code_runner"
    timeout = 30
    memory_limit = "256MB"

class FileSearchSkill(Skill):
    """Search files by pattern"""
    name = "file_search"
    max_results = 50

class LinterSkill(Skill):
    """Run code linters"""
    name = "linter"
    tools = ["ruff", "mypy", "black"]
```

### 4. Multi-Agent Collaboration Protocol

#### 4.1 Message Protocol

```python
class AgentMessage(BaseModel):
    sender: str
    receiver: str | None  # None = broadcast
    type: Literal["request", "response", "error", "status"]
    content: str
    attachments: list[str] = []
    metadata: dict = {}

class TaskRequest(Message):
    task_id: str
    task_type: Literal["plan", "code", "review", "test"]
    requirements: str
    context_files: list[str] = []

class TaskResponse(Message):
    task_id: str
    status: Literal["success", "error", "partial"]
    output: str
    artifacts: list[str] = []
```

#### 4.2 Workflow Patterns

**Sequential Pattern** (Plan → Code → Review → Test):
```python
workflow = SequentialBuilder(
    participants=[planner, coder, reviewer, tester],
    stop_on_error=True,
)
```

**Parallel Pattern** (同时执行多个独立任务):
```python
workflow = ConcurrentBuilder(
    participants=[linter, type_checker, formatter],
    aggregate="all_success",
)
```

**Handoff Pattern** (按条件转交给不同Agent):
```python
workflow = HandoffBuilder(
    initial=coordinator,
    rules=[
        HandoffRule(condition="is_coding", target=coder),
        HandoffRule(condition="needs_review", target=reviewer),
        HandoffRule(condition="needs_test", target=tester),
    ]
)
```

### 5. Sandbox Execution

```python
class SandboxConfig:
    timeout: int = 30  # seconds
    memory_limit: str = "256MB"
    network_enabled: bool = False
    filesystem_scope: str = "workspace"  # Only access workspace

class CodeExecutionResult:
    success: bool
    stdout: str
    stderr: str
    execution_time: float
    memory_used: str

async def execute_in_sandbox(code: str, config: SandboxConfig) -> CodeExecutionResult:
    """Execute code in isolated sandbox"""
    ...
```

### 6. Session Management

```python
class Session:
    id: str
    created_at: datetime
    model: str
    messages: list[Message]
    artifacts: list[Artifact]
    metadata: dict

    def compact(self):
        """Compress context when exceeding limits"""
        ...

    def fork(self) -> "Session":
        """Create branch for experimentation"""
        ...

    def archive(self):
        """Move to inactive storage"""
        ...
```

### 7. Implementation Tasks

#### Phase 1: Core Infrastructure
- [ ] Skill基类和注册系统
- [ ] Context Manager (token计数、压缩)
- [ ] Session Manager (创建、恢复、fork)
- [ ] Basic Sandbox Executor

#### Phase 2: Agent System
- [ ] Coordinator Agent
- [ ] Planner Agent
- [ ] Coder Agent with skills
- [ ] Reviewer Agent
- [ ] Tester Agent

#### Phase 3: Workflow Orchestration
- [ ] Sequential workflow
- [ ] Parallel workflow
- [ ] Handoff workflow
- [ ] Error handling & recovery

#### Phase 4: UI Integration
- [ ] Flask WebUI with streaming
- [ ] Real-time progress
- [ ] Artifact viewer
- [ ] Session management UI

### 8. 文件结构

```
agents/
  __init__.py
  coordinator/
    __init__.py
    agent.py       - Coordinator Agent
    prompts.py     - Coordinator prompts
  planner/
    __init__.py
    agent.py       - Task planning
  coder/
    __init__.py
    agent.py       - Code generation
  reviewer/
    __init__.py
    agent.py       - Code review
  tester/
    __init__.py
    agent.py       - Test generation

skills/
  __init__.py       - Skill registry
  base.py          - BaseSkill class
  shell.py         - Shell execution
  code_runner.py   - Python sandbox
  file_search.py   - File operations
  linter.py        - Code linting

core/
  __init__.py
  context.py        - Context management
  session.py       - Session handling
  sandbox.py       - Sandboxed execution
  workflow.py       - Workflow orchestration
```

### 9. Validation Gates

```bash
# Syntax/Import check
python -m py_compile agents/**/*.py skills/**/*.py core/**/*.py

# Unit tests
pytest tests/ -v --tb=short

# Integration test
pytest tests/integration/ -v

# Lint check
ruff check agents/ skills/ core/ --fix
```
