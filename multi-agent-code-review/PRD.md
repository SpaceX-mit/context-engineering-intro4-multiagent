# Multi-Agent Code Review PRD

## 基于 Codex 架构的多 Agent 开发系统

---

## 一、产品概述

### 1.1 产品定位

构建一个类 Codex Desktop 的多 Agent 协作开发系统，让多个专业 AI Agent 协作完成从需求到可运行代码的完整开发流程。

### 1.2 核心价值

- **多 Agent 协作**: 5+ 专业 Agent 分工明确
- **端到端开发**: 从需求到可运行代码
- **质量保障**: 自动审查、测试、修复
- **可视化流程**: 实时展示 Agent 工作状态

---

## 二、架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        WebUI (Gradio)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Project  │  │  Editor   │  │  Agent   │  │  Chat    │    │
│  │ Explorer │  │  Area    │  │  Panel   │  │  Area    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                      Workflow Orchestrator                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Planner   │  │ Coder    │  │ Linter   │  │Reviewer  │    │
│  │Agent    │  │Agent     │  │Agent     │  │Agent     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Tester   │  │ Fixer    │  │Coordinator│                   │
│  │Agent     │  │Agent     │  │Agent      │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
├─────────────────────────────────────────────────────────────────┤
│                    Context Manager (共享状态)                      │
├─────────────────────────────────────────────────────────────────┤
│                    Tool Executor (沙箱执行)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 类比 Codex |
|------|------|-----------|
| Workflow Orchestrator | 工作流编排 | codex_delegate |
| Context Manager | 上下文传递 | context/ |
| Agent Registry | Agent 管理 | agent/registry.rs |
| Tool Executor | 工具执行 | tools/orchestrator.rs |
| Session Manager | 会话管理 | session/ |

---

## 三、Agent 定义

### 3.1 Agent 类型

| Agent | 角色 | 职责 | Codex 类比 |
|-------|------|------|-----------|
| Coordinator | 协调者 | 需求解析、任务分解、结果聚合 | Main Thread |
| Planner | 规划师 | 制定实现计划、任务拆解 | - |
| Coder | 编码员 | 代码生成、重构 | Sub-Agent (Worker) |
| Linter | 格式化 | 代码风格检查 | - |
| Reviewer | 审查员 | 质量评估、安全扫描 | Sub-Agent (Review) |
| Fixer | 修复师 | 问题修复、代码优化 | - |
| Tester | 测试师 | 测试生成、覆盖率分析 | Sub-Agent (Tester) |

### 3.2 Agent 生命周期

```
PENDING → INIT → RUNNING → (COMPLETED | ERRORED | INTERRUPTED) → CLOSED
```

### 3.3 Agent 状态

```python
class AgentStatus(Enum):
    PENDING = "pending"          # 等待初始化
    INIT = "init"               # 初始化中
    RUNNING = "running"         # 运行中
    WAITING = "waiting"         # 等待其他 Agent
    COMPLETED = "completed"      # 已完成
    ERRORED = "errored"         # 出错
    INTERRUPTED = "interrupted"  # 被中断
    CLOSED = "closed"           # 已关闭
```

---

## 四、Context 传递机制

### 4.1 WorkflowContext 数据结构

```python
@dataclass
class WorkflowContext:
    """工作流上下文 - Agent 之间共享"""

    # 输入
    requirement: str = ""                    # 用户需求
    plan: Optional[str] = None               # Planner 输出的计划
    code: Optional[str] = None               # Coder 生成的代码

    # 审查结果
    lint_issues: List[CodeIssue] = field(default_factory=list)
    review_issues: List[CodeIssue] = field(default_factory=list)

    # 修复
    fixed_code: Optional[str] = None         # 修复后的代码

    # 测试
    tests: Optional[str] = None              # 生成的测试

    # 状态
    current_step: str = "pending"
    iteration: int = 0
    errors: List[str] = field(default_factory=list)

    # Agent 列表
    active_agents: Dict[str, AgentStatus] = field(default_factory=dict)
```

### 4.2 Context 传递流程

