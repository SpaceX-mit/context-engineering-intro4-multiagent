# Multi-Agent Code Review - Data Flow Analysis & Fix Report

**Date**: 2025-04-25

---

## 1. Architecture Overview

### 1.1 Project Structure

```
multi-agent-code-review/
├── core/
│   ├── orchestrator.py    ← 工作流编排引擎 (WorkflowOrchestrator)
│   ├── context.py         ← 共享上下文 (WorkflowContext)
│   └── models.py          ← 数据模型
├── agents/
│   ├── coordinator/       ← 需求分析、任务分解
│   ├── planner/           ← 实施计划生成
│   ├── coder/             ← 代码生成
│   ├── linter/            ← 代码风格检查
│   ├── reviewer/          ← 代码质量审查
│   ├── fixer/             ← 自动修复
│   └── test_agent/        ← 测试生成
├── webui/
│   ├── launch.py          ← Gradio 界面 + WorkflowRunner
│   ├── codex_ui.py        ← Flask 桌面 IDE 风格界面
│   └── collab_app.py      ← Flask 协作事件界面
└── tools/                 ← AST分析、安全扫描、覆盖率分析
```

### 1.2 Two Execution Pathways

| 路径 | 入口 | 编排方式 | Agent 实现 |
|------|------|----------|-----------|
| A | `launch.py` WorkflowRunner | `WorkflowOrchestrator` + 注册 handler | 关键词模板 (`agents/coder/agent.py`) |
| B | `codex_ui.py` `/generate_detailed` | 直接顺序调用 Agent | `agent_framework.ollama` LLM Agent |

---

## 2. Data Flow Design (Intended)

编排器 `WorkflowOrchestrator` 定义了明确的 agent-to-agent 数据流：

```
User Requirement
      │
      ▼
[Coordinator] analyze  ───→  (dead step, 输出不被下游使用)
      │
      ▼  input_from: ["requirement"]
[Planner]     plan      ───→  output_to: "plan"
      │
      ▼  input_from: ["plan"]           ← 设计意图: Planner 输出 → Coder 输入
[Coder]       implement ───→  output_to: "code"
      │
      ▼  input_from: ["code"]
[Linter]      lint      ───→  output_to: "lint_issues"
      │
      ▼  input_from: ["code"]
[Reviewer]    review    ───→  output_to: "review_issues"
      │
      ▼  input_from: ["code", "issues"]
[Fixer]       fix       ───→  output_to: "fixed_code"
      │
      ▼  input_from: ["fixed_code"]
[Tester]      test      ───→  output_to: "tests"
```

编排器 `get_input_for_step()` (`core/orchestrator.py:160-238`) 正确实现了：
- `"plan"` → 从 `step_outputs["plan"].result` 读取 Planner 输出
- `"code"` → 从 `step_outputs["code"].result` 读取 Coder 输出
- 等

---

## 3. Bug: Handler 层丢弃了上游数据

### 3.1 Bug #1 — `launch.py:86` coder_handler

**文件**: `webui/launch.py`, 第 74-88 行

**问题代码**:
```python
async def coder_handler(step_input, context):
    plan_text = step_input.data   # ✅ 编排器正确传入了 Planner 的 plan
    if isinstance(plan_text, dict):
        plan_text = plan_text.get("plan", str(plan_text))
    # ...
    code = get_coder_agent().implement(context.requirement)  # ❌ 忽略了 plan_text!
```

`step_input.data` 包含了 Planner 产出的 plan 文本，但 `implement()` 调用时只传了 `context.requirement`（原始用户输入），计划内容被丢弃。

**日志也制造了假象**：
```python
"input": f"Plan: {plan_text[:50]}..."    # UI 上显示 "Plan: ..." 像在用 plan
```
但实际上 `implement()` 根本没收到 plan。

### 3.2 Bug #2 — `codex_ui.py:101` coder_handler

**文件**: `webui/codex_ui.py`, 第 92-103 行

