# PluginResult - 插件执行结果

**文档版本:** 1.0
**最后更新:** 2026-03-22
**状态:** Approved

---

## 1. 概述

`PluginResult` 是插件执行后返回的结果数据结构,统一封装执行状态、结果数据和错误信息。

### 1.1 职责

- 标准化插件返回值格式
- 携带执行状态 (成功/失败/待审批)
- 传递插件执行结果和错误信息
- 支持链式传递给下一个插件

### 1.2 设计原则

- **统一格式**: 所有插件返回相同结构
- **明确状态**: success/failed/pending 三态清晰
- **完整信息**: 包含结果、错误、耗时等关键信息

---

## 2. 数据结构定义

### 2.1 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `success` | `bool` | ✅ | 插件执行是否成功 |
| `data` | `Any` | ❌ | 插件返回的数据,可以是任意类型 |
| `error` | `str` | ❌ | 错误信息,success=False时应提供 |
| `error_type` | `str` | ❌ | 错误类型,如 'ValidationError', 'PermissionDenied' |
| `should_continue` | `bool` | ✅ | 是否继续执行插件链,默认True |
| `metadata` | `Dict[str, Any]` | ❌ | 插件自定义元数据 |
| `execution_time` | `float` | ❌ | 插件执行耗时(秒),可选 |

### 2.2 类型签名

```python
from dataclasses import dataclass
from typing import Any, Optional, Dict

@dataclass
class PluginResult:
    """插件执行结果"""

    success: bool
    should_continue: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
```

---

## 3. 字段语义和约束

### 3.1 success

**语义:** 插件是否成功完成任务

**约束:**
- 布尔值
- `True`: 插件正常完成
- `False`: 插件执行失败

**语义规则:**
- 成功不代表业务通过 (如 Guard 拦截也是成功)
- 失败指插件执行异常或无法完成

**示例:**
```python
# Schema 验证通过
result = PluginResult(success=True, data={'validated': True})

# Schema 验证失败
result = PluginResult(
    success=False,
    error="参数 'location' 不能为空",
    error_type="ValidationError"
)
```

### 3.2 should_continue

**语义:** 是否继续执行插件链中的后续插件

**约束:**
- 布尔值
- 默认值: `True`
- `False`: 立即中断插件链执行

**使用场景:**
- Guard 拦截: `should_continue=False`
- 等待审批: `should_continue=False` (状态变为 pending)
- 严重错误: `should_continue=False`

**示例:**
```python
# Guard 拦截高危操作
result = PluginResult(
    success=True,
    should_continue=False,
    data={'blocked': True, 'reason': '需要人工审批'}
)
```

### 3.3 data

**语义:** 插件返回的具体数据

**约束:**
- 可以是任意类型: dict, list, str, int, bool, None
- 建议使用字典类型,便于扩展

**示例:**
```python
# Schema 插件返回验证结果
data = {'validated': True, 'normalized_params': {...}}

# Guard 插件返回审批ID
data = {'approval_id': 'APR123', 'approval_url': 'https://...'}

# Healing 插件返回重试次数
data = {'retry_count': 2, 'recovered': True}
```

### 3.4 error

**语义:** 错误描述信息

**约束:**
- 字符串类型
- success=False 时应该提供
- 面向用户的可读错误信息

**示例:**
```python
error = "参数 'location' 不能为空"
error = "权限不足: 需要 'admin' 角色"
error = "LLM调用超时"
```

### 3.5 error_type

**语义:** 错误类型分类

**约束:**
- 字符串类型
- 建议使用异常类名格式: `ValidationError`, `PermissionDenied`

**常见错误类型:**
- `ValidationError`: 参数验证错误
- `PermissionDenied`: 权限不足
- `TimeoutError`: 超时
- `ExecutionError`: 执行错误
- `ConfigError`: 配置错误

**示例:**
```python
error_type = "ValidationError"
error_type = "PermissionDenied"
```

### 3.6 metadata

**语义:** 插件自定义元数据

**约束:**
- 字典类型
- 可选字段
- 用于传递额外信息

**示例:**
```python
metadata = {
    'validator': 'JsonSchemaValidator',
    'schema_version': '1.0'
}

metadata = {
    'approval_requester': 'system',
    'approval_timeout': 3600
}
```

### 3.7 execution_time

**语义:** 插件执行耗时

**约束:**
- 浮点数,单位:秒
- 可选字段
- 用于性能监控

**示例:**
```python
execution_time = 0.025  # 25毫秒
execution_time = 1.234  # 1.234秒
```

---

## 4. 标准返回模式

### 4.1 成功执行

```python
result = PluginResult(
    success=True,
    data={'processed': True}
)
```

### 4.2 失败执行

```python
result = PluginResult(
    success=False,
    error="参数验证失败: location 不能为空",
    error_type="ValidationError",
    should_continue=False
)
```

### 4.3 Guard 拦截

```python
result = PluginResult(
    success=True,
    should_continue=False,
    data={
        'blocked': True,
        'reason': '高危操作需要审批',
        'approval_id': 'APR123'
    }
)
```

### 4.4 等待审批

```python
result = PluginResult(
    success=True,
    should_continue=False,
    data={
        'pending_approval': True,
        'approval_id': 'APR456',
        'approval_url': 'https://approval.example.com/APR456'
    },
    metadata={'timeout': 3600}
)
```

---

## 5. 使用示例

### 5.1 Schema 插件

```python
class SchemaDefault(PluginInterface):
    def execute(self, context: PluginContext) -> PluginResult:
        # 验证参数
        if not context.params.get('location'):
            return PluginResult(
                success=False,
                error="参数 'location' 不能为空",
                error_type="ValidationError",
                should_continue=False
            )

        return PluginResult(
            success=True,
            data={'validated': True, 'params': context.params}
        )
```

### 5.2 Guard 插件

```python
class GuardHumanInLoop(PluginInterface):
    def execute(self, context: PluginContext) -> PluginResult:
        # 高危工具需要审批
        if context.tool_id in HIGH_RISK_TOOLS:
            approval_id = self._create_approval(context)
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'pending_approval': True,
                    'approval_id': approval_id
                }
            )

        return PluginResult(success=True, data={'approved': True})
```

---

## 6. 不变量 (Invariants)

1. **成功状态**: `success=True` 时,`error` 应为 `None`
2. **失败状态**: `success=False` 时,应提供 `error` 和 `error_type`
3. **中断逻辑**: `should_continue=False` 表示插件链应该停止

---

## 7. 最佳实践

1. **错误处理**: 失败时始终提供清晰的 `error` 信息
2. **类型一致**: `data` 字段在同一插件中保持类型一致
3. **性能监控**: 关键插件记录 `execution_time`
4. **元数据使用**: 使用 `metadata` 而非扩展 `data` 字段

---

## 8. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|--------|
| 1.0 | 2026-03-22 | 初始版本,定义核心字段 |

---

**审批状态:** ✅ Approved
**审批人:** SlotAgent Core Team
**审批日期:** 2026-03-22