```
User Requirement
      │
      ▼
┌─────────────────┐
│   Coordinator    │ ← 接收需求，解析任务
│   (分析 + 分解)  │
└────────┬────────┘
         │ context.requirement
         ▼
┌─────────────────┐
│    Planner      │ ← 从 context 读取需求
│   (制定计划)    │    输出 plan 到 context
└────────┬────────┘
         │ context.plan
         ▼
┌─────────────────┐
│     Coder       │ ← 从 context 读取计划
│   (生成代码)    │    输出 code 到 context
└────────┬────────┘
         │ context.code
         ▼
┌────────┴────────┐
│ Linter │Reviewer│ ← 并行审查
│       │         │    输出 issues 到 context
└────────┬────────┘
         │ context.{lint,review}_issues
         ▼
┌─────────────────┐
│     Fixer       │ ← 从 context 读取问题
│   (修复代码)    │    输出 fixed_code 到 context
└────────┬────────┘
         │ context.fixed_code
         ▼
┌─────────────────┐
│    Tester       │ ← 从 context 读取代码
│   (生成测试)    │    输出 tests 到 context
└────────┬────────┘
         │
         ▼
      完成
```

---

## 五、工作流定义

### 5.1 Development Workflow (完整流程)

```python
WORKFLOW_DEVELOPMENT = {
    "name": "DevelopmentWorkflow",
    "type": "sequential",
    "steps": [
        {"agent": "coordinator", "action": "analyze", "input": "requirement"},
        {"agent": "planner", "action": "plan", "input": "requirement", "output": "plan"},
        {"agent": "coder", "action": "implement", "input": "plan", "output": "code"},
        {"agent": "linter", "action": "lint", "input": "code", "output": "lint_issues"},
        {"agent": "reviewer", "action": "review", "input": "code", "output": "review_issues"},
        {"agent": "fixer", "action": "fix", "input": ["code", "issues"], "output": "fixed_code"},
        {"agent": "tester", "action": "test", "input": "fixed_code", "output": "tests"},
    ]
}
```

### 5.2 Review Workflow (审查流程)

```python
WORKFLOW_REVIEW = {
    "name": "ReviewWorkflow",
    "type": "concurrent",
    "steps": [
        {"agent": "linter", "action": "lint", "input": "code"},
        {"agent": "reviewer", "action": "review", "input": "code"},
        {"agent": "fixer", "action": "fix", "input": "issues"},
    ]
}
```

### 5.3 Iterative Workflow (迭代流程)

```python
WORKFLOW_ITERATIVE = {
    "name": "IterativeWorkflow",
    "type": "iterative",
    "max_iterations": 3,
    "steps": [
        {"agent": "reviewer", "action": "review"},
        {"agent": "fixer", "action": "fix"},
    ],
    "exit_condition": "no_critical_issues"
}
```

---

## 六、Tool 系统

### 6.1 Tool Executor

```python
class ToolExecutor:
    """工具执行器 - 处理工具调用和沙箱"""

    def __init__(self):
        self.orchestrator = ToolOrchestrator()

    async def execute(self, tool: Tool, req: Request) -> Response:
        # 1. 权限检查
        # 2. 选择沙箱策略
        # 3. 执行工具
        # 4. 处理结果或重试
```

### 6.2 内置工具

| 工具 | 功能 | 沙箱要求 |
|------|------|----------|
| execute_python | 执行 Python 代码 | 隔离沙箱 |
| read_file | 读取文件 | 只读 |
| write_file | 写入文件 | 工作区 |
| search_files | 搜索文件 | 只读 |
| run_shell | 执行 Shell | 受限 |

### 6.3 工具执行流程

```
Tool Call Request
      │
      ▼
┌─────────────────┐
│ Permission      │ ← 检查执行策略
│ Check           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sandbox         │ ← 选择沙箱类型
│ Selection       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Tool Execution  │
│                 │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success? │
    └────┬────┘
    Yes  │   No
    ▼         ▼
Return    ┌─────────────────┐
Result    │ Retry with      │
          │ escalated       │
          │ sandbox         │
          └─────────────────┘
```

---

## 七、UI 设计

### 7.1 Codex Desktop 风格布局

