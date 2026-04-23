## FEATURE:

### 多Agent协同开发系统 - 代码开发、审查与修复

构建一个基于 PydanticAI 的多Agent协同开发系统，支持：
1. **代码开发** - 多Agent协作生成和修改代码
2. **代码审查** - 检测语法错误、逻辑错误、安全问题
3. **代码修复** - 自动修复发现的问题
4. **WebUI** - 完整的Web界面进行交互

### 核心架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            WebUI (Gradio/FastAPI)                        │
│  - 实时对话界面                    - 代码编辑器预览                        │
│  - 审查结果展示                    - 文件管理                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Coordinator Agent (协调者)                            │
│  - 理解任务需求                          - 分配任务给专业Agent             │
│  - 聚合结果并做出最终决策                - 管理工作流                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌──────────────┐        ┌──────────────────┐        ┌──────────────┐
│ Coder Agent  │        │  Review Agent    │        │  Test Agent   │
│ (代码开发)    │        │  (代码审查)       │        │  (测试覆盖)   │
└──────────────┘        └──────────────────┘        └──────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                          ┌──────────────────┐
                          │  Fixer Agent     │
                          │  (自动修复)       │
                          └──────────────────┘
```

### 核心功能需求

#### 1. WebUI (Gradio/FastAPI)
- **对话界面**: 实时与Agent对话
- **代码预览**: 高亮显示代码修改
- **文件浏览器**: 浏览和管理项目文件
- **审查面板**: 显示发现的问题和修复建议
- **设置面板**: 配置API密钥、模型选择
- **流式输出**: 实时显示Agent思考过程

#### 2. Coordinator Agent (协调者)
- 接收用户的开发/审查请求
- 解析任务类型（开发/审查/修复）
- 协调多个专业Agent并行/串行执行
- 汇总结果并生成统一报告

#### 3. Coder Agent (代码开发)
- 根据需求生成代码
- 遵循项目代码规范
- 使用 agent-framework 模式
- 支持多种编程语言

#### 4. Review Agent (代码审查)
- 代码复杂度分析
- 安全漏洞检测
- 代码风格检查
- 性能反模式识别

#### 5. Test Agent (测试覆盖)
- 生成单元测试
- 生成集成测试
- 覆盖率分析
- 边界条件测试

#### 6. Fixer Agent (自动修复)
- 根据审查结果自动修复
- 迭代式改进
- 代码格式化

### 技术要求

#### Web框架
- **FastAPI**: 后端API
- **Gradio**: 前端界面 (简单易用)
- **WebSocket**: 实时通信

#### Agent框架
- **PydanticAI**: Agent实现
- **多种LLM支持**: OpenAI/Anthropic/Gemini

#### 功能要求
- 代码生成
- 代码审查
- 自动修复
- 测试生成
- 文件操作
- 项目理解

## EXAMPLES:

### 参考示例 (在 examples/agent-framework 中)

#### 1. 多Agent编排模式
- `examples/agent-framework/python/samples/autogen-migration/orchestrations/01_round_robin_group_chat.py` - 顺序执行模式
- `examples/agent-framework/python/samples/autogen-migration/orchestrations/02_selector_group_chat.py` - 选择性群聊模式
- `examples/agent-framework/python/samples/autogen-migration/orchestrations/03_swarm.py` - 任务传递模式
- `examples/agent-framework/python/samples/autogen-migration/orchestrations/04_magentic_one.py` - 协调者模式

#### 2. 并发执行模式
- `examples/agent-framework/python/samples/03-workflows/orchestrations/concurrent_agents.py` - 并行审查
- `examples/agent-framework/python/samples/03-workflows/orchestrations/concurrent_custom_aggregator.py` - 自定义结果聚合

#### 3. 工作流循环模式
- `examples/agent-framework/python/samples/03-workflows/control-flow/simple_loop.py` - Agent判断循环
- `examples/agent-framework/python/samples/03-workflows/orchestrations/magentic.py` - 带流式输出的协调

### 已有的 use-cases 参考
- `use-cases/agent-factory-with-subagents/` - Agent工厂模式
- `use-cases/build-with-agent-team/` - 多Agent团队协作

## DOCUMENTATION:

### PydanticAI 文档
- https://ai.pydantic.dev/agents/ - Agent创建
- https://ai.pydantic.dev/multi-agent-applications/ - 多Agent模式

### WebUI 框架
- https://gradio.app/ - Gradio文档
- https://fastapi.tiangolo.com/ - FastAPI文档

### agent-framework 文档
- `examples/agent-framework/python/README.md`

## OTHER CONSIDERATIONS:

### 项目约束
1. **文件大小限制**: 单个文件不超过500行，需要拆分
2. **模块组织**: agent.py / tools.py / prompts.py / providers.py
3. **测试要求**: 必须创建Pytest测试
4. **代码规范**: PEP8, type hints, docstrings (Google style)
5. **依赖管理**: 使用 python_dotenv, load_env()

### WebUI 设计要求
1. **响应式设计**: 支持不同屏幕尺寸
2. **实时反馈**: 流式输出Agent响应
3. **代码高亮**: 使用Prism.js或Highlight.js
4. **文件管理**: 树形结构展示项目文件

### 安全性要求
1. API密钥安全存储
2. 代码执行沙箱隔离
3. 输入验证
4. 速率限制