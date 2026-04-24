# Multi-Agent Context 传递设计方案

## 问题分析

### 当前问题
1. Agent 之间没有信息传递
2. 各 Agent 收到的是静态 prompt，无法形成协作链
3. 无法端到端完成一个任务

### 期望流程
```
用户需求 → Planner(分析) → Coder(生成) → Linter+Reviewer(审查) → Fixer(修复) → Tester(测试)
              ↓              ↓              ↓                ↓             ↓
           context[      context[       context[         context[       context[
             plan]      code]         issues]         fixed_code]    tests]
```

---

## 设计方案

### 1. Context 数据结构

```python
@dataclass
class WorkflowContext:
    """工作流上下文 - 在 Agent 之间传递"""

    # 输入
    requirement: str = ""                    # 用户需求

    # 中间产物
    plan: Optional[str] = None               # Planner 输出的计划
    code: Optional[str] = None               # Coder 生成的代码
    lint_issues: List[CodeIssue] = field(default_factory=list)    # Linter 发现的问题
    review_issues: List[CodeIssue] = field(default_factory=list)   # Reviewer 发现的问题
    fixed_code: Optional[str] = None         # Fixer 修复后的代码
    tests: Optional[str] = None              # Tester 生成的测试

    # 状态
    current_step: str = "pending"           # 当前步骤
    iteration: int = 0                       # 迭代次数
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requirement": self.requirement,
            "plan": self.plan,
            "code": self.code,
            "lint_issues": [i.to_dict() for i in self.lint_issues],
            "review_issues": [i.to_dict() for i in self.review_issues],
            "fixed_code": self.fixed_code,
            "tests": self.tests,
            "current_step": self.current_step,
            "iteration": self.iteration,
        }
```

### 2. Agent 协作 Prompt 模板

#### Planner Agent
```
你是一个规划 Agent。用户需求如下：

## 用户需求
{requirement}

你的任务：
1. 分析需求，确定需要创建的文件和模块
2. 制定实现步骤
3. 考虑依赖关系

请输出：
### 分析
[对需求的理解]

### 计划
1. [步骤1]
2. [步骤2]
...

### 文件结构
- file1.py: [用途]
- file2.py: [用途]
```

#### Coder Agent
```
你是编码 Agent。根据以下计划生成代码：

## 实现计划
{plan}

## 用户需求
{requirement}

任务：
1. 按照计划生成完整的、可运行的 Python 代码
2. 代码必须包含类型提示和文档字符串
3. 确保代码可以正常执行

输出格式：
```python
# filename.py
[完整代码]
```

## 重要
- 生成完整代码，不要省略任何部分
- 代码必须能够直接运行
```

#### Linter Agent
```
你是代码审查 Agent。检查以下代码的风格问题：

## 待审查代码
```{code}```

任务：
1. 运行 ruff linter 检查风格
2. 返回发现的问题列表
3. 标记哪些可以自动修复

输出格式：
```json
{{
  "issues": [
    {{"line": 1, "rule": "E501", "message": "...", "auto_fixable": true}},
    ...
  ]
}}
```
```

#### Reviewer Agent
```
你是代码审查 Agent。检查以下代码的质量问题：

## 待审查代码
```{code}```

任务：
1. 检查逻辑错误
2. 检查安全问题
3. 检查性能问题
4. 检查边缘情况

输出格式：
```json
{{
  "issues": [
    {{"line": 10, "severity": "high", "type": "security", "message": "..."}},
    ...
  ]
}}
```
```

#### Fixer Agent
```
你是修复 Agent。根据发现的问题修复代码：

## 原代码
```{code}```

## 发现的问题
{issues}

任务：
1. 逐一修复每个问题
2. 保持代码原有功能
3. 确保修复后代码可以运行

输出格式：
```python
# filename.py (fixed)
[修复后的完整代码]
```
```

