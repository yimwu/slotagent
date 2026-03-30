# Hook System Architecture

**文档版本:** 1.1
**最后更新:** 2026-03-27
**状态:** Approved

## 概述 (Overview)

Hook 系统是 SlotAgent 可观测性的核心机制。通过发布-订阅模型，核心调度引擎只负责在关键生命周期节点发出事件，外部系统按需订阅并处理这些事件，从而实现日志、监控、审批通知、审计等能力，同时保持内核轻量和职责边界清晰。

在保持既有 5 个核心事件完全兼容的前提下，第一批扩展新增 6 个调度阶段细粒度事件：

- `before_schema`
- `after_schema`
- `before_guard`
- `after_healing`
- `retry_started`
- `after_reflect`

因此，当前正式纳入 Hook 架构范围的调度域事件共 11 个：

- 既有事件：`before_exec`、`after_exec`、`fail`、`guard_block`、`wait_approval`
- 第一批扩展事件：`before_schema`、`after_schema`、`before_guard`、`after_healing`、`retry_started`、`after_reflect`

`approval_resolved` 属于第二批审批域事件，当前仅保留架构边界，不纳入本批正式接口范围。

## 设计原则 (Design Principles)

1. **松耦合**：核心引擎只发布事件，不直接依赖外部处理器。
2. **极小内核**：新增能力以补充事件模型和 emit 点为主，不把业务策略塞入 `CoreScheduler`。
3. **同步分发**：当前阶段继续使用同步分发，保持实现简单、行为可预测、易于测试。
4. **订阅者隔离**：单个订阅者异常不得影响主流程和其他订阅者。
5. **向后兼容优先**：既有 5 个事件的名称、触发时机、订阅方式保持不变。
6. **事件数量受控**：只引入当前明确需要的事件，不补充未被需求驱动的对称事件。
7. **调度域与审批域分层**：`wait_approval` 表示调度链被 Guard 暂停；审批终态通知由第二批单独处理，不在本批混入恢复执行逻辑。

## 系统架构 (Architecture)

```text
┌─────────────────────────────────────────────────────────────┐
│                      Hook System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                HookManager (事件管理器)              │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  - subscribe(event_type, handler)                    │  │
│  │  - unsubscribe(event_type, handler)                  │  │
│  │  - emit(event)                                       │  │
│  │  - clear_subscribers(event_type)                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                        ↓                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Event Dispatcher (同步分发)             │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  - 复制订阅者列表后分发                              │  │
│  │  - 捕获订阅者异常，不中断主流程                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                        ↓                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               Subscribers (外部订阅者)               │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  - Logging                                            │  │
│  │  - Metrics                                            │  │
│  │  - Alerting                                           │  │
│  │  - Approval Notification                              │  │
│  │  - Audit / Trace                                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         ↑                                           ↑
   CoreScheduler                             External Systems
   (事件发布者)                              (事件消费者)
```

## 接口规格 (Interface Specification)

### 1. HookManager

**职责：**

- 管理合法事件类型与订阅关系
- 对指定事件类型执行订阅 / 取消订阅
- 同步向所有订阅者广播事件
- 捕获并记录订阅者异常
- 在多线程环境中保持内部状态一致

**正式事件类型（第一批同步后）：**

```python
VALID_EVENT_TYPES = {
    "before_schema",
    "after_schema",
    "before_guard",
    "before_exec",
    "after_exec",
    "fail",
    "after_healing",
    "retry_started",
    "after_reflect",
    "guard_block",
    "wait_approval",
}
```

**内部订阅表结构：**

```python
self._subscribers: Dict[str, List[HookHandler]] = {
    event_type: [] for event_type in VALID_EVENT_TYPES
}
```

**核心接口：**

```python
class HookManager:
    def subscribe(self, event_type: str, handler: HookHandler) -> None:
        """Subscribe to a hook event."""

    def unsubscribe(self, event_type: str, handler: HookHandler) -> None:
        """Unsubscribe from a hook event."""

    def emit(self, event: HookEvent) -> None:
        """Emit a hook event to all subscribers."""

    def clear_subscribers(self, event_type: Optional[str] = None) -> None:
        """Clear subscribers for one event type or all event types."""

    def get_subscriber_count(self, event_type: str) -> int:
        """Get subscriber count for an event type."""
```

### 2. 事件域边界

