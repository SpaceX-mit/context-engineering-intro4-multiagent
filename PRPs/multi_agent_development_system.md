# PRP: 多Agent协同开发系统 - 代码开发、审查与WebUI

## Purpose
构建一个基于 PydanticAI 的多Agent协同开发系统，支持代码开发、审查、修复，并提供完整的 WebUI 界面。

## Core Principles
1. **Context is King**: 包含所有必要的文档、示例和注意事项
2. **Validation Loops**: 提供AI可执行测试/检查的验证循环
3. **Information Dense**: 使用代码库中的关键词和模式
4. **Progressive Success**: 从简单开始，验证，然后增强

---

## Goal
创建一个生产级的多Agent开发系统，包含：
- **代码开发**: Coder Agent 生成和修改代码
- **代码审查**: Review Agent 检测问题
- **自动修复**: Fixer Agent 自动修复问题
- **测试生成**: Test Agent 生成测试用例
- **WebUI**: Gradio/FastAPI 完整界面

## Why
- **业务价值**: 自动化代码开发流程，提高开发效率
- **一致性**: 确保代码质量标准统一执行
- **可视化**: WebUI 提供直观的交互体验
- **协作**: 多Agent协同处理复杂任务

## What
Web应用，包含：
- 对话界面：与Agent自然语言交互
- 代码编辑器：显示和编辑代码
- 文件浏览器：管理项目文件
- 审查面板：显示问题和建议
- 流式输出：实时显示Agent响应

### Success Criteria
- [ ] WebUI 可正常启动和交互
- [ ] Coder Agent 可生成代码
- [ ] Review Agent 可审查代码
- [ ] Fixer Agent 可自动修复问题
- [ ] Test Agent 可生成测试
- [ ] 多Agent协同工作正常
- [ ] 所有测试通过

---

## All Needed Context

### Documentation & References
```yaml
# MUST READ

- url: https://ai.pydantic.dev/agents/
  why: PydanticAI Agent创建基础

- url: https://ai.pydantic.dev/multi-agent-applications/
  why: 多Agent应用模式

- url: https://gradio.app/docs/
  why: Gradio UI框架文档

- url: https://fastapi.tiangolo.com/
  why: FastAPI后端框架

- file: use-cases/agent-factory-with-subagents/examples/main_agent_reference/cli.py
  why: 流式输出和Agent交互模式

- file: multi-agent-code-review/cli.py
  why: CLI模式，代码审查集成

- file: multi-agent-code-review/agents/coordinator/
  why: 现有Coordinator Agent实现

- file: multi-agent-code-review/core/workflow.py
  why: 工作流编排模式
```

### Current Codebase tree
```bash
multi-agent-code-review/
├── agents/
│   ├── coordinator/
│   ├── fixer/
│   ├── linter/
│   ├── reviewer/
│   └── test_agent/
├── core/
│   ├── models.py
│   └── workflow.py
├── tools/
│   ├── ast_analyzer.py
│   ├── linter_tools.py
│   ├── security_scanner.py
│   └── coverage_analyzer.py
├── cli.py
├── settings.py
├── providers.py
└── requirements.txt
```

### Desired Codebase tree with files to be added
```bash
multi-agent-code-review/
├── agents/                          # 现有Agents
│   ├── coordinator/
│   ├── coder/                      # 新增: Coder Agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── fixer/
│   ├── linter/
│   ├── reviewer/
│   └── test_agent/
├── webui/                           # 新增: WebUI模块
│   ├── __init__.py
│   ├── app.py                     # Gradio应用主入口
│   ├── api.py                     # FastAPI后端
│   ├── components/
│   │   ├── __init__.py
│   │   ├── chat.py               # 聊天组件
│   │   ├── code_editor.py        # 代码编辑器
│   │   ├── file_browser.py       # 文件浏览器
│   │   └── review_panel.py       # 审查面板
│   └── static/
│       └── styles.css
├── core/                           # 现有核心模块
│   ├── models.py
│   └── workflow.py
├── tools/                          # 现有工具
├── cli.py
├── settings.py
├── providers.py
├── requirements.txt
└── tests/
    ├── test_coder.py              # 新增测试
    ├── test_webui.py
    └── ...
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Gradio需要异步处理，使用yield实现流式输出
# CRITICAL: PydanticAI Agent需要正确配置model和provider
# CRITICAL: 文件操作需要安全验证，防止路径遍历
# CRITICAL: 代码执行需要沙箱隔离

# CRITICAL: Gradio chatbot需要使用add()方法添加消息
# CRITICAL: PydanticAI的stream需要使用iter()方法
# CRITICAL: FastAPI需要正确配置CORS中间件
```

---

## Implementation Blueprint

### Data models and structure

```python
# webui/models.py - WebUI数据模型

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class ChatMessage(BaseModel):
    """Chat message model."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    agent: Optional[str] = None
    tool_calls: Optional[List[dict]] = None

class CodeFile(BaseModel):
    """Code file model."""
    path: str
    content: str
    language: str = "python"
    modified: bool = False

class ReviewIssue(BaseModel):
    """Review issue model."""
    file: str
    line: Optional[int]
    severity: str
    issue_type: str
    message: str
    suggestion: Optional[str] = None

class ProjectContext(BaseModel):
    """Project context for agents."""
    root_path: str
    files: List[CodeFile] = Field(default_factory=list)
    selected_file: Optional[str] = None

class AgentResponse(BaseModel):
    """Agent response model."""
    content: str
    agent: str
    tool_calls: List[dict] = Field(default_factory=list)
    code_changes: List[dict] = Field(default_factory=list)
    issues: List[ReviewIssue] = Field(default_factory=list)
```

