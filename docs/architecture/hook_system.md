# Hook System Architecture

## 概述 (Overview)

Hook 系统是 SlotAgent 实现可观测性的核心机制。通过发布-订阅模式，Hook 系统允许外部系统订阅工具执行生命周期中的关键事件，从而实现监控、日志、审批、告警等功能，同时保持核心引擎的轻量和无耦合。

## 设计原则

1. **松耦合**: 核心引擎只负责发布事件，不关心订阅者
2. **异步非阻塞**: 事件处理不阻塞主流程（Phase 5 先实现同步，Phase 6+ 优化为异步）
3. **订阅者隔离**: 订阅者异常不影响主流程和其他订阅者
4. **线程安全**: 支持多线程环境下的订阅和发布

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Hook System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │           HookManager (Hook管理器)               │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  - subscribe(event_type, handler)                │      │
│  │  - unsubscribe(event_type, handler)              │      │
│  │  - emit(event)                                   │      │
│  │  - clear_subscribers(event_type)                 │      │
│  └──────────────────────────────────────────────────┘      │
│                      ↓                                      │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Event Dispatcher (事件分发器)            │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  同步分发事件到所有订阅者                        │      │
│  │  捕获订阅者异常，不影响主流程                    │      │
│  └──────────────────────────────────────────────────┘      │
│                      ↓                                      │
│  ┌──────────────────────────────────────────────────┐      │
│  │        Subscribers (订阅者/处理器)               │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  - Logging Handler: 记录日志                     │      │
│  │  - Metrics Handler: 更新监控指标                 │      │
│  │  - Alert Handler: 发送告警                       │      │
│  │  - Approval Handler: 触发审批流程                │      │
│  │  - IM Notification: 发送 IM 通知                 │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         ↑                                           ↑
   CoreScheduler                             External Systems
   (事件发布者)                              (事件消费者)
```

## 核心组件

### 1. HookManager (Hook管理器)

**职责**:
- 管理事件订阅关系
- 分发事件到订阅者
- 处理订阅者异常
- 保证线程安全

**核心接口**:

```python
from typing import Callable, Dict, List
import threading
import logging

HookHandler = Callable[[HookEvent], None]