#### 2.1 调度域事件

以下事件都由 `CoreScheduler` 驱动，属于工具调度生命周期的一部分：

- `before_schema`
- `after_schema`
- `before_guard`
- `before_exec`
- `after_exec`
- `fail`
- `after_healing`
- `retry_started`
- `after_reflect`
- `guard_block`
- `wait_approval`

#### 2.2 审批域事件（第二批预留）

审批状态从 `PENDING` 进入终态后的通知事件 `approval_resolved` 不在本批接口内。其职责是表达“审批状态完成”，而不是表达“调度继续执行”。

### 3. Event Dispatcher

```python
def emit(self, event: HookEvent) -> None:
    """Emit event to all subscribers."""
    event_type = event.event_type

    with self._lock:
        subscribers = self._subscribers.get(event_type, []).copy()

    for handler in subscribers:
        try:
            handler(event)
        except Exception as exc:
            self._logger.error(
                f"Hook handler error for {event_type}: {exc}",
                exc_info=True,
                extra={
                    "event_type": event_type,
                    "execution_id": getattr(event, "execution_id", None),
                    "handler": getattr(handler, "__name__", repr(handler)),
                },
            )
```

**关键特性：**

1. **线程安全**：读取订阅者时短暂持锁，随后在锁外分发。
2. **异常隔离**：任何单个订阅者失败都不会中断其他订阅者或主流程。
3. **同步执行**：事件顺序与调度顺序保持一致，便于精确断言。
4. **低侵入性**：仅引入常量级判断与事件对象构造开销。

### 4. CoreScheduler 集成点

```python
class CoreScheduler:
    def _execute_plugin_chain(self, context, tool):
        previous_results = {}

        # 1. Schema layer
        schema_plugin = self.plugin_pool.get_plugin("schema", context.tool_id)
        if schema_plugin:
            self.hook_manager.emit(BeforeSchemaEvent(...))
            result = self._execute_plugin(schema_plugin, context, previous_results, tool)
            self.hook_manager.emit(AfterSchemaEvent(...))

            if not result.should_continue:
                self.hook_manager.emit(FailEvent(..., failed_stage="schema"))
                return context

        # 2. Guard layer
        guard_plugin = self.plugin_pool.get_plugin("guard", context.tool_id)
        if guard_plugin:
            self.hook_manager.emit(BeforeGuardEvent(...))
            result = self._execute_plugin(guard_plugin, context, previous_results, tool)

            if result.data and result.data.get("pending_approval"):
                self.hook_manager.emit(WaitApprovalEvent(...))
                return context

            if not result.should_continue:
                self.hook_manager.emit(GuardBlockEvent(...))
                return context

        # 3. Tool execute
        self.hook_manager.emit(BeforeExecEvent(...))

        for attempt in range(max_attempts):
            try:
                final_result = tool.execute_func(context.params)
                self.hook_manager.emit(AfterExecEvent(...))
                break
            except Exception as exc:
                self.hook_manager.emit(FailEvent(..., failed_stage="execute"))

                if healing_plugin and attempt < max_attempts - 1:
                    healing_result = self._execute_plugin(
                        healing_plugin, context, previous_results, tool
                    )
                    self.hook_manager.emit(AfterHealingEvent(...))

                    if healing_result.data and healing_result.data.get("recovered"):
                        self.hook_manager.emit(RetryStartedEvent(...))
                        continue

                return context

        # 4. Reflect layer
        reflect_plugin = self.plugin_pool.get_plugin("reflect", context.tool_id)
        if reflect_plugin:
            result = self._execute_plugin(reflect_plugin, context, previous_results, tool)
            self.hook_manager.emit(AfterReflectEvent(...))

        return context
```

**触发规则：**

1. `before_schema` / `after_schema` 仅在 Schema 插件真实执行时触发。
2. `after_schema` 无论校验通过还是失败都必须触发一次。
3. `before_guard` 仅在 Guard 插件真实执行时触发。
4. `after_healing` 仅在工具执行失败且 Healing 插件真实执行时触发。
5. `retry_started` 仅在 Healing 明确给出“可恢复并继续下一次尝试”时触发。
6. `after_reflect` 仅在 Reflect 插件真实执行时触发。
7. `wait_approval` 与 `guard_block` 仍维持原有语义，不因新增细粒度事件而改变。

## 流程与状态 (Workflow & State Machines)

