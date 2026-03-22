# Core Scheduler - 核心调度引擎设计

**文档版本:** 1.0
**最后更新:** 2026-03-22
**状态:** Approved

---

## 1. 概述

CoreScheduler 是 SlotAgent 的核心调度引擎,负责插件链执行、事件分发和状态管理。

### 1.1 设计目标

- **极小内核**: 只负责调度,不含业务逻辑
- **事件驱动**: 通过 Hook 事件支持外部可观测
- **状态安全**: 正确管理执行状态转移
- **双模式兼容**: 既可独立运行,也可嵌入 LangGraph

### 1.2 核心职责

- 插件链执行编排
- Hook 事件分发
- 执行状态管理
- 审批流程协调

---

## 2. 架构设计

### 2.1 核心组件

```python
class CoreScheduler:
    """核心调度引擎"""

    def __init__(self):
        self.plugin_pool: PluginPool  # 插件池
        self.tool_registry: ToolRegistry  # 工具注册中心
        self.hook_manager: HookManager  # Hook 管理器 (Phase 5)
        self.approval_manager: ApprovalManager  # 审批管理器 (Phase 6)

    # 执行接口
    def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext
    def run(self, user_query: str) -> ToolExecutionContext  # Phase 8
    def batch_run(self, tasks: List[Dict]) -> List[ToolExecutionContext]  # Phase 8

    # 审批接口
    def approve(self, approval_id: str) -> None  # Phase 6
    def reject(self, approval_id: str, reason: str) -> None  # Phase 6
```

### 2.2 依赖关系

```
CoreScheduler
├── PluginPool (管理插件)
├── ToolRegistry (管理工具)
├── HookManager (事件分发, Phase 5)
└── ApprovalManager (审批管理, Phase 6)
```

---

## 3. 核心方法设计

### 3.1 execute() - 直接执行工具

**签名:**
```python
def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
    """
    直接执行指定工具。

    Args:
        tool_id: 工具ID,必须已注册
        params: 工具参数,将通过 Schema 插件验证

    Returns:
        ToolExecutionContext: 执行上下文,包含状态和结果

    Raises:
        ToolNotFoundError: 工具不存在
        PluginExecutionError: 插件执行异常

    Contract:
        Precondition:
            - tool_id 不为空且已注册
            - params 不为 None (可以是空字典)

        Postcondition:
            - 返回值不为 None
            - context.status 为终态 (COMPLETED/FAILED/PENDING_APPROVAL)
            - 触发了相应的 Hook 事件

        Invariant:
            - 不修改全局状态 (除了 approval_manager)
            - 相同输入多次执行,行为一致 (幂等性,除非工具有副作用)
    """
```

**执行流程:**

```python
def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
    # 1. 验证工具存在
    tool = self.tool_registry.get_tool(tool_id)
    if not tool:
        raise ToolNotFoundError(f"Tool '{tool_id}' not found")

    # 2. 创建执行上下文
    context = ToolExecutionContext(
        tool_id=tool_id,
        tool_name=tool.name,
        params=params,
        execution_id=str(uuid.uuid4()),
        status=ExecutionStatus.RUNNING,
        start_time=time.time()
    )

    # 3. 触发 before Hook
    self.hook_manager.emit('on_before_exec', context)

    try:
        # 4. 执行插件链
        context = self._execute_plugin_chain(context, tool)

        # 5. 根据状态触发 Hook
        if context.status == ExecutionStatus.COMPLETED:
            self.hook_manager.emit('on_after_exec', context)
        elif context.status == ExecutionStatus.FAILED:
            self.hook_manager.emit('on_fail', context)
        elif context.status == ExecutionStatus.PENDING_APPROVAL:
            self.hook_manager.emit('on_wait_approval', context)

    except Exception as e:
        context.status = ExecutionStatus.FAILED
        context.error = str(e)
        self.hook_manager.emit('on_fail', context)

    finally:
        # 6. 记录执行时间
        context.end_time = time.time()
        context.execution_time = context.end_time - context.start_time

    return context
```

### 3.2 _execute_plugin_chain() - 插件链执行 (核心逻辑)

**签名:**
```python
def _execute_plugin_chain(
    self,
    context: ToolExecutionContext,
    tool: ToolInterface
) -> ToolExecutionContext:
    """
    执行完整插件链。

    插件执行顺序: Schema → Guard → [Tool Execution] → Healing → Reflect → Observe
    """
```

**详细流程:**

