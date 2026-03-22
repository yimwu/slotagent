# ToolExecutionContext - 工具执行上下文

**文档版本:** 1.0
**最后更新:** 2026-03-22
**状态:** Approved

---

## 1. 概述

`ToolExecutionContext` 是工具执行的完整上下文,包含工具定义、执行状态、插件链结果等信息。

### 1.1 职责

- 存储工具执行的完整状态
- 追踪插件链执行进度
- 管理执行状态转移 (running/pending/completed/failed)
- 支持审批流程的状态管理

### 1.2 设计原则

- **可变状态**: 执行过程中状态会更新
- **完整性**: 包含从开始到结束的所有信息
- **可追溯**: 记录所有插件的执行结果

---

## 2. 数据结构定义

### 2.1 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `tool_id` | `str` | ✅ | 工具ID |
| `tool_name` | `str` | ✅ | 工具名称 |
| `params` | `Dict[str, Any]` | ✅ | 工具参数 |
| `execution_id` | `str` | ✅ | 执行ID (UUID) |
| `status` | `ExecutionStatus` | ✅ | 执行状态枚举 |
| `plugin_results` | `Dict[str, PluginResult]` | ✅ | 各插件层执行结果 |
| `final_result` | `Any` | ❌ | 最终执行结果 |
| `error` | `str` | ❌ | 错误信息 |
| `approval_id` | `str` | ❌ | 审批ID (如需审批) |
| `start_time` | `float` | ✅ | 开始时间戳 |
| `end_time` | `float` | ❌ | 结束时间戳 |
| `execution_time` | `float` | ❌ | 总执行耗时(秒) |

### 2.2 ExecutionStatus 枚举

```python
from enum import Enum

class ExecutionStatus(str, Enum):
    """工具执行状态"""

    RUNNING = "running"           # 执行中
    PENDING_APPROVAL = "pending"  # 等待审批
    COMPLETED = "completed"       # 执行成功
    FAILED = "failed"             # 执行失败
```

### 2.3 类型签名

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum

@dataclass
class ToolExecutionContext:
    """工具执行上下文"""

    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    execution_id: str
    status: ExecutionStatus
    start_time: float
    plugin_results: Dict[str, PluginResult] = field(default_factory=dict)
    final_result: Optional[Any] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    end_time: Optional[float] = None
    execution_time: Optional[float] = None
```

---

## 3. 字段语义和约束

### 3.1 status (ExecutionStatus)

**语义:** 工具执行的当前状态

**状态转移:**

```
RUNNING ──> COMPLETED  (执行成功)
RUNNING ──> FAILED     (执行失败)
RUNNING ──> PENDING_APPROVAL (需要审批)
PENDING_APPROVAL ──> RUNNING (审批通过)
PENDING_APPROVAL ──> FAILED  (审批拒绝)
```

**约束:**
- 初始状态: `RUNNING`
- 终态: `COMPLETED`, `FAILED`
- 可恢复状态: `PENDING_APPROVAL` (审批后继续)

### 3.2 plugin_results

**语义:** 各插件层的执行结果记录

**约束:**
- key: 插件层名称 ('schema', 'guard', 'healing', 'reflect', 'observe')
- value: 对应插件的 `PluginResult`
- 按执行顺序填充

**示例:**
```python
plugin_results = {
    'schema': PluginResult(success=True, data={'validated': True}),
    'guard': PluginResult(success=True, should_continue=False,
                          data={'pending_approval': True, 'approval_id': 'APR123'})
}
```

### 3.3 final_result

**语义:** 工具执行的最终结果

**约束:**
- status=COMPLETED 时必须有值
- 可以是任意类型 (取决于工具返回)

**示例:**
```python
# 天气查询结果
final_result = {
    'location': 'Beijing',
    'temperature': 15,
    'weather': 'Sunny'
}
```

### 3.4 approval_id

**语义:** 审批流程的唯一标识

**约束:**
- status=PENDING_APPROVAL 时必须有值
- UUID 格式

**示例:**
```python
approval_id = "550e8400-e29b-41d4-a716-446655440001"
```

### 3.5 execution_time

**语义:** 从开始到结束的总耗时

**约束:**
- 浮点数,单位:秒
- `end_time - start_time`
- 执行结束时计算

**示例:**
```python
execution_time = 0.523  # 523毫秒
```

---

## 4. 状态转移示例

### 4.1 成功执行流程

```python
# 1. 初始化
context = ToolExecutionContext(
    tool_id="weather_query",
    tool_name="天气查询",
    params={"location": "Beijing"},
    execution_id=str(uuid.uuid4()),
    status=ExecutionStatus.RUNNING,
    start_time=time.time()
)

