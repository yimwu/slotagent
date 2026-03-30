# Hook Event Types Data Model

**文档版本:** 1.1
**最后更新:** 2026-03-27
**状态:** Approved

## 概述 (Overview)

Hook 事件数据模型定义了 SlotAgent 在工具执行生命周期中对外暴露的观测结构。外部系统通过订阅不同事件类型，可以获得执行前、执行后、失败、守卫拦截、审批等待、恢复重试等关键状态。

在保持既有 5 个核心事件完全兼容的前提下，第一批新增 6 个调度阶段细粒度事件：

- `before_schema`
- `after_schema`
- `before_guard`
- `after_healing`
- `retry_started`
- `after_reflect`

因此，当前正式数据模型范围共 11 个调度域事件。`approval_resolved` 为第二批审批域事件，暂不纳入本批正式数据模型。

## 设计原则 (Design Principles)

1. **类型清晰**：每种事件使用独立数据类，避免字段语义混杂。
2. **向后兼容**：既有 5 个事件名称、字段和语义保持兼容。
3. **事件数量受控**：只为真实需求新增事件，不补充未明确需要的对称事件。
4. **全链路可追踪**：同一次执行的所有调度域事件共享同一个 `execution_id`。
5. **阶段结果显式化**：Schema、Healing、Reflect 的关键结果通过独立事件暴露，而不是把语义塞进 `metadata`。

## 接口定义 (Interface Specification)

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

### 2. 事件总览

| 事件名 | 触发时机 | 关键字段 |
|------|---------|---------|
| `before_schema` | Schema 插件执行前 | `params` |
| `after_schema` | Schema 插件返回后 | `params`、`success`、`should_continue`、`schema_plugin_id`、`error` |
| `before_guard` | Guard 插件执行前 | `params` |
| `before_exec` | 工具执行前 | `params` |
| `after_exec` | 工具执行成功后 | `params`、`result`、`execution_time` |
| `fail` | 工具执行或插件链失败时 | `params`、`error`、`error_type`、`failed_stage` |
| `after_healing` | Healing 插件执行后 | `attempt`、`max_attempts`、`recovered`、`fixed_params_applied`、`healing_plugin_id`、`error` |
| `retry_started` | Healing 判定可恢复、准备进入下一次尝试前 | `attempt`、`next_attempt`、`max_attempts`、`reason` |
| `after_reflect` | Reflect 插件执行后 | `reflect_plugin_id`、`success`、`should_continue`、`error` |
| `guard_block` | Guard 插件拦截执行时 | `params`、`reason`、`guard_plugin_id` |
| `wait_approval` | GuardHumanInLoop 触发人工审批时 | `params`、`approval_id`、`approval_context` |

### 3. 调度前置阶段事件

#### 3.1 BeforeSchemaEvent

```python
@dataclass
class BeforeSchemaEvent(HookEvent):
    """Event fired before schema plugin execution starts."""
    event_type: str = "before_schema"
    params: Dict[str, Any] = field(default_factory=dict)
```

**触发时机**：存在 Schema 插件，且即将执行该插件时。

**字段说明**：
- `params`: 当前待校验参数。

#### 3.2 AfterSchemaEvent

```python
@dataclass
class AfterSchemaEvent(HookEvent):
    """Event fired after schema plugin execution returns."""
    event_type: str = "after_schema"
    params: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    should_continue: bool = True
    schema_plugin_id: str = ""
    error: str = ""
```

**触发时机**：Schema 插件返回后，无论是否通过校验都触发一次。

**字段说明**：
- `params`: Schema 阶段处理后的参数快照。
- `success`: Schema 插件是否成功执行。
- `should_continue`: 插件链是否允许继续。
- `schema_plugin_id`: 当前 Schema 插件 ID。
- `error`: 失败或拒绝继续时的错误信息。

#### 3.3 BeforeGuardEvent

```python
@dataclass
class BeforeGuardEvent(HookEvent):
    """Event fired before guard plugin execution starts."""
    event_type: str = "before_guard"
    params: Dict[str, Any] = field(default_factory=dict)
```

**触发时机**：存在 Guard 插件，且即将执行该插件时。

