# Tool System Architecture

## 概述 (Overview)

工具系统是 SlotAgent 的核心组件，管理所有可用工具的注册、查询和执行配置。每个工具都是一等公民，可以独立配置插件链，实现细粒度的优化。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Tool System                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │          ToolRegistry (工具注册中心)         │      │
│  ├──────────────────────────────────────────────┤      │
│  │  - register(tool: Tool) -> None              │      │
│  │  - get_tool(tool_id: str) -> Optional[Tool]  │      │
│  │  - list_tools() -> List[Tool]                ���      │
│  │  - unregister(tool_id: str) -> None          │      │
│  │  - validate_tool(tool: Tool) -> bool         │      │
│  └──────────────────────────────────────────────┘      │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────┐      │
│  │              Tool (工具定义)                 │      │
│  ├──────────────────────────────────────────────┤      │
│  │  - tool_id: str                              │      │
│  │  - name: str                                 │      │
│  │  - description: str                          │      │
│  │  - input_schema: Dict[str, Any]              │      │
│  │  - execute_func: Callable                    │      │
│  │  - plugins: Optional[Dict[str, str]]         │      │
│  │  - metadata: Optional[Dict[str, Any]]        │      │
│  └──────────────────────────────────────────────┘      │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────┐      │
│  │         Plugin Chain Builder                 │      │
│  ├──────────────────────────────────────────────┤      │
│  │  根据工具配置动态组合插件链                  │      │
│  │  优先级: 工具级 > 全局                       │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ↓                                    ↓
  PluginPool (插件池)              CoreScheduler (调度引擎)
