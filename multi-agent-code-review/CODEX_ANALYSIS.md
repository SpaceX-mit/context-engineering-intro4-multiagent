# Codex 多 Agent 架构分析

## 项目概述

Codex 是 OpenAI 开发的 AI 编程助手，采用 Rust 实现的多 Agent 协作系统。

### 架构特点

| 特性 | 说明 |
|------|------|
| **语言** | Rust (高性能) |
| **终端 UI** | Ratatui (TUI) |
| **协议** | Model Context Protocol (MCP) |
| **沙箱** | 进程隔离执行 |
| **核心** | 多 Agent 协作 + Skills 系统 |

---

## 一、核心架构

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          Codex CLI                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   TUI    │  │   Exec   │  │   MCP    │  │  Skills  │      │
│  │  (Ratatui)│  │ (Headless)│  │  Server  │  │  System  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │               │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐         │
│  │                    codex-core                       │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │         │
│  │  │  Agent   │  │ Context  │  │  Tools   │       │         │
│  │  │  Control │  │ Management│  │ Orchestrator│      │         │
│  │  └──────────┘  └──────────┘  └──────────┘       │         │
│  └─────────────────────────────────────────────────┘         │
│                            │                                  │
│  ┌────────────────────────┴────────────────────────┐         │
│  │              Protocol Layer (codex-protocol)      │         │
│  └─────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 代码组织结构

```
codex/
├── codex-rs/                    # Rust 主实现
│   ├── core/                    # 核心业务逻辑
│   │   ├── src/
│   │   │   ├── agent/          # Agent 核心
│   │   │   │   ├── control.rs   # Agent 控制
│   │   │   │   ├── registry.rs # Agent 注册表
│   │   │   │   └── role.rs    # Agent 角色
│   │   │   ├── context/        # 上下文管理
│   │   │   ├── tools/          # 工具系统
│   │   │   │   ├── orchestrator.rs  # 工具编排器
│   │   │   │   ├── registry.rs     # 工具注册表
│   │   │   │   └── sandboxing.rs   # 沙箱管理
│   │   │   ├── session/       # 会话管理
│   │   │   ├── codex_delegate.rs   # 委托逻辑
│   │   │   └── client.rs          # 主客户端
│   │   └── ...
│   ├── tui/                    # 终端 UI
│   │   └── src/
│   │       ├── app.rs         # 主应用
│   │       ├── multi_agents.rs # 多 Agent 显示
│   │       └── chatwidget.rs  # 聊天组件
│   ├── skills/                # Skills 系统
│   │   └── src/lib.rs        # Skill 加载器
│   ├── exec/                  # 无头执行
│   └── cli/                   # CLI 入口
└── sdk/                       # SDK 实现
```

---

## 二、Agent 系统

### 2.1 Agent 核心组件

#### AgentRegistry (`core/src/agent/registry.rs`)
管理所有活跃 Agent 的注册表，维护 Agent 树结构。

```rust
pub(crate) struct AgentRegistry {
    active_agents: Mutex<ActiveAgents>,  // 活跃 Agent
    total_count: AtomicUsize,            // 总计数
}

struct ActiveAgents {
    agent_tree: HashMap<String, AgentMetadata>,    // Agent 树
    used_agent_nicknames: HashSet<String>,         // 已用昵称
    nickname_reset_count: usize,                   // 昵称重置计数
}
```

#### AgentControl (`core/src/agent/control.rs`)
多 Agent 操作的控制平面，提供 spawn 和消息传递能力。

```rust
pub(crate) struct AgentControl {
    manager: Weak<ThreadManagerState>,  // 弱引用回管理状态
    state: Arc<AgentRegistry>,          // Agent 注册表
}
```

#### Agent 元数据

```rust
pub(crate) struct AgentMetadata {
    pub(crate) agent_id: Option<ThreadId>,      // Agent 线程 ID
    pub(crate) agent_path: Option<AgentPath>,    // Agent 路径
    pub(crate) agent_nickname: Option<String>,   // 昵称
    pub(crate) agent_role: Option<String>,        // 角色
    pub(crate) last_task_message: Option<String>, // 最近任务
}
```

### 2.2 Agent 生命周期

