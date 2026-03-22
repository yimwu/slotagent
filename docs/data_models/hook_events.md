# Hook Event Types Data Model

## 概述 (Overview)

Hook 事件系统是 SlotAgent 可观测性的核心机制。通过事件驱动的方式，外部系统可以订阅工具执行生命周期中的关键事件，实现监控、日志、告警、审批等功能。

## Hook 事件类型定义

### 1. HookEvent (基类)

```python
@dataclass
class HookEvent:
    """Base class for all Hook events."""
    event_type: str
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
```

### 2. 核心事件类型

#### 2.1 on_before_exec - 执行前事件

```python
@dataclass
class BeforeExecEvent(HookEvent):
    """
    Event fired before tool execution starts.

    Triggered after schema validation and guard checks pass,
    right before calling tool.execute_func().
    """
    event_type: str = "before_exec"
    params: Dict[str, Any] = field(default_factory=dict)
```

**触发时机**: Schema 和 Guard 插件执行成功后，工具执行前
**用途**:
- 记录执行开始时间
- 执行前置检查
- 发送执行通知

**字段说明**:
- `params`: 已验证的工具参数

#### 2.2 on_after_exec - 执行后事件

```python
@dataclass
class AfterExecEvent(HookEvent):
    """
    Event fired after tool execution completes successfully.

    Triggered after tool.execute_func() returns, before reflect plugin.
    """
    event_type: str = "after_exec"
    params: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    execution_time: float = 0.0
```

**触发时机**: 工具执行成功后，Reflect 插件执行前
**用途**:
- 记录执行结果
- 更新监控指标
- 发送成功通知

**字段说明**:
- `result`: 工具执行结果
- `execution_time`: 工具执行耗时（秒）

#### 2.3 on_fail - 执行失败事件

```python
@dataclass
class FailEvent(HookEvent):
    """
    Event fired when tool execution fails.

    Triggered when tool.execute_func() raises exception,
    or plugin chain fails.
    """
    event_type: str = "fail"
    params: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    error_type: str = ""
    failed_stage: str = ""  # "schema", "guard", "execute", "healing", etc.
```

**触发时机**: 工具执行失败或插件链中断时
**用途**:
- 记录错误日志
- 触发告警
- 记录失败指标

**字段说明**:
- `error`: 错误消息
- `error_type`: 错误类型（如 "ValidationError", "PermissionDenied"）
- `failed_stage`: 失败阶段

#### 2.4 on_guard_block - 守卫拦截事件

```python
@dataclass
class GuardBlockEvent(HookEvent):
    """
    Event fired when Guard plugin blocks execution.

    Triggered when guard plugin returns should_continue=False
    (but not pending approval).
    """
    event_type: str = "guard_block"
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    guard_plugin_id: str = ""
```

**触发时机**: Guard 插件拦截执行时（非审批场景）
**用途**:
- 记录拦截事件
- 安全审计
- 权限分析

**字段说明**:
- `reason`: 拦截原因
- `guard_plugin_id`: 拦截的 Guard 插件 ID

#### 2.5 on_wait_approval - 等待审批事件

```python
@dataclass
class WaitApprovalEvent(HookEvent):
    """
    Event fired when execution is pending approval.

    Triggered when GuardHumanInLoop plugin requires approval.
    """
    event_type: str = "wait_approval"
    params: Dict[str, Any] = field(default_factory=dict)
    approval_id: str = ""
    approval_context: Optional[Dict[str, Any]] = None
```

**触发时机**: GuardHumanInLoop 插件触发人工审批时
**用途**:
- 通知审批人（IM、邮件、Web通知）
- 记录审批请求
- 展示审批界面

**字段说明**:
- `approval_id`: 审批请求 ID（唯一）
- `approval_context`: 审批上下文（风险级别、参数摘要等）

## 事件触发顺序

### 正常执行流程
```
on_before_exec → on_after_exec
```

### 失败流程
```
on_before_exec → on_fail
```

### 守卫拦截流程
```
on_guard_block
```

### 审批流程
```
on_wait_approval → (用户批准) → on_before_exec → on_after_exec
on_wait_approval → (用户拒绝) → on_fail
```

## 事件字段约束

### 必填字段（所有事件）
- `event_type`: 事件类型（字符串，非空）
- `execution_id`: 执行 ID（UUID 格式）
- `tool_id`: 工具 ID（非空）
- `tool_name`: 工具名称（非空）
- `timestamp`: 事件时间戳（Unix timestamp）

### 可选字段
- `metadata`: 扩展元数据（任意键值对）

## 设计决策

### D1: 分离的事件类型而非通用事件
- **决策**: 每个 Hook 类型有独立的数据类
- **理由**:
  - 类型安全，编译时检查
  - 字段清晰，避免可选字段过多
  - 便于文档生成和理解
- **权衡**: 类定义增多，但提高可维护性

### D2: 事件不可变（frozen dataclass）
- **决策**: 考虑使用 frozen dataclass（Phase 5 暂不强制）
- **理由**:
  - 事件应该是不可变的记录
  - 避免订阅者意外修改事件
  - 线程安全
- **权衡**: Phase 5 先使用普通 dataclass，后续可优化

### D3: 最小化事件数量
- **决策**: 只定义 5 个核心事件类型
- **理由**:
  - 覆盖主要场景
  - 避免事件爆炸
  - 保持简单
- **权衡**: 一些细节场景通过 metadata 扩展

### D4: execution_id 作为关联 ID
- **决策**: 所有事件携带相同的 execution_id
- **理由**:
  - 便于追踪完整执行链路
  - 便于日志关联
  - 支持分布式追踪
- **权衡**: 无

## 使用示例

### 订阅事件示例

```python
def on_tool_fail(event: FailEvent):
    """Handle tool execution failure."""
    logger.error(
        f"Tool {event.tool_id} failed: {event.error}",
        extra={
            "execution_id": event.execution_id,
            "error_type": event.error_type,
            "failed_stage": event.failed_stage
        }
    )

    # Send alert
    if event.error_type == "PermissionDenied":
        send_security_alert(event)

# Subscribe to hook
hook_manager.subscribe("fail", on_tool_fail)
```

### 触发事件示例（内部实现）

```python
# In CoreScheduler
def _execute_plugin_chain(self, context, tool):
    try:
        # Fire before_exec event
        self.hook_manager.emit(BeforeExecEvent(
            execution_id=context.execution_id,
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            timestamp=time.time(),
            params=context.params
        ))

        # Execute tool
        result = tool.execute_func(context.params)

        # Fire after_exec event
        self.hook_manager.emit(AfterExecEvent(
            execution_id=context.execution_id,
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            timestamp=time.time(),
            params=context.params,
            result=result,
            execution_time=time.time() - context.start_time
        ))

    except Exception as e:
        # Fire fail event
        self.hook_manager.emit(FailEvent(
            execution_id=context.execution_id,
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            timestamp=time.time(),
            params=context.params,
            error=str(e),
            error_type=type(e).__name__,
            failed_stage="execute"
        ))
```

## 不变式 (Invariants)

### INV-HOOK-1: 事件类型唯一性
- 每个事件的 `event_type` 必须唯一且与类名对应

### INV-HOOK-2: execution_id 一致性
- 同一次工具执行的所有事件必须有相同的 `execution_id`

### INV-HOOK-3: 时间戳单调性
- 同一 execution_id 的事件时间戳应单调递增

### INV-HOOK-4: 必填字段非空
- 所有必填字段（event_type, execution_id, tool_id, tool_name, timestamp）不能为空

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义 5 个核心 Hook 事件类型
