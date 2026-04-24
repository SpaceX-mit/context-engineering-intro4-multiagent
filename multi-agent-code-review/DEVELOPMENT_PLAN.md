# Development Plan - Multi-Agent Code Development System

基于 CODEX_ANALYSIS.md 和 PRD.md 的完整开发计划。

## 一、当前状态

### 已实现
- ✅ 7 个 Agent 模块 (Coordinator, Planner, Coder, Reviewer, Linter, Fixer, Tester)
- ✅ 工作流编排 (Sequential/Concurrent/Iterative)
- ✅ Codex Desktop 风格 UI (Agent Pipeline + Status Cards)
- ✅ Skills 系统 (code_runner, shell, file_search, linter)
- ✅ Context Manager 和 Session Manager
- ✅ 代码执行沙箱

### 待实现 (根据 PRD.md Phase)

| Phase | 内容 | 优先级 |
|-------|------|--------|
| **Phase 1** | 核心框架完善 | P0 |
| **Phase 2** | Agent 实现 | P0 |
| **Phase 3** | Context 传递 | P1 |
| **Phase 4** | UI 实现 | P1 |
| **Phase 5** | Tool 系统 | P2 |

---

## 二、详细实施计划

### Phase 1: 核心框架完善

#### T1.1 Agent Registry (Agent管理)
```
目标: 管理所有活跃 Agent，维护 Agent 树结构
文件: core/registry.py (新建)

功能:
- register_agent(agent_id, agent_info)
- unregister_agent(agent_id)
- get_agent(agent_id) -> Agent
- list_agents() -> List[AgentMetadata]
- get_agent_tree() -> Dict (层级结构)

数据结构:
AgentMetadata:
  - agent_id: str
  - nickname: str
  - role: str
  - status: AgentStatus
  - parent_id: Optional[str] (父Agent)
  - spawned_at: float
```

#### T1.2 WorkflowContext 增强
```
目标: 实现 PRD 中的 WorkflowContext 数据结构
文件: core/context.py (增强)

需要添加字段:
- requirement: str
- plan: Optional[str]
- code: Optional[str]
- lint_issues: List[CodeIssue]
- review_issues: List[CodeIssue]
- fixed_code: Optional[str]
- tests: Optional[str]
- active_agents: Dict[str, AgentStatus]
- iteration: int
```

#### T1.3 Workflow Orchestrator 重构
```
目标: 实现 PRD 中的完整工作流编排器
文件: core/orchestrator.py (新建)

功能:
- register_workflow(workflow_def)
- execute_workflow(workflow_id, context) -> WorkflowResult
- pause_workflow(workflow_id)
- resume_workflow(workflow_id)
- cancel_workflow(workflow_id)
- get_workflow_status(workflow_id) -> WorkflowStatus

支持:
- 顺序执行 (Sequential)
- 并行执行 (Concurrent)
- 迭代执行 (Iterative with max_iterations)
```

---

### Phase 2: Agent 实现完善

#### T2.1 Agent 生命周期状态机
```
文件: agents/base.py (增强)

AgentStatus:
  PENDING -> INIT -> RUNNING -> (COMPLETED | ERRORED | INTERRUPTED) -> CLOSED

需要实现:
- _transition_to(new_status)
- _on_enter_status(status)
- _on_exit_status(status)
- timeout_handler
- cancel_handler
```

#### T2.2 每个 Agent 的完整实现

**Coordinator Agent** (`agents/coordinator/`)
```
职责:
- 接收用户需求
- 解析并分解任务
- 分配给其他 Agent
- 聚合结果

需要实现:
- analyze_requirement(requirement) -> TaskList
- decompose_tasks(tasks) -> Dict[str, AgentTask]
- delegate_task(task, agent)
- aggregate_results(results) -> FinalResult
```

**Planner Agent** (`agents/planner/`)
```
职责:
- 分析需求
- 制定实施计划
- 输出文件列表和步骤

需要实现:
- create_plan(requirement) -> Plan
- break_down_step(step) -> SubSteps
- estimate_effort(step) -> EffortEstimate
```

**Coder Agent** (`agents/coder/`)
```
职责:
- 根据计划生成代码
- 实现功能

需要实现:
- implement(plan) -> Code
- write_to_file(filepath, code)
- execute_code(code) -> ExecutionResult
```

**Reviewer Agent** (`agents/reviewer/`)
```
职责:
- 代码质量评估
- 逻辑检查
- 安全扫描

需要实现:
- review(code) -> ReviewReport
- check_logic(code) -> List[Issue]
- check_security(code) -> List[Issue]
```

**Linter Agent** (`agents/linter/`)
```
职责:
- 代码风格检查
- PEP8 规范

需要实现:
- lint(code) -> List[StyleIssue]
- format_code(code) -> FormattedCode
```

**Fixer Agent** (`agents/fixer/`)
```
职责:
- 自动修复问题
- 应用修复建议

需要实现:
- fix(code, issues) -> FixedCode
- apply_suggestion(code, suggestion) -> Code
```