```
┌──────────────────────────────────────────────────────────────────┐
│ [Logo] AI Coder         [Project ▼]  [Workflow: Sequential ▼]   │
├────────────┬─────────────────────────────────┬─────────────────┤
│ PROJECT    │         EDITOR AREA              │  AGENT PANEL    │
│ EXPLORER  │                                 │                 │
│           │ ┌───────────────────────────┐  │ ┌─────────────┐ │
│ 📁 src/   │ │ # main.py                 │  │ │Coordinator  │ │
│  📄a.py   │ │                           │  │ │ ✓ Ready     │ │
│  📄b.py   │ │ code...                   │  │ └─────────────┘ │
│ 📁tests/  │ │                           │  │ ┌─────────────┐ │
│  📄t.py    │ └───────────────────────────┘  │ │ Planner     │ │
│           │                                 │ │ ⟳ Running   │ │
│           │ ┌───────────────────────────┐  │ └─────────────┘ │
│           │ │ # output.py              │  │ ┌─────────────┐ │
│           │ └───────────────────────────┘  │ │ Coder       │ │
│           │                                 │ │ ○ Waiting   │ │
├───────────┴─────────────────────────────────┴─┤ └─────────────┘ │
│ TERMINAL / OUTPUT                            │ ┌─────────────┐ │
│ ─────────────────────────────────────────── │ │ Reviewer    │ │
│ [Coordinator] 分析需求中...                  │ │ ○ Waiting   │ │
│ [Planner] 制定计划中...                      │ └─────────────┘ │
│ [Coder] 生成代码中...                       │ ┌─────────────┐ │
│ [Reviewer] 审查中...                        │ │ Tester      │ │
│                                               │ │ ○ Waiting   │ │
└──────────────────────────────────────────────┴─┴─────────────┘─┘
│ Status: Ready  │ Model: gpt-4  │  Memory: 512MB  │  Agents: 7   │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Agent 卡片组件

```html
<div class="agent-card" data-agent="planner">
  <div class="agent-header">
    <div class="agent-name">
      <div class="agent-avatar">📋</div>
      <span>Planner</span>
    </div>
    <span class="agent-status status-running">Running</span>
  </div>
  <div class="agent-progress">
    <div class="agent-progress-bar" style="width: 60%"></div>
  </div>
  <div class="agent-message">分析需求中: 理解项目结构...</div>
</div>
```

### 7.3 协作事件显示

```html
<!-- Agent Spawn -->
<div class="collab-event">
  <span class="event-icon">✦</span>
  <span class="event-text">Spawned: <strong>Robie</strong> [explorer] (gpt-4)</span>
</div>

<!-- Agent Interaction -->
<div class="collab-event">
  <span class="event-icon">→</span>
  <span class="event-text">Sent input to: <strong>Robie</strong></span>
</div>

<!-- Waiting -->
<div class="collab-event">
  <span class="event-icon">⏳</span>
  <span class="event-text">Waiting for: <strong>Robie</strong> [explorer]</span>
</div>

<!-- Completed -->
<div class="collab-event">
  <span class="event-icon">✓</span>
  <span class="event-text">Closed: <strong>Robie</strong> - Completed</span>
</div>
```

---

## 八、API 设计

### 8.1 REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow/execute` | POST | 执行工作流 |
| `/api/workflow/status` | GET | 获取工作流状态 |
| `/api/agents/list` | GET | 列出所有 Agent |
| `/api/agents/{id}/status` | GET | 获取 Agent 状态 |
| `/api/agents/{id}/send` | POST | 向 Agent 发送消息 |
| `/api/context` | GET | 获取当前上下文 |
| `/api/tools/execute` | POST | 执行工具 |

### 8.2 WebSocket Events

```python
# 服务器 -> 客户端事件
class WSEvent(Enum):
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_CLOSED = "agent_closed"
    AGENT_MESSAGE = "agent_message"
    WORKFLOW_PROGRESS = "workflow_progress"
    TOOL_OUTPUT = "tool_output"
    ERROR = "error"

# 客户端 -> 服务器事件
class WSCommand(Enum):
    SUBMIT_REQUIREMENT = "submit_requirement"
    CANCEL_WORKFLOW = "cancel_workflow"
    SEND_TO_AGENT = "send_to_agent"
    EXECUTE_TOOL = "execute_tool"
```

---

## 九、数据模型

### 9.1 核心模型