```python
def _execute_plugin_chain(self, context: ToolExecutionContext, tool: ToolInterface) -> ToolExecutionContext:
    previous_results = {}

    # 1. Schema 层
    schema_plugin = self.plugin_pool.get_plugin('schema', context.tool_id)
    if schema_plugin:
        result = self._execute_plugin(schema_plugin, context, previous_results)
        context.plugin_results['schema'] = result
        previous_results['schema'] = result.data

        if not result.should_continue:
            context.status = ExecutionStatus.FAILED
            context.error = result.error
            return context

    # 2. Guard 层
    guard_plugin = self.plugin_pool.get_plugin('guard', context.tool_id)
    if guard_plugin:
        result = self._execute_plugin(guard_plugin, context, previous_results)
        context.plugin_results['guard'] = result
        previous_results['guard'] = result.data

        if not result.should_continue:
            # 检查是否需要审批
            if result.data and result.data.get('pending_approval'):
                context.status = ExecutionStatus.PENDING_APPROVAL
                context.approval_id = result.data['approval_id']
                # 注册到 ApprovalManager
                self.approval_manager.register(context.approval_id, context)
            else:
                # Guard 拦截
                context.status = ExecutionStatus.FAILED
                context.error = result.data.get('reason', 'Blocked by guard')
                self.hook_manager.emit('on_guard_block', context)

            return context

    # 3. 执行工具
    try:
        final_result = tool.execute(context.params)
        context.final_result = final_result

    except Exception as e:
        # 4. Healing 层 (工具执行失败时)
        healing_plugin = self.plugin_pool.get_plugin('healing', context.tool_id)
        if healing_plugin:
            healing_context = self._create_plugin_context(
                context, 'healing', previous_results, error=str(e)
            )
            result = healing_plugin.execute(healing_context)
            context.plugin_results['healing'] = result

            if result.success and result.data.get('recovered'):
                context.final_result = result.data.get('result')
            else:
                context.status = ExecutionStatus.FAILED
                context.error = str(e)
                return context
        else:
            context.status = ExecutionStatus.FAILED
            context.error = str(e)
            return context

    # 5. Reflect 层 (工具执行成功后)
    reflect_plugin = self.plugin_pool.get_plugin('reflect', context.tool_id)
    if reflect_plugin:
        reflect_context = self._create_plugin_context(
            context, 'reflect', previous_results, tool_result=context.final_result
        )
        result = reflect_plugin.execute(reflect_context)
        context.plugin_results['reflect'] = result
        previous_results['reflect'] = result.data

    # 6. Observe 层 (贯穿全流程,可异步)
    observe_plugin = self.plugin_pool.get_plugin('observe', context.tool_id)
    if observe_plugin:
        observe_context = self._create_plugin_context(
            context, 'observe', previous_results, full_context=context
        )
        result = observe_plugin.execute(observe_context)
        context.plugin_results['observe'] = result

    # 7. 标记成功
    context.status = ExecutionStatus.COMPLETED

    return context
```

### 3.3 _execute_plugin() - 单个插件执行

```python
def _execute_plugin(
    self,
    plugin: PluginInterface,
    context: ToolExecutionContext,
    previous_results: Dict[str, Any]
) -> PluginResult:
    """
    执行单个插件。

    Args:
        plugin: 插件实例
        context: 工具执行上下文
        previous_results: 前序插件结果

    Returns:
        PluginResult: 插件执行结果
    """

    # 创建插件上下文
    plugin_context = PluginContext(
        tool_id=context.tool_id,
        tool_name=context.tool_name,
        params=context.params,
        layer=plugin.layer,
        execution_id=context.execution_id,
        timestamp=time.time(),
        previous_results=previous_results
    )

    # 执行插件
    start_time = time.time()
    result = plugin.execute(plugin_context)
    execution_time = time.time() - start_time

    # 记录执行时间
    if result.execution_time is None:
        result.execution_time = execution_time

    return result
```

---

## 4. 状态管理

### 4.1 ExecutionStatus 状态机

```
                ┌─────────┐
                │ RUNNING │ (初始状态)
                └────┬────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        v            v            v
   ┌─────────┐  ┌──────┐   ┌──────────────┐
   │ FAILED  │  │COMPL │   │PENDING_APPR  │
   │         │  │ETED  │   │OVAL          │
   └─────────┘  └──────┘   └───────┬──────┘
   (终态)       (终态)             │
                              ┌────┴────┐
                              │ approve │
                              │ /reject │
                              └────┬────┘
                                   │
                            ┌──────┴──────┐
                            v              v
                       ┌─────────┐    ┌──────────┐
                       │ RUNNING │    │ FAILED   │
                       └─────────┘    └──────────┘
```

### 4.2 状态转移规则

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|---------|---------|---------|------|
| RUNNING | 插件成功,工具成功 | COMPLETED | 正常完成 |
| RUNNING | 插件失败/工具失败 | FAILED | 执行失败 |
| RUNNING | Guard 需要审批 | PENDING_APPROVAL | 等待审批 |
| PENDING_APPROVAL | approve() | RUNNING | 审批通过,继续执行 |
| PENDING_APPROVAL | reject() | FAILED | 审批拒绝,终止执行 |

### 4.3 状态一致性保证

```python
# 状态检查 - 确保终态不可变
def _ensure_terminal_state(self, context: ToolExecutionContext):
    terminal_states = {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED
    }

    if context.status in terminal_states:
        # 终态不可修改
        raise ValueError(f"Cannot modify terminal state: {context.status}")
```

