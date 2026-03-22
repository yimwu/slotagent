# PluginContext - 插件执行上下文

**文档版本:** 1.0
**最后更新:** 2026-03-22
**状态:** Approved

---

## 1. 概述

`PluginContext` 是插件执行时的上下文数据结构,携带插件执行所需的所有信息。

### 1.1 职责

- 向插件传递工具信息、参数、执行状态
- 携带前序插件的执行结果,支持插件链协作
- 提供插件层级信息,便于日志和调试
- 不可变数据结构,保证线程安全

### 1.2 设计原则

- **不可变性**: 使用 `@dataclass(frozen=True)` 确保上下文不被修改
- **完整性**: 包含插件执行所需的所有信息
- **类型安全**: 所有字段明确类型注解

---

## 2. 数据结构定义

### 2.1 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `tool_id` | `str` | ✅ | 工具唯一标识,lowercase_with_underscore |
| `tool_name` | `str` | ✅ | 工具可读名称 |
| `params` | `Dict[str, Any]` | ✅ | 工具参数,已通过Schema验证的参数字典 |
| `layer` | `str` | ✅ | 当前插件所在层 ('schema', 'guard', 'healing', 'reflect', 'observe') |
| `execution_id` | `str` | ✅ | 执行ID,用于追踪和日志关联,UUID格式 |
| `previous_results` | `Dict[str, Any]` | ❌ | 前序插件的执行结果,key为插件层名称 |
| `metadata` | `Dict[str, Any]` | ❌ | 扩展元数据,供插件自定义使用 |
| `timestamp` | `float` | ✅ | 上下文创建时间戳 (Unix timestamp) |

### 2.2 类型签名

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class PluginContext:
    """插件执行上下文"""

    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    layer: str
    execution_id: str
    timestamp: float
    previous_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
```

---

## 3. 字段语义和约束

### 3.1 tool_id

**语义:** 工具的全局唯一标识符

**约束:**
- 格式: `[a-z0-9_]+` (lowercase with underscore)
- 长度: 3-64 字符
- 不可为空

**示例:**
```python
tool_id = "weather_query"
tool_id = "payment_refund"
tool_id = "user_profile_update"
```

### 3.2 tool_name

**语义:** 工具的可读名称,用于日志和UI显示

**约束:**
- 非空字符串
- 长度: 1-100 字符

**示例:**
```python
tool_name = "天气查询"
tool_name = "支付退款"
```

### 3.3 params

**语义:** 工具执行参数,已通过Schema层验证

**约束:**
- 必须是字典类型
- 可以为空字典 `{}`
- 值类型可以是任意JSON可序列化类型

**示例:**
```python
params = {"location": "Beijing", "days": 7}
params = {"order_id": "ORD123", "amount": 99.99}
params = {}  # 无参数工具
```

### 3.4 layer

**语义:** 当前插件所在的层级

**约束:**
- 必须是以下值之一: `'schema'`, `'guard'`, `'healing'`, `'reflect'`, `'observe'`
- 不可为空

**示例:**
```python
layer = 'schema'
layer = 'guard'
```

### 3.5 execution_id

**语义:** 唯一执行ID,用于追踪和日志关联

**约束:**
- UUID v4 格式字符串
- 每次工具执行生成唯一ID

**示例:**
```python
execution_id = "550e8400-e29b-41d4-a716-446655440000"
```

### 3.6 previous_results

**语��:** 前序插件层的执行结果,支持插件链协作

**约束:**
- 可选字段,默认为 `None`
- key 为插件层名称 (`'schema'`, `'guard'` 等)
- value 为对应插件的返回值

**示例:**
```python
previous_results = {
    'schema': {'validated': True, 'normalized_params': {...}},
    'guard': {'approved': True, 'approval_id': None}
}
```

### 3.7 metadata

**语义:** 扩展元数据,供插件自定义使用

**约束:**
- 可选字段,默认为 `None`
- 插件可以在此存储任意扩展信息

**示例:**
```python
metadata = {
    'user_id': 'user123',
    'request_source': 'api',
    'priority': 'high'
}
```

### 3.8 timestamp

**语义:** 上下文创建时间,用于性能分析和超时检测

**约束:**
- Unix timestamp (秒级)
- 浮点数类型

**示例:**
```python
timestamp = 1711065600.123456
```

---

## 4. 使用示例

### 4.1 创建上下文

```python
import time
import uuid
from slotagent.types import PluginContext

context = PluginContext(
    tool_id="weather_query",
    tool_name="天气查询",
    params={"location": "Beijing", "days": 7},
    layer="schema",
    execution_id=str(uuid.uuid4()),
    timestamp=time.time(),
    previous_results=None,
    metadata={"user_id": "user123"}
)
```

### 4.2 在插件链中传递

```python
# Schema 插件执行后
schema_result = {'validated': True}

# 创建新上下文给 Guard 插件
guard_context = PluginContext(
    tool_id=context.tool_id,
    tool_name=context.tool_name,
    params=context.params,
    layer="guard",
    execution_id=context.execution_id,
    timestamp=context.timestamp,
    previous_results={'schema': schema_result},
    metadata=context.metadata
)
```

---

## 5. 不变量 (Invariants)

1. **上下文不可变**: 创建后所有字段不可修改
2. **execution_id 唯一**: 同一次工具执行使用相同的 execution_id
3. **layer 有效性**: layer 必须是5个插件层之一
4. **时间单调性**: timestamp 必须 ≤ 当前时间

---

## 6. 扩展性

### 6.1 未来可能添加的字段

- `retry_count`: 当前重试次数 (Healing层使用)
- `timeout`: 超时时间 (秒)
- `parent_execution_id`: 父级执行ID (嵌套调用场景)

### 6.2 向后兼容

- 新增字段必须是可选字段 (Optional)
- 不允许删除或重命名现有字段

---

## 7. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|--------|
| 1.0 | 2026-03-22 | 初始版本,定义核心字段 |

---

**审批状态:** ✅ Approved
**审批人:** SlotAgent Core Team
**审批日期:** 2026-03-22
