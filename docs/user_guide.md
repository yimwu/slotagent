# SlotAgent 使用指南

**版本：** 0.1.0-alpha
**最后更新：** 2026-03-22

本指南帮助您快速上手 SlotAgent，并深入理解其核心概念和使用方法。

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基础用法](#基础用法)
4. [进阶功能](#进阶功能)
5. [最佳实践](#最佳实践)
6. [故障排查](#故障排查)

---

## 快速开始

### 安装

```bash
# 从源码安装（开发版本）
git clone https://github.com/yimwu/slotagent.git
cd slotagent
pip install -e .

# 或从 PyPI 安装（稳定版本 - 即将推出）
pip install slotagent
```

### 第一个工具

创建并执行一个简单的工具：

```python
from slotagent.core import CoreScheduler
from slotagent.types import Tool

# 1. 创建调度器
scheduler = CoreScheduler()

# 2. 定义工具
def echo_message(params):
    return {'echo': params.get('message', 'Hello')}

echo_tool = Tool(
    tool_id='echo',
    name='Echo Tool',
    description='Echo back the input message',
    input_schema={
        'type': 'object',
        'properties': {
            'message': {'type': 'string'}
        }
    },
    execute_func=echo_message
)

# 3. 注册并执行
scheduler.register_tool(echo_tool)
context = scheduler.execute('echo', {'message': 'Hello SlotAgent!'})

print(context.final_result)  # {'echo': 'Hello SlotAgent!'}
```

---

## 核心概念

### 1. 极小内核（Minimal Kernel）

SlotAgent 的核心调度引擎 (`CoreScheduler`) 只负责：
- 工具调度
- 插件链协调
- 事件分发
- 状态管理

**不包含任何业务逻辑**，所有功能都通过插件实现。

### 2. 五层插件系统

插件按照固定顺序执行，形成处理链：

```
Schema → Guard → [Tool Execution] → Healing → Reflect → Observe
```

| 层级 | 作用 | 典型插件 |
|------|------|----------|
| **Schema** | 参数验证 | SchemaDefault, SchemaStrict |
| **Guard** | 权限控制、审批 | GuardDefault, GuardHumanInLoop |
| **Healing** | 失败恢复 | HealingRetry（占位） |
| **Reflect** | 结果反思 | ReflectSimple（占位） |
| **Observe** | 可观测性 | LogPlugin |

### 3. 工具级插件配置

**全局插件 vs 工具级插件：**

- **全局插件**：应用于所有工具（默认行为）
- **工具级插件**：为特定工具覆盖全局配置

**优先级规则：** 工具级插件 > 全局插件

```python
# 全局配置：轻量验证
scheduler.plugin_pool.register_global_plugin(SchemaDefault(...))

# 高风险工具：严格验证 + 人工审批
payment_tool = Tool(
    tool_id='payment',
    plugins={
        'schema': 'schema_strict',      # 覆盖全局
        'guard': 'guard_human_in_loop'  # 覆盖全局
    },
    ...
)
```

### 4. Hook 事件系统

SlotAgent 通过 Hook 实现松耦合的可观测性：

**5 种核心事件：**
1. `before_exec` - 工具执行前
2. `after_exec` - 执行成功后
3. `fail` - 执行失败
4. `guard_block` - Guard 阻止执行
5. `wait_approval` - 等待人工审批

**外部系统订阅 Hook 事件：**
```python
from slotagent.core import HookManager

hook_manager = HookManager()

# 订阅事件
hook_manager.subscribe('before_exec', lambda e: print(f"Starting: {e.tool_id}"))
hook_manager.subscribe('fail', lambda e: send_alert(e.error))

scheduler = CoreScheduler(hook_manager=hook_manager)
```

### 5. 人工审批（Human-in-the-Loop）

高风险操作可以暂停执行，等待人工审批：

**审批状态机：**
```
PENDING → APPROVED
        ↘ REJECTED
        ↘ TIMEOUT
```

**完整审批流程：**
1. GuardHumanInLoop 插件触发审批请求
2. 执行状态变为 `PENDING_APPROVAL`
3. 触发 `wait_approval` Hook 事件
4. 外部系统通知审批人
5. 审批人调用 `approve()` 或 `reject()`
6. 审批结果记录在 ApprovalManager

---

## 基础用法

### 注册和执行工具

```python
from slotagent.core import CoreScheduler
from slotagent.types import Tool, ExecutionStatus

scheduler = CoreScheduler()

# 定义工具
calculator = Tool(
    tool_id='add',
    name='Add Numbers',
    description='Add two numbers together',
    input_schema={
        'type': 'object',
        'properties': {
            'a': {'type': 'number'},
            'b': {'type': 'number'}
        },
        'required': ['a', 'b']
    },
    execute_func=lambda p: {'result': p['a'] + p['b']}
)

# 注册工具
scheduler.register_tool(calculator)

# 执行工具
context = scheduler.execute('add', {'a': 10, 'b': 32})

# 检查结果
if context.status == ExecutionStatus.COMPLETED:
    print(f"Result: {context.final_result['result']}")  # 42
elif context.status == ExecutionStatus.FAILED:
    print(f"Error: {context.error}")
```

### 使用 Schema 验证

```python
from slotagent.plugins import SchemaDefault

# 定义验证规则
weather_schema = {
    'type': 'object',
    'properties': {
        'location': {'type': 'string'},
        'unit': {'type': 'string', 'enum': ['celsius', 'fahrenheit']}
    },
    'required': ['location']
}

# 注册全局 Schema 插件
scheduler.plugin_pool.register_global_plugin(
    SchemaDefault(schema=weather_schema)
)

# 工具定义
weather_tool = Tool(
    tool_id='weather',
    name='Weather Query',
    description='Get weather for a location',
    input_schema=weather_schema,
    execute_func=lambda p: {'temp': 25, 'location': p['location']}
)

scheduler.register_tool(weather_tool)

# 有效调用
context = scheduler.execute('weather', {'location': 'Beijing', 'unit': 'celsius'})
print(context.status)  # COMPLETED

# 无效调用（缺少 required 字段）
context = scheduler.execute('weather', {})
print(context.status)  # FAILED
print(context.error)   # "Required field 'location' is missing"
```

### 使用 Guard 控制访问

```python
from slotagent.plugins import GuardDefault

# 方式1：黑名单模式
guard = GuardDefault(blacklist=['dangerous_tool', 'deprecated_api'])
scheduler.plugin_pool.register_global_plugin(guard)

# 方式2：白名单模式
guard = GuardDefault(
    whitelist=['safe_tool_1', 'safe_tool_2'],
    whitelist_only=True  # 仅允许白名单工具
)
scheduler.plugin_pool.register_global_plugin(guard)

# 被阻止的工具
context = scheduler.execute('dangerous_tool', {})
print(context.status)  # FAILED
# guard_block Hook 事件会被触发
```

### 监听 Hook 事件

```python
from slotagent.core import HookManager

hook_manager = HookManager()

# 定义事件处理器
def log_execution(event):
    print(f"[{event.event_type}] Tool: {event.tool_id}, Time: {event.timestamp}")

def handle_failure(event):
    print(f"[ERROR] Tool {event.tool_id} failed: {event.error}")
    # 发送告警、记录日志等

def handle_guard_block(event):
    print(f"[BLOCKED] Tool {event.tool_id} was blocked: {event.reason}")

# 订阅事件
hook_manager.subscribe('before_exec', log_execution)
hook_manager.subscribe('after_exec', log_execution)
hook_manager.subscribe('fail', handle_failure)
hook_manager.subscribe('guard_block', handle_guard_block)

# 使用自定义 HookManager
scheduler = CoreScheduler(hook_manager=hook_manager)
```

---

## 进阶功能

### 工具级插件配置

为不同工具配置不同的插件策略：

```python
from slotagent.plugins import SchemaDefault, SchemaStrict, GuardDefault, GuardHumanInLoop
from slotagent.core import ApprovalManager

# 1. 注册全局插件（默认策略）
scheduler.plugin_pool.register_global_plugin(SchemaDefault(...))
scheduler.plugin_pool.register_global_plugin(GuardDefault(...))

# 2. 注册额外插件供工具选择
scheduler.plugin_pool.register_global_plugin(SchemaStrict(...))

approval_manager = ApprovalManager()
scheduler.plugin_pool.register_global_plugin(
    GuardHumanInLoop(approval_manager=approval_manager)
)

# 3. 定义不同级别的工具

# 简单工具：使用全局插件（轻量验证 + 默认 Guard）
simple_tool = Tool(
    tool_id='echo',
    name='Echo',
    description='Simple echo tool',
    input_schema={...},
    execute_func=echo_func
    # 不指定 plugins，使用全局配置
)

# 高风险工具：覆盖为严格策略
payment_tool = Tool(
    tool_id='payment_refund',
    name='Payment Refund',
    description='Refund payment to customer',
    input_schema={...},
    execute_func=refund_func,
    plugins={
        'schema': 'schema_strict',           # 严格验证
        'guard': 'guard_human_in_loop'      # 人工审批
    }
)

scheduler.register_tool(simple_tool)
scheduler.register_tool(payment_tool)

# 执行简单工具：快速通过
scheduler.execute('echo', {...})

# 执行高风险工具：进入审批流程
context = scheduler.execute('payment_refund', {...})
# context.status == PENDING_APPROVAL
```

### 人工审批完整流程

```python
from slotagent.core import CoreScheduler, ApprovalManager, HookManager
from slotagent.plugins import GuardHumanInLoop
from slotagent.types import ExecutionStatus, ApprovalStatus

# 1. 创建组件
approval_manager = ApprovalManager(default_timeout=600.0)  # 10分钟超时
hook_manager = HookManager()
scheduler = CoreScheduler(hook_manager=hook_manager)

# 2. 订阅审批事件
approval_queue = []

def on_wait_approval(event):
    """当需要审批时，将请求加入队列"""
    approval_queue.append({
        'approval_id': event.approval_id,
        'tool_id': event.tool_id,
        'params': event.params
    })
    print(f"New approval request: {event.approval_id}")

    # 实际应用中：发送通知给审批人
    # send_email_to_approver(event.approval_id, event.tool_id, event.params)

hook_manager.subscribe('wait_approval', on_wait_approval)

# 3. 注册审批插件
scheduler.plugin_pool.register_global_plugin(
    GuardHumanInLoop(approval_manager=approval_manager)
)

# 4. 注册高风险工具
dangerous_tool = Tool(
    tool_id='delete_database',
    name='Delete Database',
    description='Delete entire database (dangerous)',
    input_schema={...},
    execute_func=delete_db_func
)
scheduler.register_tool(dangerous_tool)

# 5. 执行工具（触发审批）
context = scheduler.execute('delete_database', {'confirm': True})

assert context.status == ExecutionStatus.PENDING_APPROVAL
approval_id = context.approval_id

# 6. 审批人处理请求
print(f"Pending approvals: {len(approval_queue)}")

# 选择批准或拒绝
choice = input("Approve? (y/n): ")

if choice == 'y':
    record = approval_manager.approve(approval_id, approver='admin@company.com')
    print(f"Approved by: {record.approver}")
else:
    record = approval_manager.reject(
        approval_id,
        approver='admin@company.com',
        reason='Operation too risky'
    )
    print(f"Rejected: {record.reject_reason}")

# 7. 查询审批记录
final_record = approval_manager.get_approval(approval_id)
print(f"Final status: {final_record.status}")
```

### 超时管理

```python
import time

# 创建审批管理器，设置短超时用于演示
approval_manager = ApprovalManager(default_timeout=5.0)  # 5秒

# ... 注册插件、工具 ...

# 执行工具
context = scheduler.execute('risky_operation', {})
approval_id = context.approval_id

# 等待超时
time.sleep(6)

# 检查超时
expired_ids = approval_manager.check_timeouts()
print(f"Expired approvals: {expired_ids}")

# 查询记录
record = approval_manager.get_approval(approval_id)
print(f"Status: {record.status}")  # TIMEOUT
print(f"Reason: {record.reject_reason}")  # "Approval request timed out"
```

### 自定义插件开发

创建自定义 Guard 插件，实现基于用户角色的访问控制：

```python
from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

class GuardRBAC(PluginInterface):
    """基于角色的访问控制插件"""

    layer = 'guard'
    plugin_id = 'guard_rbac'

    def __init__(self, role_permissions: dict):
        """
        Args:
            role_permissions: {tool_id: [allowed_roles]}
        """
        self.role_permissions = role_permissions

    def validate(self) -> bool:
        """验证配置有效性"""
        return isinstance(self.role_permissions, dict)

    def execute(self, context: PluginContext) -> PluginResult:
        """检查用户角色是否有权限"""
        tool_id = context.tool_id

        # 从 metadata 获取用户角色
        user_role = context.metadata.get('user_role', 'guest')

        # 检查权限
        allowed_roles = self.role_permissions.get(tool_id, [])

        if user_role in allowed_roles:
            return PluginResult(
                success=True,
                data={'authorized': True, 'role': user_role}
            )
        else:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f"Role '{user_role}' not authorized for tool '{tool_id}'"
                }
            )

# 使用自定义插件
rbac_plugin = GuardRBAC(role_permissions={
    'payment_refund': ['admin', 'finance'],
    'view_report': ['admin', 'finance', 'analyst'],
    'delete_data': ['admin']
})

scheduler.plugin_pool.register_global_plugin(rbac_plugin)

# 执行时传递用户角色
context = scheduler.execute(
    'payment_refund',
    {'amount': 100},
    # 注意：当前版本需要通过其他方式传递 metadata
    # 可以在 Tool.execute_func 中访问并设置
)
```

---

## 最佳实践

### 1. 工具设计原则

✅ **好的工具设计：**
```python
# 单一职责：工具只做一件事
weather_tool = Tool(
    tool_id='weather_query',
    name='Weather Query',
    description='Get current weather for a specific location',
    input_schema={
        'type': 'object',
        'properties': {
            'location': {'type': 'string'},
            'unit': {'type': 'string', 'enum': ['celsius', 'fahrenheit']}
        },
        'required': ['location']
    },
    execute_func=get_weather
)

# 清晰的 schema：明确定义参数类型和约束
# 详细的描述：至少 10 个字符，说明工具功能
```

❌ **避免：**
```python
# 功能过于复杂：一个工具做多件事
multi_tool = Tool(
    tool_id='do_everything',
    name='Multi Tool',
    description='Does weather, payments, and more',  # 不清晰
    input_schema={'type': 'object'},  # 缺少 properties
    execute_func=lambda p: complex_logic(p)  # 逻辑过于复杂
)
```

### 2. 插件配置策略

**按风险级别分层配置：**

```python
# 低风险：轻量级验证，无审批
low_risk_tools = ['echo', 'view_status', 'query_info']

# 中风险：严格验证，无审批
medium_risk_tools = ['update_profile', 'send_notification']

# 高风险：严格验证 + 人工审批
high_risk_tools = ['payment_refund', 'delete_data', 'grant_permission']

# 全局插件（适用于低风险）
scheduler.plugin_pool.register_global_plugin(SchemaDefault(...))
scheduler.plugin_pool.register_global_plugin(GuardDefault(...))

# 高风险工具单独配置
for tool_id in high_risk_tools:
    tool = Tool(
        tool_id=tool_id,
        plugins={
            'schema': 'schema_strict',
            'guard': 'guard_human_in_loop'
        },
        ...
    )
    scheduler.register_tool(tool)
```

### 3. Hook 事件处理

**分离关注点：不同系统订阅不同事件**

```python
# 日志系统
def log_all_events(event):
    logger.info(f"Event: {event.event_type}, Tool: {event.tool_id}")

hook_manager.subscribe('before_exec', log_all_events)
hook_manager.subscribe('after_exec', log_all_events)
hook_manager.subscribe('fail', log_all_events)

# 监控系统
def send_metrics(event):
    metrics.increment(f'tool.{event.tool_id}.{event.event_type}')

hook_manager.subscribe('after_exec', send_metrics)
hook_manager.subscribe('fail', send_metrics)

# 告警系统
def send_alert_on_failure(event):
    if event.tool_id in critical_tools:
        alerting.send(f"Critical tool {event.tool_id} failed: {event.error}")

hook_manager.subscribe('fail', send_alert_on_failure)

# 审批通知系统
def notify_approver(event):
    approval_service.notify(event.approval_id, event.tool_id, event.params)

hook_manager.subscribe('wait_approval', notify_approver)
```

### 4. 错误处理

**优雅处理执行失败：**

```python
from slotagent.types import ExecutionStatus

context = scheduler.execute(tool_id, params)

if context.status == ExecutionStatus.COMPLETED:
    # 成功处理
    return context.final_result

elif context.status == ExecutionStatus.PENDING_APPROVAL:
    # 等待审批
    return {
        'status': 'pending',
        'approval_id': context.approval_id,
        'message': 'Waiting for approval'
    }

elif context.status == ExecutionStatus.FAILED:
    # 失败处理
    logger.error(f"Tool {tool_id} failed: {context.error}")

    # 根据错误类型决定重试或返回
    if 'timeout' in context.error.lower():
        # 可重试的错误
        return {'status': 'retry_later', 'error': context.error}
    else:
        # 不可重试的错误
        return {'status': 'failed', 'error': context.error}
```

### 5. 审批管理

**定期清理超时审批：**

```python
import threading
import time

def periodic_timeout_check(approval_manager, interval=60):
    """每隔一定时间检查超时审批"""
    while True:
        expired_ids = approval_manager.check_timeouts()

        for approval_id in expired_ids:
            record = approval_manager.get_approval(approval_id)
            logger.warning(f"Approval {approval_id} timed out for tool {record.tool_id}")

            # 可选：发送超时通知
            notify_timeout(record)

        time.sleep(interval)

# 在后台线程运行
cleanup_thread = threading.Thread(
    target=periodic_timeout_check,
    args=(approval_manager, 60),
    daemon=True
)
cleanup_thread.start()
```

---

## 故障排查

### 常见问题

#### 1. 工具未找到错误

**错误：**
```
ToolNotFoundError: Tool 'my_tool' not found
```

**解决方法：**
- 确认工具已注册：`scheduler.tool_registry.list_tools()`
- 检查 tool_id 拼写是否正确
- 确认工具在执行前已注册

#### 2. Schema 验证失败

**错误：**
```
ExecutionStatus.FAILED, error: "Required field 'location' is missing"
```

**解决方法：**
- 检查传入的 params 是否包含所有 required 字段
- 确认字段类型是否匹配 schema 定义
- 使用 `SchemaDefault` 而不是 `SchemaStrict` 降低验证严格度

#### 3. 插件配置错误

**错误：**
```
PluginConfigError: Plugin 'MyPlugin' must define 'layer' class attribute
```

**解决方法：**
- 确保自定义插件类定义了 `layer` 和 `plugin_id` **类属性**（不是实例属性）
- 继承自 `PluginInterface`
- 实现 `validate()` 和 `execute()` 方法

**正确示例：**
```python
class MyPlugin(PluginInterface):
    layer = 'guard'           # 类属性
    plugin_id = 'my_plugin'   # 类属性

    def validate(self):
        return True

    def execute(self, context):
        return PluginResult(success=True)
```

#### 4. 审批超时

**问题：** 审批请求超时，但没有收到通知

**解决方法：**
- 确认 `HookManager` 已正确订阅 `wait_approval` 事件
- 检查 `ApprovalManager.default_timeout` 是否足够长
- 定期调用 `approval_manager.check_timeouts()` 或在后台线程运行
- 确认审批通知逻辑正常工作

#### 5. Hook 事件未触发

**问题：** 订阅了 Hook 事件但处理器未被调用

**解决方法：**
- 确认 `CoreScheduler` 使用了正确的 `HookManager` 实例
- 检查事件类型拼写：`'before_exec'` 而不是 `'before_execute'`
- 确认插件成功注册并执行
- 检查处理器函数是否抛出异常（异常会被捕获但不影响主流程）

### 调试技巧

**1. 启用详细日志：**

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# LogPlugin 会输出详细执行信息
from slotagent.plugins import LogPlugin
scheduler.plugin_pool.register_global_plugin(LogPlugin())
```

**2. 检查执行上下文：**

```python
context = scheduler.execute('my_tool', params)

print(f"Status: {context.status}")
print(f"Error: {context.error}")
print(f"Execution time: {context.execution_time}")
print(f"Plugin results: {context.plugin_results}")
```

**3. 追踪插件执行：**

```python
def trace_plugin_execution(event):
    if hasattr(event, 'result'):
        print(f"[{event.event_type}] Tool: {event.tool_id}, Result: {event.result}")
    else:
        print(f"[{event.event_type}] Tool: {event.tool_id}")

hook_manager.subscribe('before_exec', trace_plugin_execution)
hook_manager.subscribe('after_exec', trace_plugin_execution)
hook_manager.subscribe('fail', trace_plugin_execution)
```

---

**文档版本：** 1.0
**维护者：** SlotAgent 核心团队
**反馈：** https://github.com/yimwu/slotagent/issues