# 2. 插件链执行
context.plugin_results['schema'] = PluginResult(success=True)
context.plugin_results['guard'] = PluginResult(success=True)

# 3. 执行完成
context.status = ExecutionStatus.COMPLETED
context.final_result = {'temperature': 15, 'weather': 'Sunny'}
context.end_time = time.time()
context.execution_time = context.end_time - context.start_time
```

### 4.2 等待审批流程

```python
# 1. 初始化
context = ToolExecutionContext(
    tool_id="payment_refund",
    tool_name="支付退款",
    params={"order_id": "ORD123", "amount": 99.99},
    execution_id=str(uuid.uuid4()),
    status=ExecutionStatus.RUNNING,
    start_time=time.time()
)

# 2. Guard 插件拦截
guard_result = PluginResult(
    success=True,
    should_continue=False,
    data={'pending_approval': True, 'approval_id': 'APR123'}
)
context.plugin_results['guard'] = guard_result

# 3. 状态变为等待审批
context.status = ExecutionStatus.PENDING_APPROVAL
context.approval_id = 'APR123'

# 4. 审批通过后
context.status = ExecutionStatus.RUNNING
# 继续执行...

# 5. 执行完成
context.status = ExecutionStatus.COMPLETED
context.final_result = {'refund_id': 'REF456', 'status': 'success'}
context.end_time = time.time()
context.execution_time = context.end_time - context.start_time
```

### 4.3 执行失败流程

```python
# 1. 初始化
context = ToolExecutionContext(
    tool_id="api_call",
    tool_name="API调用",
    params={"endpoint": "/users"},
    execution_id=str(uuid.uuid4()),
    status=ExecutionStatus.RUNNING,
    start_time=time.time()
)

# 2. Schema 验证失败
schema_result = PluginResult(
    success=False,
    error="参数 'endpoint' 格式错误",
    error_type="ValidationError",
    should_continue=False
)
context.plugin_results['schema'] = schema_result

# 3. 状态变为失败
context.status = ExecutionStatus.FAILED
context.error = "参数验证失败: endpoint 格式错误"
context.end_time = time.time()
context.execution_time = context.end_time - context.start_time
```

---

## 5. 使用示例

### 5.1 在 CoreScheduler 中使用

```python
class CoreScheduler:
    def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
        # 创建执行上下文
        context = ToolExecutionContext(
            tool_id=tool_id,
            tool_name=self._get_tool_name(tool_id),
            params=params,
            execution_id=str(uuid.uuid4()),
            status=ExecutionStatus.RUNNING,
            start_time=time.time()
        )

        try:
            # 执行插件链
            for layer in ['schema', 'guard', 'healing', 'reflect']:
                result = self._execute_plugin(layer, context)
                context.plugin_results[layer] = result

                if not result.should_continue:
                    if result.data and result.data.get('pending_approval'):
                        context.status = ExecutionStatus.PENDING_APPROVAL
                        context.approval_id = result.data['approval_id']
                    return context

            # 成功完成
            context.status = ExecutionStatus.COMPLETED
            context.final_result = self._get_final_result(context)

        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.error = str(e)

        finally:
            context.end_time = time.time()
            context.execution_time = context.end_time - context.start_time

        return context
```

---

## 6. 不变量 (Invariants)

1. **状态一致性**:
   - `status=COMPLETED` 时,`final_result` 不为 `None`
   - `status=FAILED` 时,`error` 不为 `None`
   - `status=PENDING_APPROVAL` 时,`approval_id` 不为 `None`

2. **时间顺序**: `end_time >= start_time`

3. **插件顺序**: `plugin_results` 中的插件按执行顺序记录

---

## 7. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|--------|
| 1.0 | 2026-03-22 | 初始版本,定义核心字段和状态枚举 |

---

**审批状态:** ✅ Approved
**审批人:** SlotAgent Core Team
**审批日期:** 2026-03-22