### 1. 正常成功流程

```text
before_schema
  -> schema execute
  -> after_schema
      -> before_guard
          -> guard execute
              -> before_exec
                  -> tool execute success
                      -> after_exec
                          -> reflect execute
                              -> after_reflect
                                  -> observe
                                      -> completed
```

### 2. Schema 失败流程

```text
before_schema
  -> schema execute
  -> after_schema(success=false, should_continue=false)
      -> fail(failed_stage=schema)
```

### 3. Healing 恢复与重试流程

```text
before_exec
  -> tool execute fail
      -> fail(failed_stage=execute)
          -> healing execute
              -> after_healing(recovered=true)
                  -> retry_started
                      -> next attempt
                          -> after_exec
                              -> after_reflect
```

### 4. Guard 拦截 / 审批流程

```text
before_guard
  -> guard execute
      -> guard_block
```

```text
before_guard
  -> guard execute
      -> wait_approval
          -> approval pending
```

### 5. 当前审批边界

第一批只覆盖调度链中的 `wait_approval` 观测点；审批从 `PENDING` 进入 `APPROVED` / `REJECTED` / `TIMEOUT` 的终态通知由第二批 `approval_resolved` 单独补充，且不在本批引入“审批通过后自动恢复执行”的链路。

## 非功能要求 (Non-Functional Requirements)

### 1. 兼容性

1. 既有 5 个事件名称、订阅方式、触发语义保持兼容。
2. 未订阅新增事件时，现有业务行为不受影响。
3. 旧订阅者无需改代码即可继续工作。

### 2. 性能

1. 新增 Hook 仅允许引入常量级额外判断和对象构造开销。
2. 不允许为了 Hook 扩展引入网络 I/O、持久化 I/O 或异步队列。
3. 订阅者应快速返回，避免长期阻塞主流程。

### 3. 可靠性

1. 订阅者异常必须被隔离并记录日志。
2. `after_schema`、`after_healing`、`after_reflect` 的触发条件必须可预测、可测试。
3. `retry_started` 的 `attempt` / `next_attempt` 编号必须稳定可断言。

### 4. 可追踪性

1. 所有调度域事件必须携带相同的 `execution_id`。
2. `wait_approval` 必须携带 `approval_id`。
3. 事件顺序必须能被单元测试和集成测试稳定断言。

## 测试策略 (Testing Strategy)

### 单元测试

1. **HookManager**
   - 新事件可订阅 / 取消订阅 / 计数
   - 非法事件类型仍被拒绝

2. **CoreScheduler**
   - 有 Schema 插件时触发 `before_schema` → `after_schema`
   - Schema 失败时仍触发 `after_schema`，随后触发 `fail`
   - 有 Guard 插件时触发 `before_guard`
   - Healing 成功恢复时触发 `after_healing` 与 `retry_started`
   - Reflect 执行后触发 `after_reflect`

3. **SlotAgent**
   - 新增便利订阅接口正确注册到相应 `event_type`

### 集成测试

1. 成功流程包含：`before_schema`、`after_schema`、`before_guard`、`before_exec`、`after_exec`、`after_reflect`
2. 重试流程包含：`fail`、`after_healing`、`retry_started`
3. Guard 审批 / 拦截分支不因本批新增事件而回归

## 设计决策 (Design Decisions)

### D1: 继续保持同步分发
- **决策**：当前阶段继续采用同步分发。
- **理由**：行为简单、顺序稳定、测试断言直接。

### D2: 受控扩展而非对称扩张
- **决策**：仅增加用户明确需要的 6 个细粒度调度事件。
- **理由**：避免 `after_guard`、`before_healing`、`before_reflect` 等未被需求驱动的事件扩张。

### D3: 调度域与审批域分层
- **决策**：`wait_approval` 与未来的 `approval_resolved` 分开建模。
- **理由**：审批状态完成不等价于调度继续执行，避免职责混淆。

### D4: 向后兼容优先
- **决策**：旧事件不重命名、不改变原有语义。
- **理由**：保护已有订阅者与测试基线。

## 变更历史 (Changelog)

- **1.1** (2026-03-27): 同步第一批细粒度 Hook 正式规格，新增 6 个调度阶段事件与对应流程约束。
- **1.0** (2026-03-22): 初始版本，定义 Hook 系统架构和 HookManager 接口。
