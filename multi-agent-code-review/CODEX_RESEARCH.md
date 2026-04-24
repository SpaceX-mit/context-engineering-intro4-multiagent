# OpenAI Codex 架构研究

## 核心发现

### 1. Codex是什么
- OpenAI的编程Agent，运行在终端、IDE或桌面应用中
- 支持代码编写、理解、审查、调试和自动化任务
- 基于GPT模型，专注于软件开发

### 2. 核心架构组件

#### Skills (技能系统)
Codex使用可复用的技能系统：
- **Shell** - 执行Shell命令
- **Computer Use** - 自动化GUI操作
- **File Search & Retrieval** - 文件搜索和检索
- **Code Interpreter** - 代码解释执行
- **Apply Patch** - 应用补丁
- **Local Shell** - 本地Shell执行
- **Image Generation** - 图像生成

#### Sandbox (沙箱环境)
- 安全的代码执行环境
- 支持approval policies (审批策略)
- 隔离危险操作

#### Agents (多Agent系统)
- **Hierarchical agents** - 层级Agent
- **Subagents** - 子Agent处理特定任务
- **AGENTS.md** - Agent定义配置

#### Thread (会话管理)
- 多轮对话支持
- 状态持久化
- 对话恢复和分叉
- 上下文压缩 (Compaction)

### 3. SDK架构模式

```python
from codex_app_server import Codex

with Codex() as codex:
    thread = codex.thread_start(model="gpt-5.4")
    result = thread.run("Write a hello world function")
    print(result.final_response)
```

关键概念：
- `Codex()` - 主入口
- `thread_start()` - 创建会话
- `thread.run()` - 执行prompt
- 支持async、streaming、interruption

### 4. Codex CLI vs SDK

**CLI模式** (`codex`命令):
- 交互式终端体验
- 支持多种启动方式
- 集成认证

**SDK模式**:
- Python/TypeScript库
- 程序化控制
- 自定义集成

### 5. 安全机制

- **Approval policies** - 敏感操作需要审批
- **Sandbox isolation** - 危险操作隔离
- **Cyber Safety checks** - 安全检查

---

## 对aicoder系统的启发

### 当前系统问题
1. 仅使用单Agent，没有真正的多Agent协作
2. 缺乏技能系统，tool调用混乱
3. 没有沙箱/安全执行环境
4. 缺乏会话管理
5. 没有上下文工程优化

### Codex风格的重构方向

#### 1. 技能系统 (Skills)
```
skills/
  shell.py       - Shell命令执行
  code_runner.py - Python代码执行
  file_search.py - 文件搜索
  linter.py      - 代码检查
```

#### 2. 多Agent协作
```
agents/
  coordinator.py - 主协调Agent
  planner.py     - 任务规划
  coder.py       - 代码编写
  reviewer.py    - 代码审查
  tester.py      - 测试生成
```

#### 3. 沙箱执行
- 安全的代码执行环境
- 超时和资源限制
- 输出捕获

#### 4. 会话管理
- Thread-based对话
- 上下文压缩
- 状态持久化

#### 5. Streaming支持
- 实时流式输出
- 中断支持
- 进度显示

---

## 参考资料

- GitHub: https://github.com/openai/codex
- Docs: https://developers.openai.com/codex
- SDK: https://github.com/openai/codex/tree/main/sdk/python