**问题代码** (与 Bug #1 完全相同):
```python
async def coder_handler(step_input, context):
    """Coder: receives plan from planner -> outputs code"""
    plan_text = step_input.data   # ✅ 收到 plan
    # ...
    code = get_coder_agent().implement(context.requirement)  # ❌ 忽略 plan
```

### 3.3 Bug #3 — `codex_ui.py:1419` /generate_detailed 端点

**文件**: `webui/codex_ui.py`, 第 1284-1531 行

**问题**: 每个 Agent 的 prompt 都用原始 `prompt` 格式化，完全不使用上游 Agent 的输出。

```python
# Step 1: Coordinator - 输出被丢弃
coord_prompt = coord_cfg['prompt'].format(requirement=prompt)
coord_result = await coordinator.run(coord_prompt)
coord_output = coord_result.text         # ← 只存到 workflow_steps 展示用

# Step 2: Planner - 没收到 Coordinator 的输出
plan_prompt = plan_cfg['prompt'].format(requirement=prompt)  # ← 缺少 coord_output
plan_result = await planner.run(plan_prompt)
plan_output = plan_result.text           # ← 只存到 workflow_steps 展示用

# Step 3: Coder - 没收到 Planner 的输出
coder_prompt = coder_cfg['prompt'].format(requirement=prompt)  # ← 缺少 plan_output!
```

结果就是 Coder 看到的 prompt 是：
```
Write code for: 写一个计算器
```

Planner 精心产出的实施计划从未传给 Coder。

### 3.4 根本原因总结

```
                    编排器层                        Handler 层
                 ┌──────────────┐            ┌──────────────────┐
                 │ input_from   │  正确传递  │ step_input.data  │
                 │ output_to    │ ────────→  │ 包含上游输出      │
                 │ 数据映射正确  │            │                  │
                 └──────────────┘            │ 但 handler 调用   │
                                             │ implement() 时    │
                                             │ 传的是原始需求    │ ← BUG
                                             └──────────────────┘
```

---

## 4. 修复

### 4.1 Fix #1 — `launch.py` coder_handler

**文件**: `webui/launch.py:86`

**修改**: 将 `plan_text` 作为 `plan` 参数传入 `implement()`。

```python
# Before:
code = get_coder_agent().implement(context.requirement)

# After:
code = get_coder_agent().implement(context.requirement, plan=plan_text)
```

### 4.2 Fix #2 — `codex_ui.py` coder_handler（编排器路径）

**文件**: `webui/codex_ui.py:101`

与 Fix #1 相同的修改。

```python
# Before:
code = get_coder_agent().implement(context.requirement)

# After:
code = get_coder_agent().implement(context.requirement, plan=plan_text)
```

### 4.3 Fix #3 — `codex_ui.py` /generate_detailed 端点

**文件**: `webui/codex_ui.py`

**3a. Planner prompt 加入 Coordinator 输出**:

```python
# Before:
plan_prompt = plan_cfg['prompt'].format(requirement=prompt)

# After:
plan_prompt = plan_cfg['prompt'].format(requirement=prompt, tasks=coord_output)
```

**3b. Coder prompt 加入 Planner 输出**:

```python
# Before:
coder_prompt = coder_cfg['prompt'].format(requirement=prompt)

# After:
coder_prompt = coder_cfg['prompt'].format(requirement=prompt, plan=plan_output)
```

**3c. 更新 prompt 模板**:

Planner prompt 增加 `{tasks}` 占位符:
```
Requirement: {requirement}
Coordinator's task breakdown: {tasks}
```

Coder prompt 增加 `{plan}` 占位符:
```
Requirement: {requirement}
Implementation Plan: {plan}

Write clean Python code based on the plan above...
```

**3d. Coder 的 `input` 字段修正** (之前硬编码为 `"Write code for: {prompt}"`):

```python
# Before:
'input': f"Write code for: {prompt}",

# After:
'input': f"Plan + Requirement: {plan_output[:80]}...",
```

### 4.4 Fix #4 — `CoderAgent.implement()` 和 `generate_code()`

**文件**: `agents/coder/agent.py`, `agents/coder/tools.py`

**4a. agent.py**: 修复类型签名，允许 `plan` 为字符串。

```python
# Before:
def implement(self, requirement: str, plan: Optional[Dict[str, Any]] = None) -> str:

# After:
def implement(self, requirement: str, plan: Optional[Any] = None) -> str:
```

**4b. tools.py**: `generate_code()` 在生成代码时使用 plan 信息。

当 `plan` 参数有值时，将其作为注释附加到生成代码的头部，使生成结果更有上下文。

---

## 5. 修复后的数据流

```
User: "写一个计算器"
      │
      ▼
[Coordinator] → "1. Calculator class 2. Operations 3. Tests"
      │              ↓ (tasks)
      ▼
[Planner]     → "Step 1: Create Calculator class with __init__
                  Step 2: Implement add/subtract/multiply/divide
                  Step 3: Add divide-by-zero handling"
      │              ↓ (plan)
      ▼
[Coder]       → class Calculator: ...  (基于 plan 生成，而非仅基于 "写一个计算器")
      │              ↓ (code)
      ▼
[Linter]      → [issues]
      │              ↓
      ▼
[Reviewer]    → [issues]
      │              ↓ (code + issues)
      ▼
[Fixer]       → fixed code
      │              ↓ (fixed_code)
      ▼
[Tester]      → test code
```

Coder 现在收到的输入是 Planner 产出的结构化计划，而非原始的 "写一个计算器"。

---

## 6. 未修复的已知限制

1. **`generate_code()` 仍是关键词模板**: `agents/coder/tools.py` 的代码生成是硬编码模板匹配（"calculator" → Calculator 类），不是真正的 LLM 生成。修复后 plan 信息会作为注释附加，但代码本身仍是模板。真正的 LLM 代码生成需要通过 `agent_framework` 的 `Agent` 类（如 `/generate_detailed` 端点中使用的）。

2. **Coordinator 在编排器路径中是 dead step**: `DevelopmentWorkflow` 中的 coordinator 步骤没有 `output_to`，其输出不会被任何下游步骤的 `input_from` 引用。Coordinator 的输出只在实际 LLM Agent 路径（`/generate_detailed`）中通过显式 prompt 传递。

3. **Planner 的 `plan()` 方法也是关键词模板**: `agents/planner/tools.py` 的 `create_plan()` 同样是关键词匹配，产出的 plan 质量有限。

4. **并发路径未测试**: `ReviewWorkflow`（concurrent）和 `IterativeWorkflow` 的数据流未做详细验证。

---

## 7. 修复验证

### 7.1 语法检查

所有修改文件通过 AST 语法解析：

```
launch.py: OK
codex_ui.py: OK
coder/agent.py: OK
coder/tools.py: OK
```

### 7.2 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `webui/launch.py:86` | `coder_handler` 将 `plan_text` 传入 `implement()` |
| `webui/codex_ui.py:101` | `coder_handler` (编排器路径) 同上 |
| `webui/codex_ui.py:1404` | Planner prompt 加入 `{tasks}` 占位符，传入 `coord_output` |
| `webui/codex_ui.py:1417` | Planner `input` 字段改为显示 Coordinator 输出 |
| `webui/codex_ui.py:1425` | Coder prompt 加入 `{plan}` 占位符，传入 `plan_output` |
| `webui/codex_ui.py:1442` | Coder `input` 字段改为显示 Plan 而非原始 prompt |
| `webui/codex_ui.py:1332-1334` | Coder prompt 模板增加 `Implementation Plan: {plan}` |
| `webui/codex_ui.py:1319-1322` | Planner prompt 模板增加 `Coordinator's task breakdown: {tasks}` |
| `agents/coder/agent.py:39` | `implement()` 的 `plan` 参数类型从 `Optional[Dict]` 改为 `Optional[Any]` |
| `agents/coder/tools.py:86-104` | `generate_code()` 在有 plan 时附加 plan 注释到代码头 |

### 7.3 修复前后对比

**修复前 (Coder 收到的输入)**:
```
Write code for: 写一个计算器
```

**修复后 (Coder 收到的输入)**:
```
Requirement: 写一个计算器

Implementation Plan:
Step 1: Create Calculator class with __init__
Step 2: Implement add/subtract/multiply/divide methods
Step 3: Add input validation and divide-by-zero handling

Write clean Python code with type hints and docstrings based on the plan above.
```