---

## 5. Hook 事件系统 (Phase 5)

### 5.1 事件类型

| Hook 名称 | 触发时机 | 携带数据 |
|----------|---------|--------|
| `on_before_exec` | 工具执行前 | tool_id, tool_name, params |
| `on_after_exec` | 工具执行成功后 | tool_id, final_result, execution_time |
| `on_fail` | 工具执行失败 | tool_id, error, plugin_results |
| `on_guard_block` | Guard 拦截 | tool_id, reason, block_rule |
| `on_wait_approval` | 等待审批 | approval_id, tool_id, params |

### 5.2 事件分发

```python
# Hook 管理器接口 (Phase 5 实现)
class HookManager:
    def emit(self, event_name: str, data: Any) -> None:
        """发送 Hook 事件"""
        pass

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """订阅 Hook 事件"""
        pass
```

---

## 6. 审批流程协调 (Phase 6)

### 6.1 审批流程

```
工具执行 → Guard 插件拦截 → 生成 approval_id
                           ↓
                   状态 = PENDING_APPROVAL
                           ↓
                   触发 on_wait_approval Hook
                           ↓
                   外部系统处理审批
                           ↓
                   调用 approve() 或 reject()
                           ↓
             ┌─────────────┴─────────────┐
             v                           v
        approve()                    reject()
             ↓                           ↓
        恢复执行                      终止执行
             ↓                           ↓
        status = RUNNING            status = FAILED
```

### 6.2 审批接口

```python
def approve(self, approval_id: str) -> None:
    """
    审批通过,继续执行。

    Args:
        approval_id: 审批ID

    Raises:
        ValueError: approval_id 不存在或状态非法
    """

    context = self.approval_manager.get(approval_id)
    if not context:
        raise ValueError(f"Approval '{approval_id}' not found")

    if context.status != ExecutionStatus.PENDING_APPROVAL:
        raise ValueError(f"Invalid status: {context.status}")

    # 恢复执行
    context.status = ExecutionStatus.RUNNING
    context = self._execute_plugin_chain(context, tool)

    # 触发 Hook
    self.hook_manager.emit('on_approve', context)


def reject(self, approval_id: str, reason: str) -> None:
    """
    审批拒绝,终止执行。

    Args:
        approval_id: 审批ID
        reason: 拒绝原因
    """

    context = self.approval_manager.get(approval_id)
    if not context:
        raise ValueError(f"Approval '{approval_id}' not found")

    # 终止执行
    context.status = ExecutionStatus.FAILED
    context.error = f"Approval rejected: {reason}"
    context.end_time = time.time()
    context.execution_time = context.end_time - context.start_time

    # 触发 Hook
    self.hook_manager.emit('on_reject', context)
```

---

## 7. 使用模式

### 7.1 独立模式

```python
# 初始化
scheduler = CoreScheduler()

# 注册插件和工具
scheduler.plugin_pool.register_global_plugin(SchemaDefault())
scheduler.tool_registry.register(weather_tool)

# 执行工具
context = scheduler.execute('weather_query', {'location': 'Beijing'})

if context.status == ExecutionStatus.COMPLETED:
    print(context.final_result)
elif context.status == ExecutionStatus.PENDING_APPROVAL:
    print(f"Waiting for approval: {context.approval_id}")
else:
    print(f"Failed: {context.error}")
```

### 7.2 嵌入 LangGraph 模式 (Phase 8)

```python
from langgraph import Graph

# SlotAgent 作为 LangGraph 节点
def slotagent_node(state):
    context = scheduler.execute(state['tool_id'], state['params'])
    return {'result': context.final_result, 'status': context.status}

# 构建 LangGraph
graph = Graph()
graph.add_node('tool_execution', slotagent_node)
graph.add_edge('start', 'tool_execution')
```

---

## 8. 性能优化

### 8.1 异步执行 (可选)

Observe 层可异步执行,不阻塞主流程:

```python
# 异步执行 Observe 插件
import asyncio

async def _execute_observe_async(self, plugin, context, previous_results):
    # 异步执行观测插件
    pass
```

### 8.2 插件缓存

缓存已验证的参数,避免重复验证:

```python
# Schema 插件缓存 (可选)
from functools import lru_cache

@lru_cache(maxsize=1000)
def _validate_params_cached(self, params_hash, schema):
    # 缓存验证结果
    pass
```

---

## 9. 错误处理

### 9.1 异常传播

- 插件异常: 捕获并转为 `PluginExecutionError`
- 工具异常: 尝试 Healing,失败则转为 `ToolExecutionError`
- 系统异常: 记录日志,返回 FAILED 状态

### 9.2 错误恢复

- Healing 插件负责错误恢复
- CoreScheduler 不直接处理业务逻辑

---

## 10. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|--------|
| 1.0 | 2026-03-22 | 初始版本,定义核心调度流程和状态管理 |

---

**审批状态:** ✅ Approved
**审批人:** SlotAgent Core Team
**审批日期:** 2026-03-22
