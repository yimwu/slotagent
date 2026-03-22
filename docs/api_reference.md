# SlotAgent API Reference

**Version:** 0.1.0-alpha
**Last Updated:** 2026-03-22

本文档提供 SlotAgent 所有公共 API 的详细说明。

---

## 目录

- [核心组件](#核心组件)
  - [CoreScheduler](#corescheduler)
  - [PluginPool](#pluginpool)
  - [ToolRegistry](#toolregistry)
  - [HookManager](#hookmanager)
  - [ApprovalManager](#approvalmanager)
- [数据类型](#数据类型)
  - [Tool](#tool)
  - [PluginContext](#plugincontext)
  - [PluginResult](#pluginresult)
  - [ToolExecutionContext](#toolexecutioncontext)
  - [Hook Events](#hook-events)
  - [ApprovalRecord](#approvalrecord)
- [插件接口](#插件接口)
  - [PluginInterface](#plugininterface)
  - [内置插件](#内置插件)
- [异常](#异常)

---

## 核心组件

### CoreScheduler

核心调度引擎，负责工具执行和插件链协调。

#### 构造函数

```python
CoreScheduler(
    plugin_pool: Optional[PluginPool] = None,
    tool_registry: Optional[ToolRegistry] = None,
    hook_manager: Optional[HookManager] = None
)
```

**参数：**
- `plugin_pool` (PluginPool, optional): 插件池实例。如果不提供，会自动创建新实例。
- `tool_registry` (ToolRegistry, optional): 工具注册中心实例。如果不提供，会自动创建新实例。
- `hook_manager` (HookManager, optional): Hook管理器实例。如果不提供，会自动创建新实例。

**示例：**
```python
from slotagent.core import CoreScheduler

# 使用默认配置
scheduler = CoreScheduler()

# 使用自定义组件
from slotagent.core import PluginPool, HookManager
plugin_pool = PluginPool()
hook_manager = HookManager()
scheduler = CoreScheduler(plugin_pool=plugin_pool, hook_manager=hook_manager)
```

#### execute()

执行指定工具，并通过插件链处理。

```python
def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext
```

**参数：**
- `tool_id` (str): 工具标识符（必须已注册）
- `params` (Dict[str, Any]): 工具参数（会被 Schema 插件验证）

**返回：**
- `ToolExecutionContext`: 完整的执行上下文，包含状态、结果、错误等

**抛出：**
- `ToolNotFoundError`: 如果工具未注册

**示例：**
```python
context = scheduler.execute('weather_query', {'location': 'Beijing'})

if context.status == ExecutionStatus.COMPLETED:
    print(f"Result: {context.final_result}")
elif context.status == ExecutionStatus.PENDING_APPROVAL:
    print(f"Waiting for approval: {context.approval_id}")
elif context.status == ExecutionStatus.FAILED:
    print(f"Error: {context.error}")
```

#### register_tool()

注册新工具到调度器。

```python
def register_tool(self, tool: Tool) -> None
```

**参数：**
- `tool` (Tool): 工具对象

**抛出：**
- `ToolValidationError`: 如果工具验证失败
- `DuplicateToolError`: 如果工具ID已存在

**示例：**
```python
from slotagent.types import Tool

tool = Tool(
    tool_id='my_tool',
    name='My Tool',
    description='A description with at least 10 characters',
    input_schema={'type': 'object', 'properties': {}},
    execute_func=lambda params: {'status': 'ok'}
)

scheduler.register_tool(tool)
```

#### get_tool()

获取已注册的工具。

```python
def get_tool(self, tool_id: str) -> Optional[Tool]
```

**参数：**
- `tool_id` (str): 工具标识符

**返回：**
- `Tool` 或 `None`: 工具对象，如果不存在返回 None

---

### PluginPool

插件池，管理全局插件和工具级插件配置。

#### 构造函数

```python
PluginPool()
```

无参数构造函数。

#### register_global_plugin()

注册全局插件。

```python
def register_global_plugin(self, plugin: PluginInterface) -> None
```

**参数：**
- `plugin` (PluginInterface): 插件实例

**抛出：**
- `PluginConfigError`: 如果插件配置无效
- `DuplicatePluginError`: 如果插件ID已存在

**示例：**
```python
from slotagent.plugins import SchemaDefault, GuardDefault

pool = PluginPool()
pool.register_global_plugin(SchemaDefault(schema={...}))
pool.register_global_plugin(GuardDefault(blacklist=['dangerous_tool']))
```

#### get_plugin_chain()

获取指定工具的插件链。

```python
def get_plugin_chain(
    self,
    tool_id: str,
    layers: List[str] = None
) -> List[PluginInterface]
```

**参数：**
- `tool_id` (str): 工具标识符
- `layers` (List[str], optional): 要获取的层列表。默认所有层。

**返回：**
- `List[PluginInterface]`: 按执行顺序排列的插件列表

**插件执行顺序：** schema → guard → healing → reflect → observe

---

### ToolRegistry

工具注册中心，管理工具的注册、查询和验证。

#### 构造函数

```python
ToolRegistry(plugin_pool: Optional[PluginPool] = None)
```

**参数：**
- `plugin_pool` (PluginPool, optional): 插件池实例，用于验证工具的插件配置

#### register()

注册工具。

```python
def register(self, tool: Tool) -> None
```

**参数：**
- `tool` (Tool): 工具对象

**抛出：**
- `ToolValidationError`: 工具验证失败
- `DuplicateToolError`: 工具ID已存在

**验证规则：**
- `tool_id`: 格式为 `^[a-z][a-z0-9_]{1,63}$`
- `name`: 非空字符串
- `description`: 至少 10 个字符
- `input_schema`: 必须包含 `type` 和 `properties`
- `execute_func`: 必须是可调用对象
- `plugins`: 如果提供，必须是有效的插件配置

#### get_tool()

获取工具。

```python
def get_tool(self, tool_id: str) -> Optional[Tool]
```

**参数：**
- `tool_id` (str): 工具标识符

**返回：**
- `Tool` 或 `None`

#### list_tools()

列出所有工具。

```python
def list_tools(self, tags: List[str] = None) -> List[Tool]
```

**参数：**
- `tags` (List[str], optional): 按标签过滤（暂未实现）

**返回：**
- `List[Tool]`: 工具列表

#### unregister()

注销工具。

```python
def unregister(self, tool_id: str) -> None
```

**参数：**
- `tool_id` (str): 工具标识符

**抛出：**
- `ToolNotFoundError`: 工具不存在

---

### HookManager

Hook 事件管理器，支持发布-订阅模式的事件系统。

#### 构造函数

```python
HookManager()
```

无参数构造函数。

#### subscribe()

订阅事件。

```python
def subscribe(self, event_type: str, handler: Callable) -> None
```

**参数：**
- `event_type` (str): 事件类型，可选值：
  - `"before_exec"` - 工具执行前
  - `"after_exec"` - 工具执行成功后
  - `"fail"` - 执行失败
  - `"guard_block"` - Guard 插件阻止执行
  - `"wait_approval"` - 等待人工审批
- `handler` (Callable): 事件处理函数，接收事件对象作为参数

**抛出：**
- `ValueError`: 事件类型无效

**示例：**
```python
from slotagent.core import HookManager

hook_manager = HookManager()

def on_before_exec(event):
    print(f"Executing tool: {event.tool_id}")

def on_fail(event):
    print(f"Execution failed: {event.error}")

hook_manager.subscribe('before_exec', on_before_exec)
hook_manager.subscribe('fail', on_fail)
```

#### unsubscribe()

取消订阅。

```python
def unsubscribe(self, event_type: str, handler: Callable) -> None
```

**参数：**
- `event_type` (str): 事件类型
- `handler` (Callable): 要移除的处理函数

#### emit()

触发事件（内部使用，由 CoreScheduler 调用）。

```python
def emit(self, event: Union[BeforeExecEvent, AfterExecEvent, ...]) -> None
```

**参数：**
- `event`: 事件对象

**注意：** 订阅者异常不会影响主流程，异常会被捕获并记录。

---

### ApprovalManager

审批管理器，管理人工审批流程的生命周期。

#### 构造函数

```python
ApprovalManager(default_timeout: float = 300.0)
```

**参数：**
- `default_timeout` (float): 默认审批超时时间（秒），默认 300 秒（5分钟）

#### create_approval()

创建审批请求。

```python
def create_approval(
    self,
    execution_id: str,
    tool_id: str,
    tool_name: str,
    params: Dict,
    timeout: Optional[float] = None,
    metadata: Optional[Dict] = None
) -> str
```

**参数：**
- `execution_id` (str): 执行ID
- `tool_id` (str): 工具ID
- `tool_name` (str): 工具名称
- `params` (Dict): 工具参数
- `timeout` (float, optional): 自定义超时时间（秒），默认使用 default_timeout
- `metadata` (Dict, optional): 附加元数据

**返回：**
- `str`: 审批ID（UUID格式）

**示例：**
```python
from slotagent.core import ApprovalManager

manager = ApprovalManager(default_timeout=600.0)  # 10分钟超时

approval_id = manager.create_approval(
    execution_id='exec-123',
    tool_id='payment_refund',
    tool_name='Payment Refund',
    params={'amount': 1000, 'order_id': 'ORD-001'},
    metadata={'risk_level': 'high'}
)
```

#### approve()

批准审批请求。

```python
def approve(self, approval_id: str, approver: str) -> ApprovalRecord
```

**参数：**
- `approval_id` (str): 审批ID
- `approver` (str): 审批人标识

**返回：**
- `ApprovalRecord`: 更新后的审批记录

**抛出：**
- `ValueError`: 审批ID不存在或状态不是 PENDING

**示例：**
```python
record = manager.approve(approval_id, approver='admin@example.com')
print(f"Approved by: {record.approver}")
```

#### reject()

拒绝审批请求。

```python
def reject(
    self,
    approval_id: str,
    approver: str,
    reason: str
) -> ApprovalRecord
```

**参数：**
- `approval_id` (str): 审批ID
- `approver` (str): 审批人标识
- `reason` (str): 拒绝原因

**返回：**
- `ApprovalRecord`: 更新后的审批记录

**抛出：**
- `ValueError`: 审批ID不存在或状态不是 PENDING

#### check_timeouts()

检查并标记超时的审批请求。

```python
def check_timeouts() -> List[str]
```

**返回：**
- `List[str]`: 已标记为 TIMEOUT 的审批ID列表

**示例：**
```python
# 定期调用以检查超时
expired_ids = manager.check_timeouts()
for approval_id in expired_ids:
    print(f"Approval {approval_id} timed out")
```

#### list_pending()

列出所有待审批请求。

```python
def list_pending() -> List[ApprovalRecord]
```

**返回：**
- `List[ApprovalRecord]`: 状态为 PENDING 的审批记录列表

---

## 数据类型

### Tool

工具定义数据类（dataclass）。

```python
@dataclass
class Tool:
    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    execute_func: Callable[[Dict[str, Any]], Any]
    plugins: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
```

**字段说明：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `tool_id` | str | ✅ | 工具唯一标识符，格式: `^[a-z][a-z0-9_]{1,63}$` |
| `name` | str | ✅ | 工具名称（用于显示） |
| `description` | str | ✅ | 工具描述（至少10个字符） |
| `input_schema` | Dict | ✅ | JSON Schema 格式的参数定义 |
| `execute_func` | Callable | ✅ | 工具执行函数，接收 `params: Dict` 返回结果 |
| `plugins` | Dict[str, str] | ❌ | 工具级插件配置，格式: `{layer: plugin_id}` |
| `metadata` | Dict | ❌ | 附加元数据（用于扩展） |

**示例：**
```python
from slotagent.types import Tool

# 简单工具
simple_tool = Tool(
    tool_id='echo',
    name='Echo',
    description='Echo the input message',
    input_schema={
        'type': 'object',
        'properties': {
            'message': {'type': 'string'}
        },
        'required': ['message']
    },
    execute_func=lambda params: {'echo': params['message']}
)

# 带插件配置的工具
payment_tool = Tool(
    tool_id='payment_refund',
    name='Payment Refund',
    description='Process payment refund with strict validation',
    input_schema={
        'type': 'object',
        'properties': {
            'amount': {'type': 'number', 'minimum': 0},
            'order_id': {'type': 'string'}
        },
        'required': ['amount', 'order_id']
    },
    execute_func=process_refund,
    plugins={
        'schema': 'schema_strict',
        'guard': 'guard_human_in_loop'
    },
    metadata={'risk_level': 'high'}
)
```

---

### PluginContext

插件执行上下文。

```python
@dataclass
class PluginContext:
    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    layer: str
    execution_id: str
    timestamp: float
    previous_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
```

**字段说明：**
- `tool_id`: 工具标识符
- `tool_name`: 工具名称
- `params`: 工具参数
- `layer`: 当前插件层 (schema/guard/healing/reflect/observe)
- `execution_id`: 执行ID（UUID）
- `timestamp`: 时间戳
- `previous_results`: 前序插件的执行结果
- `metadata`: 附加元数据

---

### PluginResult

插件执行结果。

```python
@dataclass
class PluginResult:
    success: bool
    should_continue: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

**字段说明：**
- `success`: 插件是否执行成功
- `should_continue`: 是否继续执行链（False 会中断执行）
- `data`: 结果数据（传递给后续插件）
- `error`: 错误信息

**示例：**
```python
from slotagent.types import PluginResult

# 成功且继续
result = PluginResult(success=True, data={'validated': True})

# 阻止执行
result = PluginResult(
    success=True,
    should_continue=False,
    data={'blocked': True, 'reason': 'Tool in blacklist'}
)

# 失败
result = PluginResult(
    success=False,
    should_continue=False,
    error='Schema validation failed: missing required field'
)
```

---

### ToolExecutionContext

工具执行上下文（完整执行状态）。

```python
@dataclass
class ToolExecutionContext:
    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    execution_id: str
    status: ExecutionStatus
    start_time: float
    end_time: Optional[float] = None
    execution_time: Optional[float] = None
    final_result: Optional[Any] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    plugin_results: Optional[Dict[str, Any]] = None
```

**ExecutionStatus 枚举：**
```python
class ExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_APPROVAL = "pending_approval"
```

**方法：**
```python
def is_terminal(self) -> bool:
    """检查是否为终止状态（COMPLETED/FAILED/PENDING_APPROVAL）"""
```

---

### Hook Events

#### BeforeExecEvent

工具执行前触发。

```python
@dataclass
class BeforeExecEvent:
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    event_type: str = "before_exec"
    metadata: Optional[Dict[str, Any]] = None
```

#### AfterExecEvent

工具执行成功后触发。

```python
@dataclass
class AfterExecEvent:
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    result: Any
    execution_time: float
    event_type: str = "after_exec"
    metadata: Optional[Dict[str, Any]] = None
```

#### FailEvent

执行失败���触发。

```python
@dataclass
class FailEvent:
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    error: str
    failed_at: str  # Layer where failure occurred
    event_type: str = "fail"
    metadata: Optional[Dict[str, Any]] = None
```

#### GuardBlockEvent

Guard 插件阻止执行时触发。

```python
@dataclass
class GuardBlockEvent:
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    reason: str
    event_type: str = "guard_block"
    metadata: Optional[Dict[str, Any]] = None
```

#### WaitApprovalEvent

等待人工审批时触发。

```python
@dataclass
class WaitApprovalEvent:
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    approval_id: str
    event_type: str = "wait_approval"
    metadata: Optional[Dict[str, Any]] = None
```

---

### ApprovalRecord

审批记录。

```python
@dataclass
class ApprovalRecord:
    approval_id: str
    status: ApprovalStatus
    execution_id: str
    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    created_at: float
    timeout_at: float
    approved_at: Optional[float] = None
    rejected_at: Optional[float] = None
    approver: Optional[str] = None
    reject_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

**ApprovalStatus 枚举：**
```python
class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
```

---

## 插件接口

### PluginInterface

所有插件必须继承的基类（抽象类）。

```python
class PluginInterface(ABC):
    layer: str          # 插件层 (schema/guard/healing/reflect/observe)
    plugin_id: str      # 插件唯一标识符

    @abstractmethod
    def validate(self) -> bool:
        """验证插件配置是否有效"""
        pass

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """执行插件逻辑"""
        pass
```

**自定义插件示例：**
```python
from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

class CustomGuardPlugin(PluginInterface):
    layer = 'guard'
    plugin_id = 'guard_custom'

    def __init__(self, allowed_users: List[str]):
        self.allowed_users = set(allowed_users)

    def validate(self) -> bool:
        return len(self.allowed_users) > 0

    def execute(self, context: PluginContext) -> PluginResult:
        user = context.metadata.get('user_id', '')

        if user in self.allowed_users:
            return PluginResult(success=True, data={'approved': True})
        else:
            return PluginResult(
                success=True,
                should_continue=False,
                data={'blocked': True, 'reason': f'User {user} not authorized'}
            )
```

---

### 内置插件

#### Schema Layer

**SchemaDefault**
```python
SchemaDefault(schema: Dict[str, Any] = None)
```
基础 JSON Schema 验证，允许额外属性。

**SchemaStrict**
```python
SchemaStrict(schema: Dict[str, Any] = None)
```
严格 JSON Schema 验证，拒绝额外属性，支持 pattern 和 enum。

#### Guard Layer

**GuardDefault**
```python
GuardDefault(
    blacklist: List[str] = None,
    whitelist: List[str] = None,
    whitelist_only: bool = False
)
```
基于黑名单/白名单的访问控制。

**GuardHumanInLoop**
```python
GuardHumanInLoop(
    approval_manager: ApprovalManager,
    timeout: Optional[float] = None
)
```
人工审批插件，触发审批流程。

#### Healing Layer

**HealingRetry**
```python
HealingRetry(max_retries: int = 3, delay: float = 1.0)
```
简单重试机制（当前为占位实现）。

#### Reflect Layer

**ReflectSimple**
```python
ReflectSimple()
```
简单反思插件，判断任务是否完成（当前为占位实现）。

#### Observe Layer

**LogPlugin**
```python
LogPlugin()
```
日志记录插件，输出执行信息到 stdout。

---

## 异常

### ToolNotFoundError

```python
class ToolNotFoundError(Exception):
    """工具未找到异常"""
```

**抛出时机：** 执行不存在的工具时

### ToolValidationError

```python
class ToolValidationError(Exception):
    """工具验证失败异常"""
```

**抛出时机：** 工具定义不符合验证规则时

### DuplicateToolError

```python
class DuplicateToolError(Exception):
    """工具ID重复异常"""
```

**抛出时机：** 注册已存在的工具ID时

### PluginConfigError

```python
class PluginConfigError(Exception):
    """插件配置错误异常"""
```

**抛出时机：** 插件配置无效时（如缺少 layer 或 plugin_id）

### DuplicatePluginError

```python
class DuplicatePluginError(Exception):
    """插件ID重复异常"""
```

**抛出时机：** 注册已存在的插件ID时

---

## 完整使用示例

### 基本工具执行

```python
from slotagent.core import CoreScheduler
from slotagent.types import Tool

# 1. 创建调度器
scheduler = CoreScheduler()

# 2. 定义工具
def get_weather(params):
    location = params['location']
    # 模拟天气查询
    return {
        'location': location,
        'temperature': 25,
        'condition': 'sunny'
    }

weather_tool = Tool(
    tool_id='weather_query',
    name='Weather Query',
    description='Query weather information for a location',
    input_schema={
        'type': 'object',
        'properties': {
            'location': {'type': 'string'}
        },
        'required': ['location']
    },
    execute_func=get_weather
)

# 3. 注册工具
scheduler.register_tool(weather_tool)

# 4. 执行工具
context = scheduler.execute('weather_query', {'location': 'Beijing'})

# 5. 检查结果
if context.status == ExecutionStatus.COMPLETED:
    print(f"Weather: {context.final_result}")
```

### 使用插件链

```python
from slotagent.core import CoreScheduler
from slotagent.plugins import SchemaDefault, GuardDefault, LogPlugin

# 创建调度器和插件
scheduler = CoreScheduler()

# 注册全局插件
scheduler.plugin_pool.register_global_plugin(
    SchemaDefault(schema={
        'type': 'object',
        'properties': {
            'location': {'type': 'string'}
        },
        'required': ['location']
    })
)

scheduler.plugin_pool.register_global_plugin(
    GuardDefault(blacklist=['dangerous_api'])
)

scheduler.plugin_pool.register_global_plugin(LogPlugin())

# 注册工具并执行
scheduler.register_tool(weather_tool)
context = scheduler.execute('weather_query', {'location': 'Beijing'})
```

### 人工审批流程

```python
from slotagent.core import CoreScheduler, ApprovalManager, HookManager
from slotagent.plugins import GuardHumanInLoop
from slotagent.types import Tool, ExecutionStatus

# 创建组件
approval_manager = ApprovalManager(default_timeout=600.0)
hook_manager = HookManager()
scheduler = CoreScheduler(hook_manager=hook_manager)

# 订阅审批事件
def on_wait_approval(event):
    print(f"Approval needed for: {event.tool_id}")
    print(f"Approval ID: {event.approval_id}")

    # 在实际应用中，这里会通知审批人
    # 例如：send_notification_to_approver(event.approval_id)

hook_manager.subscribe('wait_approval', on_wait_approval)

# 注册审批插件
scheduler.plugin_pool.register_global_plugin(
    GuardHumanInLoop(approval_manager=approval_manager)
)

# 注册高风险工具
payment_tool = Tool(
    tool_id='payment_refund',
    name='Payment Refund',
    description='Process a payment refund (high risk operation)',
    input_schema={
        'type': 'object',
        'properties': {
            'amount': {'type': 'number'},
            'order_id': {'type': 'string'}
        },
        'required': ['amount', 'order_id']
    },
    execute_func=lambda p: {'refunded': p['amount']}
)

scheduler.register_tool(payment_tool)

# 执行工具
context = scheduler.execute('payment_refund', {
    'amount': 1000,
    'order_id': 'ORD-12345'
})

# 检查状态
if context.status == ExecutionStatus.PENDING_APPROVAL:
    approval_id = context.approval_id

    # 审批人批准
    record = approval_manager.approve(approval_id, approver='admin@example.com')
    print(f"Approval status: {record.status}")
```

---

**文档版本：** 1.0
**维护者：** SlotAgent 核心团队
**反馈：** https://github.com/yimwu/slotagent/issues