### List of tasks to be completed

```yaml
Task 1: Update Project Configuration
UPDATE requirements.txt:
  - 添加 fastapi, uvicorn, gradio
  - 添加 sse-starlette (流式响应)

UPDATE settings.py:
  - 添加WebUI相关配置

Task 2: Create Coder Agent
CREATE agents/coder/:
  - agent.py: Coder Agent实现
  - tools.py: 代码生成工具
  - prompts.py: 系统提示词

Task 3: Create WebUI Components
CREATE webui/components/:
  - chat.py: 聊天界面组件
  - code_editor.py: 代码编辑器组件
  - file_browser.py: 文件浏览器组件
  - review_panel.py: 审查结果面板

Task 4: Create WebUI Application
CREATE webui/:
  - app.py: Gradio主应用
  - api.py: FastAPI后端

Task 5: Integrate Agents with WebUI
UPDATE agents/coordinator/tools.py:
  - 添加与WebUI交互的方法
  - 添加流式输出支持

UPDATE agents/coder/agent.py:
  - 添加代码生成功能

Task 6: Add WebUI Tests
CREATE tests/test_webui.py
CREATE tests/test_coder.py

Task 7: Update Documentation
UPDATE README.md with WebUI usage
```

### Per task pseudocode

```python
# Task 3: Chat Component (Gradio)
# Pattern from use-cases/agent-factory-with-subagents/cli.py

def create_chat_interface():
    with gr.Blocks() as demo:
        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(placeholder="Enter your request...")
        send_btn = gr.Button("Send")

        def respond(message, chat_history):
            # 获取Agent响应
            response = coordinator_agent.run(message)

            # 添加到历史
            chat_history.append((message, response.content))
            return "", chat_history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        send_btn.click(respond, [msg, chatbot], [msg, chatbot])

    return demo


# Task 4: Streaming Response
# Pattern from PydanticAI streaming

async def stream_agent_response(message: str, deps):
    """流式返回Agent响应"""
    async with agent.iter(message, deps=deps) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if hasattr(event, 'delta'):
                            yield event.delta.content_delta


# Task 5: Code Editor Component
def create_code_editor(initial_code: str = ""):
    with gr.Column():
        file_selector = gr.Dropdown(label="Select File")
        code_editor = gr.Code(
            initial_code,
            language="python",
            label="Code Editor"
        )
        run_btn = gr.Button("Run Agent on Code")

    return file_selector, code_editor, run_btn


# Task 4: FastAPI Backend
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat(message: str):
    result = await coordinator_agent.run(message)
    return {"response": result.content}

@app.get("/api/files")
async def list_files(path: str):
    # 返回项目文件列表
    pass
```

### Integration Points
```yaml
DEPENDENCIES:
  - Update requirements.txt with:
    gradio>=4.0.0
    fastapi>=0.100.0
    uvicorn>=0.23.0
    sse-starlette>=1.8.0

ENVIRONMENT:
  - add to .env:
    WEBUI_PORT=7860
    WEBUI_HOST=0.0.0.0

CONFIG:
  - CORS配置允许Gradio访问FastAPI
  - 静态文件服务配置
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
cd multi-agent-code-review
ruff check . --fix
mypy . -i

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```bash
python -m pytest tests/ -v

# Expected: All tests pass
```

### Level 3: WebUI Test
```bash
# Start the WebUI
python -m multi_agent_code_review.webui.app

# Test in browser:
# http://localhost:7860

# Test chat functionality
# Test code editor
# Test file browser
```

### Level 4: Integration Test
```bash
# Test full workflow:
# 1. Open WebUI
# 2. Send "Create a simple calculator"
# 3. Verify code is generated
# 4. Send "Review this code"
# 5. Verify issues are displayed
# 6. Send "Fix the issues"
# 7. Verify fixes are applied
```

---

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `ruff check .`
- [ ] No type errors: `mypy .`
- [ ] WebUI starts: `python -m multi_agent_code_review.webui.app`
- [ ] Chat works: Send message and receive response
- [ ] Code editor loads and displays code
- [ ] File browser shows project files
- [ ] Review panel displays issues
- [ ] Coder Agent generates code
- [ ] Review Agent detects issues
- [ ] Fixer Agent fixes code
- [ ] README updated with WebUI instructions

---

## Anti-Patterns to Avoid
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode file paths
- ❌ Don't skip input validation
- ❌ Don't execute untrusted code without sandbox
- ❌ Don't expose API keys in frontend

## Confidence Score: 8/10

High confidence due to:
- Clear Gradio patterns
- Existing PydanticAI implementation
- Established project structure

Minor uncertainty on:
- Streaming response implementation details
- File browser security considerations

---

## Implementation Notes

### WebUI Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Gradio Frontend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Chat     │  │   Code     │  │   Review    │       │
│  │   Panel    │  │   Editor   │  │   Panel     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │ FastAPI
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Coordinator                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Coder   │  │  Review  │  │  Test    │  │  Fixer │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Files to Create
1. `webui/app.py` - Gradio主应用 (约200行)
2. `webui/components/chat.py` - 聊天组件 (约100行)
3. `webui/components/code_editor.py` - 代码编辑器 (约100行)
4. `webui/components/review_panel.py` - 审查面板 (约100行)
5. `agents/coder/agent.py` - Coder Agent (约150行)
6. `tests/test_webui.py` - WebUI测试 (约100行)

### Key Files to Update
1. `requirements.txt` - 添加Gradio/FastAPI依赖
2. `settings.py` - 添加WebUI配置
3. `README.md` - 添加WebUI使用说明
4. `agents/coordinator/tools.py` - 添加流式响应支持