**Tester Agent** (`agents/test_agent/`)
```
职责:
- 生成测试用例
- 覆盖率分析

需要实现:
- generate_tests(code) -> TestCode
- run_tests(tests, code) -> TestResult
```

---

### Phase 3: Context 传递机制

#### T3.1 Context 传递验证
```
目标: 确保 Context 在 Agent 间正确传递

文件: tests/test_context.py (新建)

测试用例:
- test_planner_receives_requirement
- test_coder_receives_plan
- test_linter_receives_code
- test_fixer_receives_issues
- test_context_preservation_across_steps
```

#### T3.2 端到端流程测试
```
文件: tests/test_e2e.py (新建)

测试用例:
- test_full_development_workflow
- test_review_workflow
- test_iterative_workflow_with_fixes
```

---

### Phase 4: UI 实现完善

#### T4.1 重构 codex_ui.py
```
目标: 实现 PRD 中的完整布局

布局:
┌──────────────────────────────────────────────────────────────────┐
│ [Logo] AI Coder         [Project ▼]  [Workflow: Sequential ▼]   │
├────────────┬─────────────────────────────────┬─────────────────┤
│ PROJECT    │         EDITOR AREA              │  AGENT PANEL    │
│ EXPLORER  │                                 │                 │
│           │                                 │  [Agent Cards]  │
│           │                                 │                 │
├───────────┴─────────────────────────────────┴─────────────────┤
│ TERMINAL / OUTPUT                            │  CHAT AREA     │
│                                               │                │
│ [Collab Events]                              │  [Messages]   │
│                                               │                │
└──────────────────────────────────────────────┴─────────────────┘
```

#### T4.2 Agent 状态面板 (实时更新)
```
需要实现:
- Agent 卡片实时状态更新
- 进度条动画
- 消息气泡显示
```

#### T4.3 协作事件显示 (类似 Codex)
```
事件类型:
- Spawn: "Spawned: [Agent] [role]"
- Interaction: "Sent input to: [Agent]"
- Waiting: "Waiting for: [Agent]"
- Close: "Closed: [Agent] - [status]"
```

#### T4.4 WebSocket 支持 (实时推送)
```
文件: webui/api.py (新建)

API:
- /ws/workflow - WebSocket 实时工作流状态
- /ws/agents - Agent 状态实时推送

事件:
- agent_status_changed
- agent_spawned
- agent_closed
- workflow_progress
```

---

### Phase 5: Tool 系统

#### T5.1 ToolExecutor
```
文件: tools/executor.py (新建)

功能:
- execute(tool_name, params) -> ToolResult
- check_permission(tool_name) -> Permission
- select_sandbox(tool_name) -> SandboxType
- retry_with_escalation(tool_name, attempt)
```

#### T5.2 沙箱隔离
```
文件: tools/sandbox.py (新建)

SandboxType:
- READONLY: 只读文件操作
- WORKSPACE_WRITE: 工作区写入
- DANGEROUS_FULL_ACCESS: 完全访问

功能:
- create_sandbox(sandbox_type) -> Sandbox
- execute_in_sandbox(code, sandbox) -> Result
- destroy_sandbox(sandbox)
```

#### T5.3 重试策略
```
文件: tools/retry.py (新建)

功能:
- exponential_backoff(attempt) -> delay
- max_retries_exceeded -> Error
- circuit_breaker(state)
```

---

## 三、实现顺序

```
Week 1: Phase 1 - 核心框架
  Day 1-2: Agent Registry
  Day 3-4: WorkflowContext 增强
  Day 5-7: Workflow Orchestrator

Week 2: Phase 2 - Agent 实现
  Day 1-2: Agent 基类 + 状态机
  Day 3-4: Coordinator + Planner
  Day 5-7: Coder + Linter

Week 3: Phase 2 + Phase 3
  Day 1-2: Reviewer + Fixer + Tester
  Day 3-5: Context 传递实现
  Day 6-7: Context 传递测试

Week 4: Phase 4 - UI 实现
  Day 1-3: UI 重构
  Day 4-5: Agent 状态面板
  Day 6-7: 协作事件显示

Week 5: Phase 5 + 集成
  Day 1-2: Tool Executor
  Day 3-4: 沙箱隔离
  Day 5-7: 端到端测试 + 验收
```

---

## 四、验收标准

### 功能验收
- [ ] 多 Agent 协作流程端到端运行
- [ ] Context 在 Agent 之间正确传递
- [ ] 工作流支持顺序/并行/迭代模式
- [ ] Agent 状态实时更新
- [ ] 代码生成→审查→修复→测试完整链路

### UI 验收
- [ ] 四面板布局正常显示
- [ ] Agent 卡片状态更新
- [ ] 协作事件可视化
- [ ] Terminal 输出日志

### 性能验收
- [ ] Agent 响应时间 < 10s
- [ ] 支持 5+ 并发 Agent
- [ ] 界面流畅无卡顿

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Agent 协作死锁 | 高 | 实现超时和取消机制 |
| Context 膨胀 | 中 | 实施上下文压缩 |
| LLM 调用失败 | 高 | 实现重试和降级策略 |
| 代码执行安全 | 高 | 严格沙箱隔离 |