**字段说明**：
- `params`: 当前待检查参数。

### 4. 核心执行事件

#### 4.1 BeforeExecEvent

```python
@dataclass
class BeforeExecEvent(HookEvent):
    """Event fired before tool execution starts."""
    event_type: str = "before_exec"
    params: Dict[str, Any] = field(default_factory=dict)
```

**触发时机**：Schema / Guard 阶段允许继续后，工具执行前。

#### 4.2 AfterExecEvent

```python
@dataclass
class AfterExecEvent(HookEvent):
    """Event fired after tool execution completes successfully."""
    event_type: str = "after_exec"
    params: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    execution_time: float = 0.0
```

**触发时机**：工具执行成功返回后，Reflect 插件执行前。

**字段说明**：
- `result`: 工具执行结果。
- `execution_time`: 当前执行耗时（秒）。

#### 4.3 FailEvent

```python
@dataclass
class FailEvent(HookEvent):
    """Event fired when tool execution or plugin chain fails."""
    event_type: str = "fail"
    params: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    error_type: str = ""
    failed_stage: str = ""
```

**触发时机**：Schema 阶段失败、工具执行抛错或插件链中断时。

**字段说明**：
- `error`: 错误消息。
- `error_type`: 错误类型。
- `failed_stage`: 失败阶段，例如 `schema`、`execute`。

### 5. 恢复与反思事件

#### 5.1 AfterHealingEvent

```python
@dataclass
class AfterHealingEvent(HookEvent):
    """Event fired after healing plugin execution returns."""
    event_type: str = "after_healing"
    attempt: int = 1
    max_attempts: int = 1
    recovered: bool = False
    fixed_params_applied: bool = False
    healing_plugin_id: str = ""
    error: str = ""
```

**触发时机**：工具执行失败后，Healing 插件真实执行结束时。

**字段说明**：
- `attempt`: 刚刚失败的执行尝试编号（1-based）。
- `max_attempts`: 当前执行允许的总尝试次数。
- `recovered`: Healing 是否判定为可恢复。
- `fixed_params_applied`: 是否已将修复后的参数应用到上下文。
- `healing_plugin_id`: 当前 Healing 插件 ID。
- `error`: Healing 阶段的错误信息；若仅判定不可恢复，可为空。

#### 5.2 RetryStartedEvent

```python
@dataclass
class RetryStartedEvent(HookEvent):
    """Event fired right before the next retry attempt starts."""
    event_type: str = "retry_started"
    attempt: int = 1
    next_attempt: int = 2
    max_attempts: int = 1
    reason: str = ""
```

**触发时机**：Healing 明确给出“可恢复并继续下一次尝试”后，下一次工具执行开始前。

**字段说明**：
- `attempt`: 当前已失败的尝试编号。
- `next_attempt`: 即将开始的下一次尝试编号。
- `max_attempts`: 当前执行允许的总尝试次数。
- `reason`: 触发重试的原因说明。

#### 5.3 AfterReflectEvent

```python
@dataclass
class AfterReflectEvent(HookEvent):
    """Event fired after reflect plugin execution returns."""
    event_type: str = "after_reflect"
    reflect_plugin_id: str = ""
    success: bool = True
    should_continue: bool = True
    error: str = ""
```

**触发时机**：Reflect 插件执行完成后。

**字段说明**：
- `reflect_plugin_id`: 当前 Reflect 插件 ID。
- `success`: Reflect 插件是否成功执行。
- `should_continue`: Reflect 是否建议继续主流程。
- `error`: Reflect 阶段错误信息。

### 6. Guard 结果事件

#### 6.1 GuardBlockEvent

```python
@dataclass
class GuardBlockEvent(HookEvent):
    """Event fired when guard plugin blocks execution."""
    event_type: str = "guard_block"
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    guard_plugin_id: str = ""
```

**触发时机**：Guard 插件拒绝执行且不是人工审批场景时。

#### 6.2 WaitApprovalEvent

