# Core Interfaces - 核心接口规范

**文档版本:** 1.0
**最后更新:** 2026-03-22
**状态:** Approved

---

## 1. 概述

本文档定义 SlotAgent 的核心接口,包括插件接口、工具接口等。所有接口遵循契约式设计,明确前置条件、后置条件和不变量。

---

## 2. PluginInterface - 插件基类

### 2.1 接口定义

```python
from abc import ABC, abstractmethod
from typing import ClassVar
from slotagent.types import PluginContext, PluginResult

class PluginInterface(ABC):
    """
    所有插件的抽象基类。

    插件是 SlotAgent 的核心扩展机制,每个插件负责特定层级的功能。
    """

    # 类属性
    layer: ClassVar[str]      # 插件所属层级
    plugin_id: ClassVar[str]  # 插件唯一标识

    @abstractmethod
    def validate(self) -> bool:
        """
        验证插件配置是否有效。

        Returns:
            bool: True 表示配置有效,False 表示无效

        Notes:
            - 在插件注册时调用
            - 验证失败应抛出 ValueError 并说明原因
        """
        pass

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """
        执行插件逻辑。

        Args:
            context: 插件执行上下文,包含工具信息、参数、前序结果等

        Returns:
            PluginResult: 插件执行结果

        Raises:
            PluginExecutionError: 插件执行异常

        Contract:
            Precondition:
                - context 不为 None
                - context.layer == self.layer
                - context.params 已通过 Schema 验证 (对于 guard 及后续插件)

            Postcondition:
                - 返回值类型为 PluginResult
                - result.success 为 False 时,result.error 不为 None

            Invariant:
                - 插件执行不修改 context (context 是 frozen dataclass)
                - 同一 context 多次执行应返回相同结果 (幂等性,除非有外部状态)
        """
        pass
```

### 2.2 类属性说明

#### layer

**类型:** `str`

**语义:** 插件所属层级,必须是以下值之一:
- `'schema'`: Schema 验证层
- `'guard'`: Guard 护栏层
- `'healing'`: Healing 自愈层
- `'reflect'`: Reflect 反思层
- `'observe'`: Observe 观测层

**示例:**
```python
class SchemaDefault(PluginInterface):
    layer = 'schema'
    plugin_id = 'schema_default'
```

#### plugin_id

**类型:** `str`

**语义:** 插件的全局唯一标识符

**约束:**
- 格式: `{layer}_{name}`,如 `schema_default`, `guard_human_in_loop`
- 在同一层内必须唯一

---

## 3. ToolInterface - 工具接口

### 3.1 接口定义

```python
from typing import Dict, Any, Callable, Optional, List

class ToolInterface:
    """
    工具定义接口。

    工具是 SlotAgent 执行的基本单元,每个工具定义包含:
    - 元数据 (ID, 名称, 描述)
    - 参数Schema
    - 执行器
    - 插件配置
    """

    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        executor: Callable[[Dict[str, Any]], Any],
        plugins: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 0,
        tags: Optional[List[str]] = None
    ):
        """
        初始化工具定义。

        Args:
            tool_id: 工具唯一ID (lowercase_with_underscore)
            name: 工具可读名称
            description: 工具功能描述
            input_schema: JSON Schema 格式的参数定义
            executor: 实际执行工具的可调用对象
            plugins: 工具级插件配置,key为layer,value为plugin_id
            timeout: 执行超时时间(秒)
            max_retries: 最大重试次数
            tags: 工具标签,如 ['payment', 'high-risk']

        Raises:
            ValueError: 参数验证失败

        Contract:
            Precondition:
                - tool_id 符合命名规范
                - executor 是可调用对象
                - input_schema 符合 JSON Schema 规范
                - plugins 中的 plugin_id 必须已注册
        """
        pass

    def execute(self, params: Dict[str, Any]) -> Any:
        """
        执行工具。

        Args:
            params: 工具参数,必须符合 input_schema

        Returns:
            Any: 工具执行结果

        Raises:
            ToolExecutionError: 工具执行失败

        Contract:
            Precondition:
                - params 符合 input_schema

            Postcondition:
                - 返回值类型与工具约定一致
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        验证参数是否符合 input_schema。

        Args:
            params: 待验证参数

        Returns:
            bool: True 表示验证通过

        Raises:
            ValidationError: 验证失败,包含详细错误信息
        """
        pass
```

### 3.2 工具定义示例