```
┌─────────────┐
│  Spawning   │ ← 通过 spawn_request 创建
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PendingInit │ ← 初始化中
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Running    │ ← 正在执行任务
└──────┬──────┘
       │
       ├──► Completed ──► Closed
       │
       ├──► Errored ────► Closed
       │
       └──► Interrupted ──► Resuming ──► Running
```

### 2.3 Agent 状态 (`tui/src/multi_agents.rs`)

```rust
pub(crate) enum AgentStatus {
    PendingInit,                    // 等待初始化
    Running,                        // 运行中
    Interrupted,                    // 被中断
    Completed(Option<String>),      // 完成
    Errored(String),               // 错误
    Shutdown,                      // 关闭
    NotFound,                      // 未找到
}
```

---

## 三、多 Agent 协作机制

### 3.1 Agent 间通信

#### InterAgentCommunication 事件

```rust
// Agent  spawn 事件
pub(crate) struct CollabAgentSpawnEndEvent {
    pub(crate) call_id: String,
    pub(crate) sender_thread_id: ThreadId,
    pub(crate) new_thread_id: Option<ThreadId>,
    pub(crate) new_agent_nickname: Option<String>,
    pub(crate) new_agent_role: Option<String>,
    pub(crate) prompt: String,
    pub(crate) model: String,
    pub(crate) reasoning_effort: ReasoningEffortConfig,
    pub(crate) status: AgentStatus,
}

// Agent 交互事件
pub(crate) struct CollabAgentInteractionEndEvent {
    pub(crate) call_id: String,
    pub(crate) sender_thread_id: ThreadId,
    pub(crate) receiver_thread_id: ThreadId,
    pub(crate) receiver_agent_nickname: Option<String>,
    pub(crate) receiver_agent_role: Option<String>,
    pub(crate) prompt: String,
    pub(crate) status: AgentStatus,
}

// 等待事件
pub(crate) struct CollabWaitingBeginEvent {
    pub(crate) sender_thread_id: ThreadId,
    pub(crate) receiver_thread_ids: Vec<ThreadId>,
    pub(crate) receiver_agents: Vec<CollabAgentRef>,
    pub(crate) call_id: String,
}

// 关闭事件
pub(crate) struct CollabCloseEndEvent {
    pub(crate) call_id: String,
    pub(crate) sender_thread_id: ThreadId,
    pub(crate) receiver_thread_id: ThreadId,
    pub(crate) receiver_agent_nickname: Option<String>,
    pub(crate) receiver_agent_role: Option<String>,
    pub(crate) status: AgentStatus,
}
```

### 3.2 Agent 协作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Main Thread (Root Agent)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  User Request ──► Analysis ──► Planning                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│         ┌───────────────────┼───────────────────┐             │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐        │
│  │  Sub-Agent │     │  Sub-Agent │     │  Sub-Agent │        │
│  │  (Worker) │     │  (Review)  │     │  (Tester)  │        │
│  └─────┬──────┘     └─────┬──────┘     └─────┬──────┘        │
│        │                   │                   │               │
│        │   ◄─── Waiting for results ────►      │               │
│        │                   │                   │               │
│        └───────────────────┴───────────────────┘               │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Results Aggregation ──► Final Response                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Session 树结构

```
Session Tree (共享 AgentControl)
│
└── Root Session (Main Thread)
    │
    ├── Sub-Agent 1 (Worker)
    │   └── ...
    │
    ├── Sub-Agent 2 (Reviewer)
    │   └── ...
    │
    └── Sub-Agent 3 (Tester)
        └── ...
```

### 3.4 协作事件流

```rust
// TUI 中渲染协作事件
pub(crate) fn spawn_end(
    ev: CollabAgentSpawnEndEvent,
    spawn_request: Option<&SpawnRequestSummary>,
) -> PlainHistoryCell {
    // "Spawned: Robie [explorer] (gpt-5 high)"
}

pub(crate) fn interaction_end(
    ev: CollabAgentInteractionEndEvent,
) -> PlainHistoryCell {
    // "Sent input to: Robie [explorer]"
}

pub(crate) fn waiting_begin(
    ev: CollabWaitingBeginEvent,
) -> PlainHistoryCell {
    // "Waiting for: Robie [explorer]"
}

pub(crate) fn close_end(
    ev: CollabCloseEndEvent,
) -> PlainHistoryCell {
    // "Closed: Robie [explorer]"
}
```

