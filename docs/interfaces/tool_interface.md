# Tool Interface Specification

## 概述 (Overview)

本文档定义 Tool 相关的接口规范，包括 Tool 类、ToolRegistry 接口和工具执行函数的契约。

## Tool 类接口

### 类定义

```python
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

@dataclass
class Tool:
    """
    Tool definition - first-class citizen in SlotAgent.

    Each tool can independently configure its plugin chain for
    fine-grained optimization.

    Attributes:
        tool_id: Unique tool identifier
        name: Display name
        description: Detailed description
        input_schema: JSON Schema for input validation
        execute_func: Tool execution function
        plugins: Tool-level plugin configuration (layer -> plugin_id)
        metadata: Additional metadata
    """
    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    execute_func: Callable[[Dict[str, Any]], Any]
    plugins: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
```

### 字段约束

详细字段说明见 `docs/data_models/tool_definition.md`

### 前置条件 (Preconditions)

**PRE-TOOL-1**: tool_id 格式
- 必须匹配正则: `^[a-z][a-z0-9_]{1,63}$`
- 示例: `"web_search"`, `"payment_refund"`

**PRE-TOOL-2**: 必填字段非空
- name, description 不能为空字符串
- input_schema 不能为空字典

**PRE-TOOL-3**: input_schema 有效性
- 必须是有效的 JSON Schema (Draft 7)
- 必须包含 `"type": "object"` 和 `"properties"`

**PRE-TOOL-4**: execute_func 可调用
- 必须是可调用对象: `callable(execute_func) == True`
- 签名: `(params: Dict[str, Any]) -> Any`

**PRE-TOOL-5**: plugins 有效性 (如果不为 None)
- 键必须是有效层名称: schema/guard/healing/reflect/observe
- 值必须是字符串（plugin_id）

### 后置条件 (Postconditions)

**POST-TOOL-1**: 实例创建成功
- Tool 实例可正常访问所有字段
- execute_func 可被调用

## ToolRegistry 接口

### 接口定义

```python
from threading import Lock
from typing import Dict, List, Optional

class ToolRegistry:
    """
    Tool registry for managing all available tools.

    Provides thread-safe tool registration, lookup, and validation.
    """

    def __init__(self, plugin_pool: Optional['PluginPool'] = None):
        """
        Initialize ToolRegistry.

        Args:
            plugin_pool: Optional PluginPool for plugin validation

        Postconditions:
            - Empty tool registry created
            - Thread lock initialized
        """
        pass

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Preconditions:
            - tool.tool_id not already registered
            - tool passes validation (validate_tool returns True)

        Args:
            tool: Tool instance to register

        Postconditions:
            - Tool stored in registry
            - Tool-level plugins registered in PluginPool (if configured)

        Raises:
            ValueError: If tool_id already exists
            ValueError: If tool validation fails
        """
        pass

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get tool by ID.

        Preconditions:
            - None (tool_id can be any string)

        Args:
            tool_id: Tool identifier

        Returns:
            Tool instance if found, None otherwise

        Postconditions:
            - Registry state unchanged
        """
        pass

    def list_tools(self, tags: Optional[List[str]] = None) -> List[Tool]:
        """
        List all registered tools, optionally filtered by tags.

        Preconditions:
            - None

        Args:
            tags: Optional list of tags to filter
                  (checks metadata['tags'])

        Returns:
            List of Tool instances
            Empty list if no tools or no matches

        Postconditions:
            - Registry state unchanged
        """
        pass

    def unregister(self, tool_id: str) -> None:
        """
        Unregister a tool.

        Preconditions:
            - tool_id exists in registry

        Args:
            tool_id: Tool identifier

        Postconditions:
            - Tool removed from registry
            - Tool-level plugins remain in PluginPool (not removed)

        Raises:
            KeyError: If tool_id not found
        """
        pass

    def validate_tool(self, tool: Tool) -> bool:
        """
        Validate tool configuration.

        Preconditions:
            - tool is a Tool instance

        Args:
            tool: Tool instance to validate

        Returns:
            True if valid (never returns False - raises instead)

        Postconditions:
            - Registry state unchanged

        Raises:
            ValueError: If validation fails with detailed reason
        """
        pass
```

### 验证规则

**validate_tool() 检查项**:

1. **tool_id 验证**:
   - 格式: `^[a-z][a-z0-9_]{1,63}$`
   - 错误消息: `"Invalid tool_id format"`

2. **name 和 description 验证**:
   - name: 长度 1-128
   - description: 长度 10-1000
   - 错误消息: `"Invalid name/description length"`

3. **input_schema 验证**:
   - 包含 `"type": "object"`
   - 包含 `"properties"`
   - 错误消息: `"Invalid input_schema: must have type=object and properties"`

4. **execute_func 验证**:
   - `callable(execute_func) == True`
   - 错误消息: `"execute_func is not callable"`

5. **plugins 验证** (如果 plugin_pool 存在):
   - 所有层名称有效
   - 所有 plugin_id 在 PluginPool 中存在
   - 错误消息: `"Invalid plugin layer: {layer}"` 或 `"Plugin {plugin_id} not found"`

### 线程安全保证

**TS-1**: register() 线程安全
- 使用锁保护 tool_id 唯一性检查和插入

**TS-2**: get_tool() 线程安全
- 字典读取操作，Python 保证原子性

**TS-3**: unregister() 线程安全
- 使用锁保护删除操作