#### Tester Agent
```
你是测试 Agent。为代码生成测试：

## 待测试代码
```{code}```

任务：
1. 分析代码功能
2. 生成单元测试
3. 确保测试覆盖关键路径

输出格式：
```python
# test_filename.py
[完整测试代码]
```
```

### 3. Workflow 改造

```python
class Workflow:
    """改造后的工作流"""

    async def _run_planner(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Planner: 从 context 读取 requirement，输出 plan 到 context"""
        from agents.planner import get_planner_agent

        # ✅ 从 context 读取
        requirement = context.requirement

        # ✅ 构建动态 prompt
        prompt = f"""用户需求：{requirement}

请制定实现计划。"""

        agent = get_planner_agent()
        result = await agent.run(prompt)

        # ✅ 保存到 context
        context.plan = result
        context.current_step = "planner_completed"

        return {"plan": result}

    async def _run_coder(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Coder: 从 context 读取 plan，输出 code 到 context"""
        from agents.coder import get_coder_agent

        # ✅ 从 context 读取前序输出
        plan = context.plan
        requirement = context.requirement

        # ✅ 构建动态 prompt
        prompt = f"""## 实现计划
{plan}

## 用户需求
{requirement}

请按照计划生成代码。"""

        agent = get_coder_agent()
        result = await agent.run(prompt)

        # ✅ 提取代码并保存
        code = extract_code(result)
        context.code = code
        context.current_step = "coder_completed"

        return {"code": code, "raw_response": result}

    async def _run_linter(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Linter: 从 context 读取 code，输出 issues 到 context"""
        from agents.linter import get_linter_agent

        code = context.code
        prompt = f"检查以下代码的风格问题：\n\n```{code}```"

        agent = get_linter_agent()
        result = await agent.run(prompt)

        # ✅ 解析问题并保存
        issues = parse_lint_issues(result)
        context.lint_issues = issues

        return {"issues": issues}

    async def _run_reviewer(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Reviewer: 从 context 读取 code，输出 issues 到 context"""
        from agents.reviewer import get_reviewer_agent

        code = context.code
        prompt = f"审查以下代码的质量：\n\n```{code}```"

        agent = get_reviewer_agent()
        result = await agent.run(prompt)

        # ✅ 解析问题并保存
        issues = parse_review_issues(result)
        context.review_issues = issues

        return {"issues": issues}

    async def _run_fixer(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Fixer: 从 context 读取 code + issues，输出 fixed_code 到 context"""
        from agents.fixer import get_fixer_agent

        code = context.code
        all_issues = context.lint_issues + context.review_issues

        prompt = f"""## 原代码
```{code}```

## 发现的问题
{format_issues(all_issues)}

请修复这些问题。"""

        agent = get_fixer_agent()
        result = await agent.run(prompt)

        # ✅ 提取修复后的代码
        fixed_code = extract_code(result)
        context.fixed_code = fixed_code
        context.code = fixed_code  # 更新 code 为修复版本

        return {"fixed_code": fixed_code}

    async def _run_tester(self, step: WorkflowStep, context: WorkflowContext) -> Dict:
        """Tester: 从 context 读取 code，输出 tests 到 context"""
        from agents.test_agent import get_tester_agent

        code = context.code
        prompt = f"为以下代码生成测试：\n\n```{code}```"

        agent = get_tester_agent()
        result = await agent.run(prompt)

        # ✅ 提取测试代码并保存
        tests = extract_code(result)
        context.tests = tests

        return {"tests": tests}
```

### 4. 开发工作流定义