```

## 核心组件

### 1. Tool (工具定义)

**职责**:
- 定义工具的所有元信息
- 存储工具的执行函数
- 配置工具级插件链

**关键特性**:
- 一等公民: 每个工具独立存在，独立配置
- 细粒度定制: 每个工具可选择不同的插件组合
- 声明式配置: 通过 plugins 字典声明插件链

详细定义见 `docs/data_models/tool_definition.md`

### 2. ToolRegistry (工具注册中心)

**职责**:
- 管理所有工具的注册和生命周期
- 提供工具查询和检索接口
- 验证工具配置的有效性
- 确保工具 ID 的唯一性

**核心接口**:

```python
class ToolRegistry:
    """
    Tool registry for managing all available tools.

    Thread-safe singleton implementation.
    """

    def __init__(self, plugin_pool: Optional['PluginPool'] = None):
        """
        Initialize ToolRegistry.

        Args:
            plugin_pool: Optional PluginPool instance for validation
        """
        self._tools: Dict[str, Tool] = {}
        self._plugin_pool = plugin_pool
        self._lock = threading.Lock()

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool_id already exists
            ValueError: If tool validation fails
        """
        pass

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get tool by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool instance or None if not found
        """
        pass

    def list_tools(self, tags: Optional[List[str]] = None) -> List[Tool]:
        """
        List all registered tools, optionally filtered by tags.

        Args:
            tags: Optional list of tags to filter

        Returns:
            List of Tool instances
        """
        pass

    def unregister(self, tool_id: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_id: Tool identifier

        Raises:
            KeyError: If tool_id not found
        """
        pass

    def validate_tool(self, tool: Tool) -> bool:
        """
        Validate tool configuration.

        Args:
            tool: Tool instance to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails with reason
        """
        pass
```

**验证规则**:

1. **基础验证**:
   - tool_id 格式正确（`^[a-z][a-z0-9_]{1,63}$`）
   - name 和 description 非空
   - input_schema 是有效的 JSON Schema
   - execute_func 可调用

2. **插件验证** (如果 plugin_pool 存在):
   - 所有配置的 plugin_id 在 PluginPool 中存在
   - 插件层名称有效（schema/guard/healing/reflect/observe）

3. **唯一性验证**:
   - tool_id 在注册表中唯一

### 3. Plugin Chain Builder (插件链构建器)

**职责**:
- 根据工具配置动态组合插件链
- 实现工具级插件优先于全局插件的逻辑
- 与 PluginPool 协作获取插件实例

**构建逻辑**:

```python
def build_plugin_chain(tool: Tool, plugin_pool: PluginPool) -> List[PluginInterface]:
    """
    Build plugin chain for a specific tool.

    Priority: Tool-level plugins > Global plugins

    Args:
        tool: Tool instance
        plugin_pool: PluginPool instance

    Returns:
        Ordered list of plugins (Schema → Guard → Healing → Reflect → Observe)
    """
    # 1. 如果工具有自定义插件配置，使用工具级插件
    if tool.plugins:
        return plugin_pool.get_plugin_chain(tool.tool_id)

    # 2. 否则使用全局插件链
    return plugin_pool.get_plugin_chain(None)
```

这个逻辑已经在 PluginPool.get_plugin_chain() 中实现，ToolRegistry 只需调用即可。

## 执行流程

### 完整工具执行流程

```
1. User/LangGraph 调用
   ↓
2. CoreScheduler.execute(tool_id, params)
   ↓
3. ToolRegistry.get_tool(tool_id)
   ↓
4. PluginPool.get_plugin_chain(tool_id)
   ↓
5. 执行插件链:
   5.1 Schema 层: 验证 params 符合 tool.input_schema
   5.2 Guard 层: 检查权限/触发审批
   5.3 执行层: tool.execute_func(params)
   5.4 Healing 层: 失败自动重试
   5.5 Reflect 层: 验证任务完成度
   5.6 Observe 层: 记录执行日志
   ↓
6. 返回 ToolExecutionContext
```

### 工具注册流程

```
1. 创建 Tool 实例
   tool = Tool(
       tool_id="payment_refund",
       name="Payment Refund",
       description="...",
       input_schema={...},
       execute_func=refund_func,
       plugins={"guard": "guard_human_in_loop"}
   )
   ↓
2. 注册到 ToolRegistry
   registry.register(tool)
   ↓
3. ToolRegistry 验证:
   3.1 检查 tool_id 格式和唯一性
   3.2 检查 input_schema 有效性
   3.3 检查 execute_func 可调用性
   3.4 检查插件配置有效性（通过 PluginPool）
   ↓
4. 注册工具级插件到 PluginPool
   plugin_pool.register_tool_plugins(tool_id, tool.plugins)
   ↓
5. 工具可用
```

## 集成关系

### 与 PluginPool 的集成

```python
# ToolRegistry 初始化时接收 PluginPool 引用
registry = ToolRegistry(plugin_pool=plugin_pool)

# 注册工具时，同步注册工具级插件
def register(self, tool: Tool) -> None:
    # 1. 验证工具
    self.validate_tool(tool)

    # 2. 存储工具
    with self._lock:
        if tool.tool_id in self._tools:
            raise ValueError(f"Tool {tool.tool_id} already registered")
        self._tools[tool.tool_id] = tool

    # 3. 注册工具级插件到 PluginPool
    if tool.plugins and self._plugin_pool:
        self._plugin_pool.register_tool_plugins(tool.tool_id, tool.plugins)
```

### 与 CoreScheduler 的集成

```python
# CoreScheduler 持有 ToolRegistry 引用
class CoreScheduler:
    def __init__(self, plugin_pool: PluginPool, tool_registry: ToolRegistry):
        self.plugin_pool = plugin_pool
        self.tool_registry = tool_registry

    def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
        # 1. 从 ToolRegistry 获取工具
        tool = self.tool_registry.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        # 2. 从 PluginPool 获取插件链
        plugin_chain = self.plugin_pool.get_plugin_chain(tool_id)

        # 3. 执行插件链
        context = self._execute_plugin_chain(tool, params, plugin_chain)

        return context
```

## 设计决策

### D1: ToolRegistry 作为中心化注册表
- **决策**: 使用单一的 ToolRegistry 管理所有工具
- **理由**:
  - 简化工具管理，避免分散
  - 便于全局查询和统计
  - 确保 tool_id 全局唯一性
- **权衡**: 单点依赖，但通过线程安全保证可靠性

### D2: 工具注册时同步到 PluginPool
- **决策**: 工具注册时，自动将工具级插件配置注册到 PluginPool
- **理由**:
  - 保持 PluginPool 和 ToolRegistry 状态同步
  - 避免运行时查找失败
  - 简化使用者的操作流程
- **权衡**: 增加耦合度，但提高一致性

### D3: 支持工具标签过滤
- **决策**: list_tools() 支持按标签过滤
- **理由**:
  - 便于按类别查询工具（如"高风险"、"支付相关"）
  - 支持工具分组和管理
  - 方便生成工具文档
- **权衡**: 增加 API 复杂度，但提供更好的可用性

### D4: validate_tool() 独立方法
- **决策**: 提供公开的 validate_tool() 方法
- **理由**:
  - 支持注册前的验证（快速失败）
  - 便于测试和调试
  - 可用于配置文件的静态检查
- **权衡**: 增加 API 表面积，但提高可测试性

## 扩展性考虑

### 未来扩展方向 (超出 Phase 4 范围)

1. **工具版本管理**:
   - 支持同一工具的多个版本共存
   - tool_id 加上版本号: `payment_refund_v1`, `payment_refund_v2`

2. **工具热加载**:
   - 运行时动态加载新工具
   - 无需重启服务

3. **工具配置持久化**:
   - 将工具配置保存到数据库或配置文件
   - 支持配置版本控制

4. **工具依赖管理**:
   - 工具之间的依赖关系
   - 自动按依赖顺序初始化

5. **异步工具支持**:
   - 支持 async/await 执行函数
   - 并发执行多个工具

6. **工具权限系统**:
   - 基于角色的工具访问控制
   - 细粒度权限管理

## 测试策略

### 单元测试重点

1. **ToolRegistry 测试**:
   - 工具注册、查询、注销
   - 重复 tool_id 注册失败
   - 无效工具注册失败
   - 标签过滤
   - 线程安全

2. **Tool 验证测试**:
   - tool_id 格式验证
   - input_schema 有效性验证
   - execute_func 可调用性验证
   - 插件配置验证

3. **插件链构建测试**:
   - 工具级插件优先
   - 全局插件回退
   - 插件顺序正确

### 集成测试重点

1. **完整执行流程**:
   - 注册工具 → 调度执行 → 插件链运行 → 返回结果

2. **工具级配置生效**:
   - 两个工具使用不同插件
   - 验证插件实际被调用

## 性能考虑

1. **线程安全**: 使用 threading.Lock 保护共享状态
2. **查询优化**: 内存字典存储，O(1) 查找
3. **延迟验证**: 仅在注册时验证，运行时不重复验证

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义工具系统架构和 ToolRegistry 接口