```python
# 轻量工具 - 最小插件配置
weather_tool = ToolInterface(
    tool_id="weather_query",
    name="天气查询",
    description="查询指定城市的天气信息",
    input_schema={
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "days": {"type": "integer", "minimum": 1, "maximum": 7}
        },
        "required": ["location"]
    },
    executor=lambda params: get_weather(params['location'], params.get('days', 1)),
    plugins={
        'schema': 'schema_default'  # 仅轻量验证
    }
)

# 高危工具 - 完整插件链
payment_tool = ToolInterface(
    tool_id="payment_refund",
    name="支付退款",
    description="处理订单退款",
    input_schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number", "minimum": 0}
        },
        "required": ["order_id", "amount"]
    },
    executor=lambda params: process_refund(params['order_id'], params['amount']),
    plugins={
        'schema': 'schema_strict',
        'guard': 'guard_human_in_loop',  # 人工审批
        'healing': 'healing_retry',
        'reflect': 'reflect_strict',
        'observe': 'observe_full'
    },
    timeout=30.0,
    max_retries=3,
    tags=['payment', 'high-risk', 'requires-approval']
)
```

---

## 4. 契约式设计 (Design by Contract)

### 4.1 前置条件 (Precondition)

调用方必须满足的条件:

**PluginInterface.execute():**
- `context` 不为 `None`
- `context.layer` 与插件的 `layer` 一致
- 对于非 Schema 插件,`context.params` 必须已通过 Schema 验证

**ToolInterface.execute():**
- `params` 不为 `None`
- `params` 符合 `input_schema` 定义

### 4.2 后置条件 (Postcondition)

方法执行后的保证:

**PluginInterface.execute():**
- 返回值类型为 `PluginResult`
- `result.success=False` 时,`result.error` 不为 `None`
- `result.should_continue=False` 时,插件链应停止

**ToolInterface.execute():**
- 返回值符合工具的输出约定
- 抛出异常时,不应有副作用 (如部分修改数据库)

### 4.3 不变量 (Invariant)

执行前后必须保持的条件:

**PluginInterface:**
- 插件执行不修改 `context` (因为 context 是 frozen)
- 插件的 `layer` 和 `plugin_id` 不可变
- 同一 context 多次执行返回相同结果 (幂等性,除非有外部状态变化)

**ToolInterface:**
- 工具的 `tool_id`, `input_schema`, `executor` 不可变
- 插件配置不可在运行时修改

---

## 5. 异常处理

### 5.1 插件异常

```python
class PluginError(Exception):
    """插件基础异常"""
    pass

class PluginExecutionError(PluginError):
    """插件执行异常"""
    pass

class PluginConfigError(PluginError):
    """插件配置异常"""
    pass

class PluginValidationError(PluginError):
    """插件验证异常"""
    pass
```

### 5.2 工具异常

```python
class ToolError(Exception):
    """工具基础异常"""
    pass

class ToolExecutionError(ToolError):
    """工具执行异常"""
    pass

class ToolNotFoundError(ToolError):
    """工具不存在"""
    pass

class ToolValidationError(ToolError):
    """工具参数验证异常"""
    pass
```

---

## 6. 最佳实践

### 6.1 插件实现

1. **幂等性**: 插件应尽可能保持幂等,相同输入返回相同输出
2. **无状态**: 插件不应依赖实例状态,所有信息从 context 获取
3. **异常安全**: 插件抛出异常不应导致系统状态不一致
4. **性能**: 轻量插件执行时间应 < 10ms

### 6.2 工具定义

1. **Schema 完整性**: `input_schema` 应完整定义所有参数和约束
2. **执行器纯函数**: `executor` 应尽可能是纯函数,避免副作用
3. **插件配置**: 根据工具风险级别选择合适的插件链
4. **超时设置**: 网络调用类工具应设置合理的 `timeout`

---

## 7. 示例实现

### 7.1 Schema 插件示例

```python
class SchemaDefault(PluginInterface):
    """默认 Schema 验证插件"""

    layer = 'schema'
    plugin_id = 'schema_default'

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        # 简单验证: 检查必填参数
        tool = self._get_tool(context.tool_id)

        try:
            # 验证参数
            self._validate_params(context.params, tool.input_schema)

            return PluginResult(
                success=True,
                data={'validated': True, 'params': context.params}
            )

        except ValidationError as e:
            return PluginResult(
                success=False,
                error=str(e),
                error_type='ValidationError',
                should_continue=False
            )
```

### 7.2 Guard 插件示例

```python
class GuardDefault(PluginInterface):
    """默认 Guard 插件 (白名单/黑名单)"""

    layer = 'guard'
    plugin_id = 'guard_default'

    def __init__(self, blacklist: List[str] = None):
        self.blacklist = blacklist or []

    def validate(self) -> bool:
        return isinstance(self.blacklist, list)

    def execute(self, context: PluginContext) -> PluginResult:
        # 检查黑名单
        if context.tool_id in self.blacklist:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f'工具 {context.tool_id} 在黑名单中'
                }
            )

        return PluginResult(
            success=True,
            data={'approved': True}
        )
```

---

## 8. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|--------|
| 1.0 | 2026-03-22 | 初始版本,定义 PluginInterface 和 ToolInterface |

---

**审批状态:** ✅ Approved
**审批人:** SlotAgent Core Team
**审批日期:** 2026-03-22