---

## 四、Tool 系统

### 4.1 Tool Orchestrator (`core/src/tools/orchestrator.rs`)

工具编排器处理 Approvals + Sandbox 选择 + 重试语义。

```rust
pub(crate) struct ToolOrchestrator {
    sandbox: SandboxManager,
}

impl ToolOrchestrator {
    // 核心执行流程:
    // 1. Approval (审批)
    // 2. Select Sandbox (选择沙箱)
    // 3. Attempt (执行)
    // 4. Retry with escalated sandbox (拒绝后升级沙箱重试)
}
```

### 4.2 Tool Runtime trait

```rust
pub trait ToolRuntime<Rq, Out> {
    fn run(&mut self, req: &Rq, attempt: &SandboxAttempt, ctx: &ToolCtx) -> Result<Out, ToolError>;
    fn network_approval_spec(&self, req: &Rq, ctx: &ToolCtx) -> Option<NetworkApprovalSpec>;
    fn exec_approval_requirement(&self, req: &Rq) -> Option<ExecApprovalRequirement>;
}
```

### 4.3 工具执行流程

```
User Tool Call
      │
      ▼
┌─────────────────┐
│  Orchestrator   │
│  (Approval)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sandbox Manager  │
│ (Select Type)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Tool Run      │────►│   Success?     │
│                 │     └────────┬────────┘
└─────────────────┘              │
                       ┌────────┴────────┐
                       │ Yes            │ No
                       ▼                ▼
                   Return          ┌─────────────────┐
                   Result         │  Retry with     │
                                   │  Escalated      │
                                   │  Sandbox        │
                                   └─────────────────┘
```

---

## 五、Context 管理

### 5.1 Context 组件

```
context/
├── mod.rs                      # 模块入口
├── environment_context.rs      # 环境上下文
├── permissions_instructions.rs # 权限指令
├── contextual_user_message.rs  # 用户消息上下文
├── prompts/                   # Prompt 模板
│   └── ...
└── ...
```

### 5.2 环境上下文

```rust
pub struct EnvironmentContext {
    pub cwd: AbsolutePathBuf,           // 当前工作目录
    pub local_apps: Vec<AppInfo>,       // 本地应用
    pub available_skills: Vec<Skill>,   // 可用技能
    pub available_plugins: Vec<Plugin>,  // 可用插件
    pub network_rules: Vec<NetworkRule>,// 网络规则
}
```

---

## 六、Skills 系统

### 6.1 Skill 结构

```
skill-name/
├── SKILL.md (required)        # Skill 定义文件
│   ├── YAML frontmatter      # 元数据
│   └── Markdown body         # 指令
├── agents/                   # UI 元数据
│   └── openai.yaml
├── scripts/                  # 可执行脚本
├── references/               # 参考文档
└── assets/                  # 资源文件
```

### 6.2 SKILL.md 格式

```markdown
---
name: skill-name
description: 描述技能用途和触发条件
---

# Skill Name

## About This Skill
[技能说明]

## When to Use
[触发条件]

## Workflow
[工作流程]
```

### 6.3 Progressive Disclosure

三级加载系统管理上下文:

1. **Metadata** (~100 words) - 始终加载
2. **SKILL.md body** (<5k words) - 触发时加载
3. **Bundled resources** - 按需加载

---

## 七、Session 管理

### 7.1 Session 结构

```
Session
├── conversation_id: ThreadId      # 会话 ID
├── session_source: SessionSource   # 来源 (User/SubAgent)
├── thread_store: ThreadStore      # 线程存储
├── agent_control: AgentControl    # Agent 控制
└── services: SessionServices      # 服务
```

### 7.2 Session 层级

```rust
pub enum SessionSource {
    User,                        // 用户发起
    SubAgent(SubAgentSource),    // 子 Agent
}

pub enum SubAgentSource {
    ThreadSpawn { depth: i32 },  // 线程分支
    // ...
}
```

---

## 八、TUI 多 Agent 显示

### 8.1 Agent 面板 (`tui/src/multi_agents.rs`)