**TS-4**: list_tools() 线程安全
- 复制工具列表，避免迭代时修改

## 工具执行函数接口

### 函数签名

```python
def tool_function(params: Dict[str, Any]) -> Any:
    """
    Tool execution function signature.

    Preconditions:
        - params conforms to tool.input_schema (validated by Schema plugin)

    Args:
        params: Input parameters (already validated)

    Returns:
        Any: Tool execution result
            - Can be any JSON-serializable type
            - Should be meaningful and structured

    Raises:
        Exception: Any exception indicates tool execution failure
            - Will be caught by CoreScheduler
            - May trigger Healing plugin retry

    Postconditions:
        - If successful: returns meaningful result
        - If failed: raises exception with clear message
    """
    pass
```

### 执行函数契约

**EF-1**: 参数验证已完成
- Schema 插件已验证 params
- execute_func 可假定 params 有效

**EF-2**: 异常处理
- 应该捕获预期异常并转换为有意义的错误消息
- 未捕获异常将触发 Healing 插件

**EF-3**: 返回值要求
- 应该返回结构化数据（Dict、List等）
- 避免返回 None（除非明确表示"无结果"）
- 建议格式:
  ```python
  {
      "success": True,
      "data": {...},
      "message": "..."
  }
  ```

**EF-4**: 幂等性建议
- 高风险操作（支付、删除）应确保幂等性
- 使用唯一 ID 防止重复执行

### 执行函数示例

#### 示例1: 简单查询工具
```python
def simple_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """Simple database query tool."""
    table = params['table']
    filter_cond = params.get('filter', {})

    try:
        # Query logic
        results = db.query(table, filter_cond)
        return {
            "success": True,
            "count": len(results),
            "data": results
        }
    except DatabaseError as e:
        raise Exception(f"Database query failed: {str(e)}")
```

#### 示例2: 高风险支付工具
```python
def payment_refund(params: Dict[str, Any]) -> Dict[str, Any]:
    """Payment refund tool with idempotency."""
    order_id = params['order_id']
    amount = params['amount']
    reason = params['reason']

    # Check idempotency
    existing = refund_db.get_by_order(order_id)
    if existing:
        return {
            "success": True,
            "refund_id": existing.refund_id,
            "message": "Refund already processed",
            "idempotent": True
        }

    try:
        # Execute refund
        refund_id = payment_api.refund(order_id, amount, reason)

        # Record in database
        refund_db.create(order_id, refund_id, amount, reason)

        return {
            "success": True,
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": amount,
            "message": "Refund successful"
        }
    except PaymentAPIError as e:
        raise Exception(f"Payment API failed: {str(e)}")
```

## 使用示例

### 完整工具注册和执行流程

```python
# 1. 创建 PluginPool 和 ToolRegistry
plugin_pool = PluginPool()
tool_registry = ToolRegistry(plugin_pool)

# 2. 注册全局插件
plugin_pool.register_global_plugin(SchemaDefault())
plugin_pool.register_global_plugin(GuardDefault())
plugin_pool.register_global_plugin(LogPlugin())

# 3. 定义工具
payment_tool = Tool(
    tool_id="payment_refund",
    name="Payment Refund",
    description="Refund payment to customer",
    input_schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number", "minimum": 0.01}
        },
        "required": ["order_id", "amount"]
    },
    execute_func=payment_refund,
    plugins={
        "schema": "schema_strict",
        "guard": "guard_human_in_loop"
    },
    metadata={
        "risk_level": "high",
        "tags": ["payment", "refund"]
    }
)

# 4. 注册工具
tool_registry.register(payment_tool)

# 5. 创建 CoreScheduler
scheduler = CoreScheduler(plugin_pool, tool_registry)

# 6. 执行工具
result = scheduler.execute(
    tool_id="payment_refund",
    params={"order_id": "ORD12345678", "amount": 99.99}
)

# 7. 查询工具
tool = tool_registry.get_tool("payment_refund")
all_tools = tool_registry.list_tools()
payment_tools = tool_registry.list_tools(tags=["payment"])
```

## 错误处理

### 注册阶段错误

1. **重复 tool_id**:
   ```python
   ValueError: Tool payment_refund already registered
   ```

2. **无效 tool_id 格式**:
   ```python
   ValueError: Invalid tool_id format: Payment-Refund
   ```

3. **无效 input_schema**:
   ```python
   ValueError: Invalid input_schema: must have type=object and properties
   ```

4. **插件不存在**:
   ```python
   ValueError: Plugin guard_payment not found in PluginPool
   ```

### 执行阶段错误

1. **工具不存在**:
   ```python
   ValueError: Tool unknown_tool not found
   ```

2. **参数验证失败**:
   - Schema 插件返回 `success=False, should_continue=False`
   - CoreScheduler 短路返回

3. **执行函数异常**:
   - 异常被 CoreScheduler 捕获
   - status 设为 FAILED
   - 可能触发 Healing 插件

## 不变式 (Invariants)

**INV-TR-1**: 唯一性
- 任意时刻，所有已注册工具的 tool_id 唯一

**INV-TR-2**: 有效性
- 所有已注册工具都通过 validate_tool() 验证

**INV-TR-3**: 同步性
- 工具的 plugins 配置与 PluginPool 中的工具级插件配置同步

**INV-TR-4**: 线程安全性
- 并发操作不会导致数据竞争或不一致状态

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义 Tool 和 ToolRegistry 接口契约
