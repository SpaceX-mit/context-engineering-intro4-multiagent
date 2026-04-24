# Multi-Agent Code Development System

基于 Codex 架构的多 Agent 协作开发系统，让多个专业 AI Agent 协同完成项目开发。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MULTI-AGENT COLLABORATION                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐       │
│    │ Coordi- │────▶│ Planner │────▶│  Coder  │────▶│ Linter  │       │
│    │  nator  │     │         │     │         │     │         │       │
│    └─────────┘     └─────────┘     └────┬────┘     └────┬────┘       │
│                                         │               │           │
│                    ┌─────────────────────┼───────────────┘           │
│                    ▼                     ▼                           │
│              ┌─────────┐           ┌─────────┐                       │
│              │Reviewer │           │ Tester  │                       │
│              └────┬────┘           └────┬────┘                       │
│                   │                     │                            │
│              ┌────▼────┐               │                            │
│              │  Fixer  │◀──────────────┘                            │
│              └─────────┘                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent 角色说明

| Agent | 图标 | 职责 | 工作内容 |
|-------|------|------|----------|
| **Coordinator** | 🧠 | 任务协调 | 解析需求、分解任务、协调流程 |
| **Planner** | 📋 | 规划制定 | 分析需求、制定实施计划 |
| **Coder** | 💻 | 代码生成 | 编写 Python 代码、实现功能 |
| **Linter** | 📝 | 风格检查 | 检查代码风格、PEP8 规范 |
| **Reviewer** | 🔍 | 质量审查 | 检查逻辑、安全、边缘情况 |
| **Fixer** | 🔧 | 问题修复 | 自动修复发现的问题 |
| **Tester** | 🧪 | 测试生成 | 生成 pytest 单元测试 |

## 工作流类型

### 1. Sequential Workflow (顺序执行)
```
Coordinator → Planner → Coder → Linter → Reviewer → Tester
```
适合简单项目，一步一步执行。

### 2. Concurrent Workflow (并行执行)
```
┌─────────────┐
│   Linter    │──┐
└─────────────┘  │
                 ├──▶ 汇总结果
┌─────────────┐  │
│  Reviewer   │──┘
└─────────────┘
```
适合代码审查，Linter 和 Reviewer 同时工作。

### 3. Iterative Workflow (迭代优化)
```
Review → Fix → Review → Fix → ... (直到通过)
```
适合高质量要求，循环修复直到通过质量检查。

## 使用方法

### 1. 启动服务

```bash
cd multi-agent-code-review
source .venv311/bin/activate
python -m webui.codex_ui
```

访问 http://localhost:7860

### 2. 界面说明

```
┌────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Coder          [Workflow ▼]     [New Project] [Open] [▶]    │
├────────┬────────────────────────────┬─────────────┬────────────────┤
│ Project│                            │ Agent Status│   💬 Chat      │
│ Explorer│     CODE EDITOR            │             │                │
│        │                            │ 🧠 Coord ✓  │  User: ...     │
│ 📁 src/│  def calculate():         │ 📋 Plan ✓   │                │
│  a.py  │    pass                    │ 💻 Coder ✓  │  AI: ...       │
│        │                            │ 📝 Lint ✓   │                │
│ 📁 tests│                            │ 🔍 Review ✓ │                │
│        │                            │ 🔧 Fixer -  │                │
│        │                            │ 🧪 Test ✓   │                │
├────────┴────────────────────────────┴─────────────┴────────────────┤
│ Terminal / Output                                                  │
│ [System] AI Coder initialized. 7 agents ready.                     │
│ [Coordinator] Task completed.                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 3. 使用流程

1. **输入需求** - 在 Chat 输入框中描述你想做什么
2. **选择工作流** - 选择 Sequential / Concurrent / Iterative
3. **点击发送** - Agent 团队开始协作
4. **观察状态** - 右侧 Agent Panel 实时显示每个 Agent 的工作状态
5. **查看结果** - 代码显示在编辑器中，流程记录在 Terminal

## API 接口

### 生成代码
```bash
curl -X POST http://localhost:7860/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a calculator class"}'
```

### 执行代码
```bash
curl -X POST http://localhost:7860/run \
  -H "Content-Type: application/json" \
  -d '{"code": "print(1+2)"}'
```

### 查看 Agent 状态
```bash
curl http://localhost:7860/agents/status
```

### 执行工作流
```bash
curl -X POST http://localhost:7860/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow": "sequential", "context": {"code": "..."}}'
```

## 工作示例

### 输入
```
Create a simple calculator class with add, subtract, multiply, divide
```

### 执行流程

```
[0s]   🧠 Coordinator: Analyzing requirement...
[1s]   📋 Planner: Creating implementation plan...
[2s]   💻 Coder: Writing Python code...
[3s]   📝 Linter: Checking code style...
[3s]   🔍 Reviewer: Reviewing code quality...
[4s]   🧪 Tester: Generating tests...
[5s]   ✅ Workflow complete!
```

### 输出
```python
from typing import Union

class Calculator:
    """A basic calculator class."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Subtract two numbers."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: float, b: float) -> Union[float, None]:
        """Divide two numbers. Returns None if dividing by zero."""
        if b == 0:
            return None
        return a / b
```

## 实时 Agent 状态

当发送请求时，UI 会实时显示每个 Agent 的状态：

| 状态 | 含义 | 显示 |
|------|------|------|
| ⏳ Waiting | 等待中 | 灰色 |
| 🔄 Running | 执行中 | 蓝色 + 进度条 |
| ✅ Completed | 完成 | 绿色 |
| ❌ Error | 错误 | 红色 |

## 文件结构

```
multi-agent-code-review/
├── agents/
│   ├── base.py              # Agent 基类
│   ├── coordinator/         # 协调者
│   ├── planner/             # 规划师
│   ├── coder/               # 编码员
│   ├── reviewer/            # 审查员
│   ├── linter/              # Linter
│   ├── fixer/               # 修复者
│   ├── test_agent/          # 测试员
│   └── orchestrator/
│       └── workflow.py      # 工作流编排
├── tools/                   # 工具模块
├── skills/                  # Skill 系统
├── core/                    # 核心模块
│   ├── context.py           # 上下文管理
│   └── session.py           # 会话管理
└── webui/
    └── codex_ui.py          # Codex Desktop UI
```

## 依赖

```
agent-framework-core
agent-framework-ollama
agent-framework-openai
agent-framework-orchestrations
flask
flask-cors
pydantic-ai
```

安装依赖：
```bash
source .venv311/bin/activate
pip install -r requirements.txt
```