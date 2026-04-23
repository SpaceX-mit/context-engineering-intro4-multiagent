### 🔄 Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for unit tests.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic
    - `tools.py` - Tool functions used by the agent
    - `prompts.py` - System prompts
    - `providers.py` - LLM provider configuration
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a "Discovered During Work" section.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.

### 🤖 Multi-Agent Development (多Agent协同开发)

#### Agent架构模式
- **每个Agent是一个独立模块**: 包含 `agent.py`, `tools.py`, `prompts.py`
- **使用 agent-framework 编排模式**:
  - `SequentialBuilder`: 线性审查 (Linter → Review → Fix)
  - `ConcurrentBuilder`: 并行多维度审查
  - `GroupChatBuilder`: 多Expert讨论
  - `HandoffBuilder`: 任务传递
  - `MagenticBuilder`: 协调者模式

#### 专业化Agent职责
| Agent | 职责 | 使用模式 |
|-------|------|---------|
| Coordinator | 任务分配、结果汇总 | MagenticBuilder |
| Linter | 代码规范检查 | SequentialBuilder |
| Reviewer | 代码质量审查 | GroupChatBuilder |
| TestAgent | 测试覆盖检查 | ConcurrentBuilder |
| Fixer | 自动修复问题 | WorkflowBuilder + Reflection |

#### 协作流程
```
1. 用户请求 → Coordinator 解析
2. Coordinator → 分配任务给专业Agent
3. 专业Agent并行/串行执行
4. 结果汇总 → Coordinator
5. Coordinator → Fixer 修复问题
6. 迭代直到质量达标
```

#### 参考示例位置
- 多Agent编排: `examples/agent-framework/python/samples/autogen-migration/orchestrations/`
- 工作流模式: `examples/agent-framework/python/samples/03-workflows/`
- Agent-as-Tool: `examples/agent-framework/python/samples/autogen-migration/single_agent/04_agent_as_tool.py`

#### 输出规范
所有Agent的输出必须符合以下格式:
```json
{
  "status": "success|error|pending",
  "agent": "agent_name",
  "results": [...],
  "next_action": "recommend_action"
}
```

### 🔍 Code Review Agent 特定规则

#### 审查优先级
1. **Critical**: 语法错误、逻辑错误、安全漏洞
2. **High**: 代码风格、未使用变量、缺失类型注解
3. **Medium**: 可维护性、复杂度
4. **Low**: 性能优化建议

#### 自动修复能力
- Linter问题: 可自动修复
- Review问题: 需确认后修复
- Test问题: 生成修复建议

#### 结果报告格式
```json
{
  "summary": {
    "files_reviewed": 10,
    "issues_found": 25,
    "critical": 3,
    "high": 8,
    "medium": 10,
    "low": 4,
    "auto_fixed": 11,
    "manual_review_needed": 2
  },
  "details": [...]
}
```