```python
@dataclass
class Workflow:
    id: str
    name: str
    workflow_type: WorkflowType
    steps: List[WorkflowStep]
    context: WorkflowContext
    status: WorkflowStatus
    created_at: datetime

@dataclass
class WorkflowStep:
    name: str
    agent: str
    action: str
    input_from: List[str]
    output_to: str
    status: StepStatus

@dataclass
class Agent:
    id: str
    name: str
    role: str
    status: AgentStatus
    current_task: Optional[str]
    thread_id: str  # 类似于 Codex 的 ThreadId

@dataclass
class CodeIssue:
    line: Optional[int]
    severity: Severity
    issue_type: IssueType
    message: str
    auto_fixable: bool
    suggestion: Optional[str]
```

---

## 十、实现计划

### Phase 1: 核心框架

| Task | Description | Files |
|------|-------------|-------|
| T1.1 | 定义 Agent 接口和状态机 | `agents/base.py` |
| T1.2 | 实现 AgentRegistry | `core/registry.py` |
| T1.3 | 实现 WorkflowContext | `core/context.py` |
| T1.4 | 实现 Workflow Orchestrator | `core/orchestrator.py` |

### Phase 2: Agent 实现

| Task | Description | Files |
|------|-------------|-------|
| T2.1 | 实现 Coordinator Agent | `agents/coordinator/` |
| T2.2 | 实现 Planner Agent | `agents/planner/` |
| T2.3 | 实现 Coder Agent | `agents/coder/` |
| T2.4 | 实现 Reviewer Agent | `agents/reviewer/` |
| T2.5 | 实现 Linter Agent | `agents/linter/` |
| T2.6 | 实现 Fixer Agent | `agents/fixer/` |
| T2.7 | 实现 Tester Agent | `agents/test_agent/` |

### Phase 3: Context 传递

| Task | Description | Files |
|------|-------------|-------|
| T3.1 | 重写 `_run_*` 方法使用动态 prompt | `agents/orchestrator/workflow.py` |
| T3.2 | 实现 Context 传递验证 | `tests/test_context.py` |
| T3.3 | 端到端流程测试 | `tests/test_e2e.py` |

### Phase 4: UI 实现

| Task | Description | Files |
|------|-------------|-------|
| T4.1 | 重构 codex_ui.py | `webui/codex_ui.py` |
| T4.2 | Agent 状态面板 | `webui/components/` |
| T4.3 | 协作事件显示 | `webui/components/collab_events.py` |
| T4.4 | WebSocket 支持 | `webui/api.py` |

### Phase 5: Tool 系统

| Task | Description | Files |
|------|-------------|-------|
| T5.1 | 实现 ToolExecutor | `tools/executor.py` |
| T5.2 | 实现沙箱隔离 | `tools/sandbox.py` |
| T5.3 | 重试策略 | `tools/retry.py` |

---

## 十一、验收标准

### 11.1 功能验收

- [ ] 多 Agent 协作流程端到端运行
- [ ] Context 在 Agent 之间正确传递
- [ ] 工作流支持顺序/并行/迭代模式
- [ ] Agent 状态实时更新
- [ ] 代码生成→审查→修复→测试完整链路

### 11.2 UI 验收

- [ ] 四面板布局正常显示
- [ ] Agent 卡片状态更新
- [ ] 协作事件可视化
- [ ] Terminal 输出日志

### 11.3 性能验收

- [ ] Agent 响应时间 < 10s
- [ ] 支持 5+ 并发 Agent
- [ ] 界面流畅无卡顿

---

## 十二、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Agent 协作死锁 | 高 | 实现超时和取消机制 |
| Context 膨胀 | 中 | 实施上下文压缩 |
| LLM 调用失败 | 高 | 实现重试和降级策略 |
| 代码执行安全 | 高 | 严格沙箱隔离 |

---

## 十三、附录

### A. Codex 参考实现

- Agent Registry: `codex-rs/core/src/agent/registry.rs`
- Agent Control: `codex-rs/core/src/agent/control.rs`
- Multi Agent UI: `codex-rs/tui/src/multi_agents.rs`
- Tool Orchestrator: `codex-rs/core/src/tools/orchestrator.rs`

### B. 参考文档

- [Codex AGENTS.md](../../codex/AGENTS.md)
- [Skill 系统设计](../../codex/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md)