class HookManager:
    """
    Hook manager for event subscription and dispatching.

    Thread-safe implementation using locks.
    """

    def __init__(self):
        """Initialize HookManager."""
        self._subscribers: Dict[str, List[HookHandler]] = {
            'before_exec': [],
            'after_exec': [],
            'fail': [],
            'guard_block': [],
            'wait_approval': []
        }
        self._lock = threading.Lock()
        self._logger = logging.getLogger('slotagent.hooks')

    def subscribe(
        self,
        event_type: str,
        handler: HookHandler
    ) -> None:
        """
        Subscribe to a hook event.

        Args:
            event_type: Event type to subscribe
            handler: Callable that handles the event

        Raises:
            ValueError: If event_type is invalid
        """
        pass

    def unsubscribe(
        self,
        event_type: str,
        handler: HookHandler
    ) -> None:
        """
        Unsubscribe from a hook event.

        Args:
            event_type: Event type to unsubscribe
            handler: Handler to remove

        Raises:
            ValueError: If event_type is invalid
        """
        pass

    def emit(self, event: HookEvent) -> None:
        """
        Emit a hook event to all subscribers.

        Args:
            event: Hook event to emit

        Notes:
            - Calls all subscribers synchronously
            - Catches and logs subscriber exceptions
            - Does not re-raise exceptions (non-blocking)
        """
        pass

    def clear_subscribers(self, event_type: Optional[str] = None) -> None:
        """
        Clear all subscribers for an event type (or all events).

        Args:
            event_type: Event type to clear (None = all)
        """
        pass

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get number of subscribers for an event type.

        Args:
            event_type: Event type

        Returns:
            Number of subscribers
        """
        pass
```

### 2. Event Dispatcher (事件分发逻辑)

**实现细节**:

```python
def emit(self, event: HookEvent) -> None:
    """Emit event to all subscribers."""
    event_type = event.event_type

    # Get subscribers (thread-safe)
    with self._lock:
        subscribers = self._subscribers.get(event_type, []).copy()

    # Dispatch to each subscriber
    for handler in subscribers:
        try:
            handler(event)
        except Exception as e:
            # Log error but don't re-raise
            self._logger.error(
                f"Hook handler error for {event_type}: {e}",
                exc_info=True,
                extra={
                    "event_type": event_type,
                    "execution_id": getattr(event, 'execution_id', None),
                    "handler": handler.__name__
                }
            )
```

**关键特性**:
1. **线程安全**: 复制订阅者列表，避免迭代时修改
2. **异常隔离**: 捕获单个订阅者异常，不影响其他订阅者
3. **同步执行**: Phase 5 使用同步调用，简单可靠
4. **日志记录**: 记录所有异常，便于调试

### 3. CoreScheduler 集成

**事件触发点**:

```python
class CoreScheduler:
    def __init__(self, plugin_pool, tool_registry, hook_manager=None):
        self.plugin_pool = plugin_pool
        self.tool_registry = tool_registry
        self.hook_manager = hook_manager or HookManager()

    def _execute_plugin_chain(self, context, tool):
        previous_results = {}

        # 1. Schema layer
        schema_plugin = self.plugin_pool.get_plugin('schema', context.tool_id)
        if schema_plugin:
            result = self._execute_plugin(schema_plugin, context, previous_results)
            context.plugin_results['schema'] = result
            previous_results['schema'] = result.data

            if not result.should_continue:
                context.status = ExecutionStatus.FAILED
                context.error = result.error
                # Emit fail event
                self.hook_manager.emit(FailEvent(
                    execution_id=context.execution_id,
                    tool_id=context.tool_id,
                    tool_name=context.tool_name,
                    timestamp=time.time(),
                    params=context.params,
                    error=result.error,
                    error_type=result.error_type or "ValidationError",
                    failed_stage="schema"
                ))
                return context

        # 2. Guard layer
        guard_plugin = self.plugin_pool.get_plugin('guard', context.tool_id)
        if guard_plugin:
            result = self._execute_plugin(guard_plugin, context, previous_results)
            context.plugin_results['guard'] = result
            previous_results['guard'] = result.data

            if not result.should_continue:
                # Check if pending approval
                if result.data and result.data.get('pending_approval'):
                    context.status = ExecutionStatus.PENDING_APPROVAL
                    context.approval_id = result.data.get('approval_id')
                    # Emit wait_approval event
                    self.hook_manager.emit(WaitApprovalEvent(
                        execution_id=context.execution_id,
                        tool_id=context.tool_id,
                        tool_name=context.tool_name,
                        timestamp=time.time(),
                        params=context.params,
                        approval_id=context.approval_id,
                        approval_context=result.data.get('approval_context')
                    ))
                else:
                    # Guard blocked
                    context.status = ExecutionStatus.FAILED
                    context.error = result.data.get('reason', 'Blocked by guard')
                    # Emit guard_block event
                    self.hook_manager.emit(GuardBlockEvent(
                        execution_id=context.execution_id,
                        tool_id=context.tool_id,
                        tool_name=context.tool_name,
                        timestamp=time.time(),
                        params=context.params,
                        reason=context.error,
                        guard_plugin_id=guard_plugin.plugin_id
                    ))

                return context

        # Emit before_exec event
        self.hook_manager.emit(BeforeExecEvent(
            execution_id=context.execution_id,
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            timestamp=time.time(),
            params=context.params
        ))

        # 3. Execute tool
        try:
            final_result = tool.execute_func(context.params)
            context.final_result = final_result

            # Emit after_exec event
            self.hook_manager.emit(AfterExecEvent(
                execution_id=context.execution_id,
                tool_id=context.tool_id,
                tool_name=context.tool_name,
                timestamp=time.time(),
                params=context.params,
                result=final_result,
                execution_time=time.time() - context.start_time
            ))

        except Exception as e:
            # Tool execution failed
            context.status = ExecutionStatus.FAILED
            context.error = f"Tool execution failed: {str(e)}"
            # Emit fail event
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
            return context

        # 4. Reflect and Observe layers (unchanged)
        # ...

        context.status = ExecutionStatus.COMPLETED
        return context
```

## 使用场景

### 场景1: 日志记录

```python
def log_handler(event: HookEvent):
    """Log all events."""
    logger.info(
        f"[{event.event_type}] {event.tool_id}",
        extra={
            "execution_id": event.execution_id,
            "timestamp": event.timestamp
        }
    )

hook_manager.subscribe('before_exec', log_handler)
hook_manager.subscribe('after_exec', log_handler)
hook_manager.subscribe('fail', log_handler)
```

### 场景2: Prometheus 监控

```python
from prometheus_client import Counter, Histogram

tool_executions = Counter('tool_executions_total', 'Total tool executions', ['tool_id', 'status'])
tool_duration = Histogram('tool_execution_seconds', 'Tool execution duration', ['tool_id'])

def metrics_handler(event: HookEvent):
    """Update Prometheus metrics."""
    if isinstance(event, AfterExecEvent):
        tool_executions.labels(tool_id=event.tool_id, status='success').inc()
        tool_duration.labels(tool_id=event.tool_id).observe(event.execution_time)
    elif isinstance(event, FailEvent):
        tool_executions.labels(tool_id=event.tool_id, status='failed').inc()

hook_manager.subscribe('after_exec', metrics_handler)
hook_manager.subscribe('fail', metrics_handler)
```

### 场景3: IM 通知（审批）

```python
def approval_notification_handler(event: WaitApprovalEvent):
    """Send approval notification to IM."""
    message = (
        f"⚠️ Approval Required\n"
        f"Tool: {event.tool_name}\n"
        f"Execution ID: {event.execution_id}\n"
        f"Approval ID: {event.approval_id}\n"
        f"[Approve] [Reject]"
    )

    send_im_message(
        channel='#approvals',
        message=message,
        buttons=[
            {'label': 'Approve', 'action': f'approve:{event.approval_id}'},
            {'label': 'Reject', 'action': f'reject:{event.approval_id}'}
        ]
    )

hook_manager.subscribe('wait_approval', approval_notification_handler)
```

## 设计决策

### D1: 同步 vs 异步事件分发
- **Phase 5 决策**: 同步分发
- **理由**:
  - 简单可靠，易于测试
  - 大多数订阅者处理很快（日志、指标）
  - 避免异步复杂性
- **未来优化**: Phase 6+ 可考虑异步队列

### D2: 订阅者异常处理
- **决策**: 捕获异常，记录日志，不re-raise
- **理由**:
  - 订阅者错误不应影响主流程
  - 订阅者之间应隔离
  - 便于调试（日志记录）

### D3: 线程安全策略
- **决策**: 使用 threading.Lock 保护订阅者字典
- **理由**:
  - 简单有效
  - Python GIL 下性能足够
  - 避免复杂的无锁数据结构

### D4: 事件不可变性
- **决策**: Phase 5 使用普通 dataclass（可变）
- **理由**: 简化实现，后续可优化为 frozen
- **权衡**: 订阅者可能意外修改事件，但通过文档约束

## 性能考虑

1. **订阅者复制**: emit() 时复制订阅者列表，避免长时间持锁
2. **异常捕获开销**: 正常情况无异常，开销可忽略
3. **同步调用**: 订阅者应快速返回，避免阻塞主流程
4. **内存占用**: 事件对象短生命周期，GC 及时回收

## 测试策略

### 单元测试
1. **HookManager 测试**:
   - 订阅和取消订阅
   - 事件分发到多个订阅者
   - 订阅者异常隔离
   - 线程安全

2. **CoreScheduler 集成测试**:
   - 各事件在正确时机触发
   - 事件携带正确数据

### 集成测试
1. **完整流程测试**:
   - 正常流程: before_exec → after_exec
   - 失败流程: before_exec → fail
   - 审批流程: wait_approval → ...

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义 Hook 系统架构和 HookManager 接口