```python
class MultiAgentWorkflow:
    """开发工作流 - 端到端"""

    @staticmethod
    def create_development_workflow() -> Workflow:
        """完整的开发流程"""
        return (
            WorkflowBuilder()
            .create("DevelopmentWorkflow", WorkflowType.SEQUENTIAL)
            # Step 1: Planner 分析需求
            .add_step("Planning", "planner", "analyze", {
                "input_from": "requirement"
            })
            # Step 2: Coder 生成代码
            .add_step("Coding", "coder", "implement", {
                "input_from": "plan"
            })
            # Step 3: Linter + Reviewer 并行审查
            .add_step("Lint", "linter", "check_style", {
                "input_from": "code",
                "output_to": "lint_issues"
            })
            .add_step("Review", "reviewer", "check_quality", {
                "input_from": "code",
                "output_to": "review_issues"
            })
            # Step 4: Fixer 修复问题
            .add_step("Fix", "fixer", "repair", {
                "input_from": ["code", "lint_issues", "review_issues"],
                "output_to": "fixed_code"
            })
            # Step 5: Tester 生成测试
            .add_step("Test", "tester", "generate_tests", {
                "input_from": "fixed_code",
                "output_to": "tests"
            })
            .build()
        )

    @staticmethod
    def create_review_workflow() -> Workflow:
        """审查工作流 - 并行审查后修复"""
        return (
            WorkflowBuilder()
            .create("ReviewWorkflow", WorkflowType.CONCURRENT)
            .add_step("Lint", "linter", "check_style", {"input_from": "code"})
            .add_step("Review", "reviewer", "check_quality", {"input_from": "code"})
            .build()
        )

    @staticmethod
    def create_iterative_workflow(max_iterations: int = 3) -> Workflow:
        """迭代工作流 - 审查→修复→审查 直到通过"""
        return (
            WorkflowBuilder()
            .create("IterativeWorkflow", WorkflowType.ITERATIVE)
            .add_step("ReviewCycle", "multi", "review_and_fix", {
                "max_iterations": max_iterations
            })
            .build()
        )
```

### 5. 执行流程示例

```python
async def run_full_development(requirement: str) -> WorkflowContext:
    """端到端运行示例"""

    # 1. 初始化 context
    context = WorkflowContext(requirement=requirement)

    # 2. 创建工作流
    workflow = MultiAgentWorkflow.create_development_workflow()

    # 3. 执行工作流
    result = await workflow.execute(context)

    # 4. 返回最终 context
    return context


# 使用示例
async def main():
    requirement = "创建一个待办事项管理应用，支持添加、删除、完成任务"

    context = await run_full_development(requirement)

    # 输出结果
    print(f"✅ 完成！")
    print(f"📄 代码: {context.code[:100]}...")
    print(f"🧪 测试: {context.tests[:100]}...")
    print(f"📋 问题: {len(context.review_issues)} 个")
```

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `core/context.py` | 新增 `WorkflowContext` 数据类 |
| `agents/orchestrator/workflow.py` | 重写 `_run_*` 方法，使用动态 prompt |
| `agents/planner/prompts.py` | 定义 Planner 的 prompt 模板 |
| `agents/coder/prompts.py` | 定义 Coder 的 prompt 模板 |
| `agents/reviewer/prompts.py` | 定义 Reviewer 的 prompt 模板 |
| `agents/linter/prompts.py` | 定义 Linter 的 prompt 模板 |
| `agents/fixer/prompts.py` | 定义 Fixer 的 prompt 模板 |
| `agents/test_agent/prompts.py` | 定义 Tester 的 prompt 模板 |
| `agents/orchestrator/builder.py` | 添加 input_from/output_to 支持 |

---

## 验证标准

### 功能验证
- [ ] Planner 能读取用户需求，输出计划
- [ ] Coder 能读取计划，生成代码
- [ ] Linter/Reviewer 能并行审查代码
- [ ] Fixer 能读取问题，修复代码
- [ ] Tester 能读取代码，生成测试

### 端到端验证
- [ ] 输入一个需求，经过完整流程，输出代码+测试
- [ ] 工作流状态能正确反映当前步骤
- [ ] 迭代流程能正常工作

### UI 验证
- [ ] Agent 面板能显示当前正在运行的 agent
- [ ] Terminal 能显示 agent 之间的信息传递
- [ ] 最终结果能正确展示
