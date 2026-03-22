# Tool Definition Data Model

## 概述 (Overview)

Tool 是 SlotAgent 中的一等公民（First-class Citizen），每个工具可以独立配置其插件链，实现细粒度的定制和优化。

## Tool 类定义

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

## 字段说明

### 1. tool_id: str
- **说明**: 工具的唯一标识符
- **约束**:
  - 必填，不能为空
  - 格式: 小写字母、数字、下划线，长度 2-64
  - 正则: `^[a-z][a-z0-9_]{1,63}$`
  - 在 ToolRegistry 中全局唯一
- **示例**: `"web_search"`, `"payment_refund"`, `"data_query"`

### 2. name: str
- **说明**: 工具的显示名称
- **约束**:
  - 必填，不能为空
  - 长度 1-128 字符
  - 用于日志和用户界面显示
- **示例**: `"Web Search"`, `"Payment Refund"`, `"数据查询"`

### 3. description: str
- **说明**: 工具的详细描述
- **约束**:
  - 必填，不能为空
  - 长度 10-1000 字符
  - 清晰说明工具的功能、用途、参数要求
- **示例**: `"Search the web using Google API and return top 10 results"`

### 4. input_schema: Dict[str, Any]
- **说明**: 工具输入参数的 JSON Schema
- **约束**:
  - 必填
  - 必须是有效的 JSON Schema (Draft 7)
  - 必须包含 `"type": "object"` 和 `"properties"` 字段
  - 支持嵌套对象和数组
- **示例**:
```python
{
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100}
    },
    "required": ["query"]
}
```

### 5. execute_func: Callable[[Dict[str, Any]], Any]
- **说明**: 工具的执行函数
- **约束**:
  - 必填
  - 签名: `(params: Dict[str, Any]) -> Any`
  - 应该是可调用对象（函数、lambda、类方法）
  - 应该处理异常并返回有意义的结果
  - 可以是同步或异步函数（Phase 4 仅支持同步）
- **示例**:
```python
def web_search(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params['query']
    limit = params.get('limit', 10)
    # ... search logic ...
    return {'results': [...]}
```

### 6. plugins: Optional[Dict[str, str]]
- **说明**: 工具级插件配置，每层指定一个 plugin_id
- **约束**:
  - 可选字段，默认为 None
  - 当为 None 时，使用全局插件配置
  - 当存在时，工具级插件优先于全局插件
  - 键: 插件层名称 (`"schema"`, `"guard"`, `"healing"`, `"reflect"`, `"observe"`)
  - 值: 插件 ID（必须在 PluginPool 中已注册）
- **示例**:
```python
{
    "schema": "schema_strict",      # 严格验证
    "guard": "guard_payment",       # 支付专用守卫
    "healing": "healing_retry",     # 重试机制
    "reflect": "reflect_simple",    # 简单反思
    "observe": "observe_log"        # 日志观察
}
```

**插件配置策略**:
- 轻量工具（如简单查询）可省略插件，使用默认全局插件
- 高风险工具（如支付、删除）应配置完整插件链
- 性能敏感工具可跳过某些层（如不配置 observe）

### 7. metadata: Optional[Dict[str, Any]]
- **说明**: 工具的元数据，存储额外信息
- **约束**:
  - 可选字段，默认为 None
  - 任意键值对
  - 建议的标准字段:
    - `"version"`: 工具版本
    - `"author"`: 工具作者
    - `"tags"`: 工具标签列表
    - `"risk_level"`: 风险级别（`"low"`, `"medium"`, `"high"`）
    - `"rate_limit"`: 速率限制配置
- **示例**:
```python
{
    "version": "1.0.0",
    "author": "SlotAgent Team",
    "tags": ["search", "web"],
    "risk_level": "low",
    "rate_limit": {"calls_per_minute": 60}
}
```

## 工具配置示例

### 示例1: 简单查询工具（轻量配置）
```python
Tool(
    tool_id="simple_query",
    name="Simple Query",
    description="Query data from local database",
    input_schema={
        "type": "object",
        "properties": {
            "table": {"type": "string"},
            "filter": {"type": "object"}
        },
        "required": ["table"]
    },
    execute_func=simple_query_func,
    plugins=None,  # 使用全局默认插件
    metadata={
        "risk_level": "low",
        "version": "1.0.0"
    }
)
```

### 示例2: 高风险支付工具（完整配置）
```python
Tool(
    tool_id="payment_refund",
    name="Payment Refund",
    description="Refund payment to customer account",
    input_schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "pattern": "^ORD[0-9]{8}$"},
            "amount": {"type": "number", "minimum": 0.01, "maximum": 10000},
            "reason": {"type": "string", "minLength": 10}
        },
        "required": ["order_id", "amount", "reason"]
    },
    execute_func=payment_refund_func,
    plugins={
        "schema": "schema_strict",      # 严格参数验证
        "guard": "guard_human_in_loop", # 人工审批
        "healing": "healing_fallback",  # 失败回退
        "reflect": "reflect_strict",    # 严格反思
        "observe": "observe_metrics"    # 指标监控
    },
    metadata={
        "risk_level": "high",
        "version": "2.1.0",
        "author": "Payment Team",
        "tags": ["payment", "refund", "high-risk"],
        "requires_approval": True
    }
)
```

## 不变式 (Invariants)

### INV-TOOL-1: 唯一标识
- 每个 Tool 的 tool_id 在 ToolRegistry 中必须唯一

### INV-TOOL-2: Schema 有效性
- input_schema 必须是有效的 JSON Schema
- 必须包含 `"type": "object"` 和 `"properties"`

### INV-TOOL-3: 插件存在性
- 如果 plugins 字典不为 None，所有指定的 plugin_id 必须在 PluginPool 中已注册
- 插件层名称必须是有效的5层之一

### INV-TOOL-4: 可执行性
- execute_func 必须是可调用对象
- 调用签名必须接受 Dict[str, Any] 参数

## 设计决策

### D1: 工具级插件配置优先
- **决策**: 工具级插件配置优先于全局插件
- **理由**:
  - 不同工具有不同的可靠性、安全性需求
  - 轻量工具无需完整插件链，减少性能开销
  - 高风险工具需要严格控制，增强安全性
- **权衡**: 增加配置复杂度，但提供更大的灵活性

### D2: input_schema 使用 JSON Schema
- **决策**: 使用 JSON Schema 标准定义输入参数
- **理由**:
  - 工业标准，广泛认可
  - 支持复杂的验证规则（类型、范围、模式、嵌套）
  - 可直接用于 Schema 层插件验证
  - 易于序列化和文档生成
- **权衡**: 需要学习 JSON Schema 语法，但收益大于成本

### D3: execute_func 直接注入
- **决策**: 将执行函数直接作为 Tool 的一个字段
- **理由**:
  - 简单直接，无需额外的工具注册机制
  - 支持任意 Python 函数（普通函数、lambda、类方法）
  - 便于测试（可注入 mock 函数）
- **权衡**: 工具实例不可序列化（包含函数对象），但 Phase 4 不需要序列化

### D4: metadata 开放式设计
- **决策**: metadata 字段允许任意键值对
- **理由**:
  - 不同场景有不同的元数据需求
  - 避免过度设计，保持灵活性
  - 建议标准字段，但不强制
- **权衡**: 可能出现不一致的元数据，但通过文档和最佳实践引导

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义 Tool 类和字段约束