```python
@dataclass
class WaitApprovalEvent(HookEvent):
    """Event fired when execution is pending approval."""
    event_type: str = "wait_approval"
    params: Dict[str, Any] = field(default_factory=dict)
    approval_id: str = ""
    approval_context: Optional[Dict[str, Any]] = None
```

**触发时机**：GuardHumanInLoop 触发人工审批时。

**字段说明**：
- `approval_id`: 审批请求 ID。
- `approval_context`: 审批上下文，例如参数摘要、风险说明等。

## 流程与状态 (Workflow & State Machines)

### 1. 正常执行流程

```text
before_schema -> after_schema -> before_guard -> before_exec -> after_exec -> after_reflect
```

### 2. Schema 失败流程

```text
before_schema -> after_schema -> fail
```

### 3. Healing 恢复流程

```text
before_exec -> fail -> after_healing -> retry_started -> after_exec -> after_reflect
```

### 4. Guard 拦截流程

```text
before_guard -> guard_block
```

### 5. 审批等待流程

```text
before_guard -> wait_approval
```

**说明**：当前 Hook 数据模型只覆盖“进入等待审批”这一观测点；审批终态通知 `approval_resolved` 将在第二批单独引入，且不等价于恢复工具执行。

## 事件字段约束 (Field Constraints)

### 1. 所有事件的公共约束

- `event_type`：非空，且必须与事件类语义一一对应。
- `execution_id`：非空，同一次调度链中的所有事件保持一致。
- `tool_id`：非空。
- `tool_name`：非空。
- `timestamp`：Unix 时间戳，且同一 `execution_id` 下应单调递增。
- `metadata`：可选扩展字段，不应用于承载核心事件语义。

### 2. 阶段性约束

1. `after_schema` 只要 Schema 插件执行过，就必须触发一次。
2. `before_guard` 仅在 Guard 插件存在且真实执行时触发。
3. `after_healing` 仅在工具执行失败且 Healing 插件真实执行时触发。
4. `retry_started` 仅在 `recovered=True` 且确有下一次尝试时触发。
5. `after_reflect` 仅在 Reflect 插件真实执行时触发。
6. `wait_approval` 必须携带非空 `approval_id`。

### 3. 重试编号约束

- `attempt` 使用 1-based 编号。
- `next_attempt = attempt + 1`。
- `next_attempt <= max_attempts`。
- 同一次恢复链中，`retry_started` 的编号必须稳定可预测。

## 设计决策 (Design Decisions)

### D1: 独立数据类而非单一通用事件
- **决策**：每个 Hook 类型使用独立数据类。
- **理由**：字段语义明确、类型检查直接、文档更清晰。

### D2: 细粒度事件显式建模
- **决策**：将 Schema、Healing、Reflect 的关键结果独立为事件，而不是仅依赖 `fail` 或 `metadata`。
- **理由**：提升可观测性，便于测试和外部系统精确订阅。

### D3: 事件数量受控扩展
- **决策**：从 5 个核心事件扩展到 11 个调度域事件，但不引入未明确需求的对称事件。
- **理由**：兼顾可观测性与复杂度控制。

### D4: 审批终态单独分批
- **决策**：`approval_resolved` 延后到第二批实现。
- **理由**：审批结果通知与调度链恢复是不同问题，应避免一次性耦合。

## 不变式 (Invariants)

### INV-HOOK-1: 事件类型唯一性
- 每个事件的 `event_type` 必须唯一且与类语义一致。

### INV-HOOK-2: execution_id 一致性
- 同一次工具执行的所有调度域事件必须共享同一个 `execution_id`。

### INV-HOOK-3: 时间戳单调性
- 同一 `execution_id` 的事件时间戳应单调递增。

### INV-HOOK-4: 必填字段非空
- 所有公共必填字段不能为空。

### INV-HOOK-5: 重试事件可推导性
- `retry_started.next_attempt` 必须能由 `attempt + 1` 推导，且不超过 `max_attempts`。

## 变更历史 (Changelog)

- **1.1** (2026-03-27): 同步第一批细粒度 Hook 数据模型，新增 6 个调度阶段事件并修正审批流程边界说明。
- **1.0** (2026-03-22): 初始版本，定义 5 个核心 Hook 事件类型。