```rust
// Agent 选择条目
pub(crate) struct AgentPickerThreadEntry {
    pub(crate) agent_nickname: Option<String>,   // 昵称
    pub(crate) agent_role: Option<String>,       // 角色
    pub(crate) is_closed: bool,                   // 是否关闭
}

// Spawn 请求摘要
pub(crate) struct SpawnRequestSummary {
    pub(crate) model: String,
    pub(crate) reasoning_effort: ReasoningEffortConfig,
}
```

### 8.2 TUI 布局

```
┌─────────────────────────────────────────────────────────────────┐
│ Codex TUI                                                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌────────────────────────────┐  ┌───────────┐   │
│  │ History │  │     Chat Widget             │  │  Agents   │   │
│  │         │  │                            │  │           │   │
│  │ • User  │  │  Main conversation...     │  │ • Main    │   │
│  │   msg   │  │                            │  │ • Robie   │   │
│  │ • Agent │  │  ┌──────────────────────┐ │  │   [explorer]│  │
│  │   resp  │  │  │ Thinking...          │ │  │           │   │
│  │         │  │  └──────────────────────┘ │  │ ◉ Running │   │
│  │ • Spawn │  │                            │  │           │   │
│  │   Robie │  └────────────────────────────┘  └───────────┘   │
│  └─────────┘                                                      │
├─────────────────────────────────────────────────────────────────┤
│  [Alt+←] Previous Agent  [Alt+→] Next Agent                       │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Agent 导航

```rust
// 键盘快捷键
pub(crate) fn previous_agent_shortcut() -> KeyBinding {
    alt(KeyCode::Left)  // Alt + ←
}

pub(crate) fn next_agent_shortcut() -> KeyBinding {
    alt(KeyCode::Right) // Alt + →
}
```

---

## 九、沙箱系统

### 9.1 Sandbox 类型

```rust
pub enum SandboxType {
    ReadOnly,           // 只读
    WorkspaceWrite,     // 工作区写入
    DangerFullAccess,   // 危险-完全访问
}
```

### 9.2 执行策略

```
Tool Execution
      │
      ▼
┌─────────────────┐
│ Check Approval   │
│ Requirement      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Skip (Pre-      │────►│ Need Approval   │
│ approved)       │     └────────┬────────┘
└─────────────────┘              │
                                  ▼
                         ┌─────────────────┐
                         │ Guardian Review  │
                         │ (Auto Review)   │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │ Approved                  │ Denied
                    ▼                          ▼
              Execute Tool              Return Error
```

---

## 十、关键设计模式

### 10.1 Weak Reference 避免循环

```rust
pub(crate) struct AgentControl {
    manager: Weak<ThreadManagerState>,  // 弱引用
    state: Arc<AgentRegistry>,
}
```

### 10.2 Spawn 预留机制

```rust
pub(crate) fn reserve_spawn_slot(
    self: &Arc<Self>,
    max_threads: Option<usize>,
) -> Result<SpawnReservation> {
    if let Some(max_threads) = max_threads {
        if !self.try_increment_spawned(max_threads) {
            return Err(CodexErr::AgentLimitReached { max_threads });
        }
    }
    // ...
}
```

### 10.3 Thread Spawn Depth 限制

```rust
pub(crate) fn exceeds_thread_spawn_depth_limit(depth: i32, max_depth: i32) -> bool {
    depth > max_depth
}
```

---

## 十一、与 multi-agent-code-review 对比

| 特性 | Codex | multi-agent-code-review |
|------|-------|------------------------|
| **语言** | Rust | Python |
| **Agent 通信** | Session 树 + Event | Workflow Context |
| **UI** | Ratatui TUI | Gradio WebUI |
| **工具执行** | Sandboxed + Orchestrator | Direct exec() |
| **状态管理** | AgentRegistry | WorkflowContext |
| **Skills** | 完整系统 | 无 |
| **协作可视化** | TUI 多 Agent 面板 | Agent 卡片 |

---

## 十二、参考价值

Codex 的设计提供了以下参考:

1. **Agent 树形管理** - 通过 Weak reference 避免循环引用
2. **Event-driven 协作** - 通过 CollabEvent 显示 Agent 交互
3. **Tool Orchestrator** - 审批 + 沙箱 + 重试的统一处理
4. **Skills 渐进加载** - 三级加载减少上下文膨胀
5. **Session 隔离** - 子 Agent 独立 Session 但共享控制平面
