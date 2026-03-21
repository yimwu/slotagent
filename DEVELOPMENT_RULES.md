# DEVELOPMENT_RULES.md

SlotAgent 开发规范和质量保证指南，基于 SDD（规格说明驱动开发）和 TDD（测试驱动开发）范式。

---

## 1. Specification-Driven Development (SDD) 规范

### 1.1 规格文档管理

**规格文档位置和分类：**
```
docs/
├── architecture/              # 架构设计文档
│   ├── overall_architecture.md    # 整体6层架构说明
│   ├── core_scheduler.md          # 核心调度引擎设计
│   ├── plugin_system.md           # 插件池和插件执行链设计
│   ├── tool_system.md             # 工具中心和工具配置设计
│   ├── hook_system.md             # Hook事件系统设计
│   └── approval_workflow.md        # 审批流程和状态机设计
├── interfaces/                # 接口规格说明
│   ├── core_interfaces.md         # 核心接口定义（类型、方法签名）
│   ├── plugin_interface.md        # 插件接口规范
│   ├── tool_interface.md          # 工具接口规范
│   ├── hook_interface.md          # Hook接口规范
│   └── approval_interface.md       # 审批接口规范
├── workflows/                 # 流程规格说明
│   ├── tool_execution_flow.md     # 工具执行全流程（独立模式）
│   ├── langgraph_integration.md   # LangGraph集成流程
│   ├── approval_process.md        # 人工审批流程
│   └── error_handling.md          # 错误处理和自愈流程
├── data_models/               # 数据模型和状态定义
│   ├── plugin_context.md          # 插件执行上下文数据结构
│   ├── tool_execution_context.md  # 工具执行上下文
│   ├── hook_events.md             # Hook事件数据结构
│   └── approval_state.md           # 审批状态定义和转移
└── requirements/              # 需求和验收标准
    ├── functional_requirements.md  # 功能需求
    └── non_functional_requirements.md  # 非功能需求（性能、可靠性等）
```

### 1.2 规格文档编写标准

**每份规格文档必须包含：**

1. **概述（Overview）**
   - 组件/流程名称和定位
   - 责任边界（what it does / what it doesn't）
   - 与其他组件的交互关系

2. **设计原理（Design Principles）**
   - 为什么这样设计
   - 关键设计决策和权衡

3. **接口定义（Interface Specification）**
   - 输入（参数、类型、约束）
   - 输出（返回值、类型、保证）
   - 异常和错误情况
   - 示例代码

4. **流程和状态（Workflow & State Machines）**
   - 执行流程图（Mermaid或文本描述）
   - 状态转移图
   - 边界情况和异常路径

5. **性能和可靠性要求（Non-Functional Requirements）**
   - 延迟要求
   - 吞吐量要求
   - 可靠性保证（如重试、超时等）

6. **变更历史（Changelog）**
   - 记录规格的演进

### 1.3 接口设计规范（核心）

**所有对外暴露的接口必须满足：**

1. **类型安全**
   - 所有参数和返回值必须有明确的类型定义
   - 使用Python类型注解（从3.8+开始）

2. **契约清晰**
   - 前置条件（Precondition）：调用者必须满足的条件
   - 后置条件（Postcondition）：方法返回后的保证
   - 不变量（Invariant）：方法执行前后必须保持的条件

3. **向后兼容性**
   - 接口变更（参数增删、返回值改变）需要在规格审批时讨论，不允许无通知改变
   - 如需破坏兼容，必须在版本号和迁移指南中说明

### 1.4 设计审批流程

1. **草稿阶段**
   - 开发者/架构师编写设计文档
   - 文档位置：`docs/` 对应目录

2. **评审阶段**
   - 提交PR或Issue，邀请核心贡献者评审
   - 评审清单：
     - [ ] 设计是否符合项目架构原理
     - [ ] 接口定义是否清晰无歧义
     - [ ] 是否考虑了错误情况和边界
     - [ ] 与其他模块的交互是否明确
     - [ ] 性能和可靠性是否有保证

3. **定案阶段**
   - 获得至少1名核心审查者的Approve
   - 规格文档标记为"Approved"
   - 作为后续TDD测试的唯一依据

### 1.5 接口变更管理

**规格变更流程：**
1. 新增接口：提交新规格文档，走设计审批
2. 修改接口：重新审批，记录变更原因
3. 删除接口：确认无依赖，标记为deprecated后可删除

---

## 2. Test-Driven Development (TDD) 规范

### 2.1 TDD工作流

**每个功能遵循三个阶段：**

1. **红色（Red）：先写失败的测试**
   - 根据规格文档编写测试用例
   - 确保测试能完整覆盖接口规范和边界情况
   - 执行测试，确认当前测试失败（代码还未实现）

2. **绿色（Green）：快速实现使测试通过**
   - 编写最小化代码使测试通过
   - 不需要考虑优化，只要逻辑正确

3. **蓝色（Blue）：重构和优化**
   - 清理代码、提取公共逻辑
   - 优化性能和可读性
   - 确保所有测试仍然通过

### 2.2 测试代码结构

**目录结构：**
```
tests/
├── conftest.py                    # 全局fixtures和test configuration
├── unit/                          # 单元测试（测试单一模块/类）
│   ├── test_core_scheduler.py
│   ├── test_plugin_pool.py
│   ├── test_hook_manager.py
│   ├── test_tool_registry.py
│   ├── test_approval_manager.py
│   └── plugins/
│       ├── test_schema_plugins.py
│       ├── test_guard_plugins.py
│       ├── test_healing_plugins.py
│       ├── test_reflect_plugins.py
│       └── test_observe_plugins.py
├── integration/                   # 集成测试（测试多个模块协作）
│   ├── test_tool_execution_flow.py          # 完整工具执行流程
│   ├── test_approval_workflow.py            # 审批流程E2E
│   ├── test_plugin_chain_execution.py       # 插件链执行顺序
│   ├── test_hook_event_flow.py              # Hook事件分发
│   └── test_langgraph_integration.py        # LangGraph集成
├── fixtures/                      # 测试数据和Mock对象
│   ├── sample_plugins.py          # 示例插件（用于测试）
│   ├── sample_tools.py            # 示例工具定义
│   └── mock_llm.py                # Mock LLM实例
└── performance/                   # 性能测试（可选）
    └── test_execution_performance.py
```

### 2.3 单元测试编写规范

**测试用例命名规则：**
```
test_{模块}_{被测试方法}_{场景描述}

示例：
test_core_scheduler_execute_tool_with_valid_params
test_plugin_pool_respect_tool_level_plugin_priority
test_hook_manager_emit_event_to_all_subscribers
test_approval_manager_state_transition_from_pending_to_approved
```

**测试用例结构（AAA 模式）：**
```python
def test_example():
    # Arrange: 准备测试数据和上下文
    tool_id = "weather_query"
    params = {"location": "Beijing"}
    expected_plugin_chain = [SchemaPlugin, GuardPlugin]

    # Act: 执行被测试的操作
    result = scheduler.execute(tool_id, params)

    # Assert: 验证结果是否符合预期
    assert result.success == True
    assert result.plugin_chain_executed == expected_plugin_chain
```

**测试覆盖范围：**

| 模块 | 覆盖率目标 | 测试重点 |
|------|----------|--------|
| core_scheduler（核心调度引擎） | ≥95% | 插件链执行顺序、事件分发、状态管理 |
| plugin_pool（插件池） | ≥90% | 插件注册、优先级、选择逻辑 |
| hook_manager（Hook管理） | ≥90% | 事件发送、订阅者回调、并发安全 |
| tool_registry（工具注册中心） | ≥85% | 工具注册、配置验证、查询 |
| approval_manager（审批管理） | ≥90% | 状态转移、超时处理、回调触发 |
| 所有插件（Plugin）实现 | ≥80% | 正常情况、异常情况、边界值 |

### 2.4 测试用例的关键场景

**针对SlotAgent核心逻辑，必须覆盖以下场景：**

#### A. 插件链执行（关键）
- [ ] 插件链按正确顺序执行（Schema → Guard → Execute → Healing → Reflect）
- [ ] 任意插件返回失败时，后续插件仍执行（如果设计要求）
- [ ] 工具级插件配置覆盖全局插件
- [ ] 跳过未配置的插件层

#### B. Guard护栏层（关键）
- [ ] Guard插件拦截高危操作时触发on_guard_block Hook
- [ ] GuardHumanInLoop插件正确生成approval_id并触发on_wait_approval
- [ ] 在审批待机状态，执行不继续

#### C. 自愈流程（重要）
- [ ] 工具执行失败时自动触发Healing插件
- [ ] Healing插件重试次数达到上限时正确失败
- [ ] 重试间隔遵循配置

#### D. 审批流程（重要）
- [ ] 审批待机时状态为pending_approval
- [ ] approve() 调用后继续执行，触发on_after_exec
- [ ] reject() 调用后终止执行，不再执行后续插件
- [ ] 审批超时自动reject（如果设计要求）

#### E. Hook事件（重要）
- [ ] 每个关键执行点都触发正确的Hook事件（before/after/fail/block）
- [ ] Hook事件携带的数据完整正确
- [ ] 多个订阅者能同时接收Hook事件
- [ ] Hook执行异常不影响主流程

#### F. 并发和状态安全（重要）
- [ ] 多个工具同时执行时状态互不影响
- [ ] 插件池线程安全
- [ ] Hook订阅和发送线程安全

#### G. 错误处理和边界（必须）
- [ ] 工具不存在时正确错误
- [ ] 参数不符合schema时正确错误
- [ ] 插件执行异常时正确处理和恢复
- [ ] 非法状态转移时拒绝

### 2.5 集成测试编写规范

**集成测试应覆盖完整的业务流程：**

1. **工具执行全流程测试**
   ```
   初始化系统
   → 注册插件和工具
   → 调用execute()
   → 验证插件链执行
   → 验证Hook事件
   → 验证返回结果
   ```

2. **审批流程端到端测试**
   ```
   调用需要审批的工具
   → 验证触发on_wait_approval
   → 模拟人工approve
   → 验证继续执行并返回结果
   ```

3. **LangGraph集成测试**
   ```
   初始化LangGraph + SlotAgent
   → 创建工具调用节点
   → 验证LangGraph能正确调用execute()
   → 验证结果返回和流程继续
   ```

### 2.6 测试环境和工具

**使用的测试框架和工具：**
```
pytest                          # 测试框架
pytest-cov                      # 覆盖率统计
pytest-mock                     # Mock支持
pytest-asyncio                  # 异步支持（如需要）
responses                       # HTTP Mock（如需要）
```

**conftest.py中应包含的fixtures：**
```python
@pytest.fixture
def sample_plugins():
    """返回示例插件集合"""
    return {
        'schema': SchemaDefault(),
        'guard': GuardDefault(),
        'healing': HealingSimple(),
    }

@pytest.fixture
def sample_tool_def():
    """返回示例工具定义"""
    return ToolDefinition(...)

@pytest.fixture
def scheduler(sample_plugins):
    """返回已初始化的调度引擎"""
    sched = CoreScheduler()
    for layer, plugin in sample_plugins.items():
        sched.register_plugin(plugin, layer)
    return sched
```

### 2.7 测试执行和报告

**本地测试运行：**
```bash
# 运行所有测试
pytest tests/

# 运行单个测试模块
pytest tests/unit/test_core_scheduler.py

# 运行单个测试用例
pytest tests/unit/test_core_scheduler.py::test_execute_tool_with_valid_params

# 生成覆盖率报告
pytest --cov=src/slotagent tests/

# 生成HTML覆盖率报告
pytest --cov=src/slotagent --cov-report=html tests/
```

**覆盖率报告标准：**
- 整体覆盖率 ≥ 85%
- 核心模块（core/）≥ 95%
- 插件模块 ≥ 80%
- 生成 `htmlcov/index.html` 作为报告

---

## 3. 代码规范

### 3.1 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `CoreScheduler`, `PluginPool`, `SchemaValidator` |
| 函数/方法名 | snake_case | `register_plugin()`, `execute_tool()`, `emit_hook()` |
| 常量 | UPPER_SNAKE_CASE | `PLUGIN_SCHEMA_LAYER`, `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 私有属性/方法 | _snake_case | `_plugin_registry`, `_hook_manager`, `_validate_params()` |
| 模块文件名 | lowercase with underscore | `core_scheduler.py`, `plugin_pool.py` |
| 包名 | lowercase | `slotagent`, `plugins`, `tools` |
| 异常类 | PascalCase + "Error" 或 "Exception" | `PluginNotFoundError`, `InvalidToolException` |

### 3.2 类型注解规范

**所有公共接口必须包含类型注解：**

```python
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

# 函数类型注解
def register_plugin(self, plugin: PluginInterface, layer: str) -> bool:
    """
    注册插件到插件池。

    Args:
        plugin: 实现PluginInterface的插件实例
        layer: 插件层（'schema', 'guard', 'healing', 'reflect', 'observe'）

    Returns:
        True if registration successful, False otherwise

    Raises:
        ValueError: if layer is invalid or plugin_id already exists
    """
    pass

# 类型定义
@dataclass
class PluginContext:
    """插件执行上下文"""
    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    layer: str
    previous_result: Optional[Any] = None
```

**类型注解最佳实践：**
- 使用 `typing` 模块的类型（`List`, `Dict`, `Optional`, `Union` 等）
- 对于复杂类型，定义数据类（`@dataclass` 或 `TypedDict`）
- 对于返回值，使用 `Union` 或多态来表示多种可能
- 避免使用 `Any` 除非必要

### 3.3 文档字符串规范

**所有公共类、模块、函数必须有 docstring（Google风格）：**

```python
def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionResult:
    """
    直接执行指定工具。

    根据工具配置加载插件链，按顺序执行：
    Schema校验 → Guard护栏 → 工具执行 → 自愈 → 反思

    Args:
        tool_id: 工具ID，必须已注册
        params: 工具参数，必须符合工具的input_schema

    Returns:
        ToolExecutionResult: 包含执行状态、结果、错误信息等

        例：
        {
            'status': 'success',  # success/pending/failed
            'result': {...},
            'error': None,
            'approval_id': None,
            'execution_time': 0.5
        }

    Raises:
        ToolNotFoundError: 如果tool_id不存在
        SchemaValidationError: 如果params不符合schema
        ToolExecutionError: 如果工具执行出错

    Warns:
        GuardBlockedWarning: 如果被Guard插件拦截（触发on_guard_block Hook）

    Examples:
        >>> scheduler = CoreScheduler()
        >>> result = scheduler.execute('weather_query', {'location': 'Beijing'})
        >>> print(result.status)
        'success'

    Notes:
        - 该方法是主要执行入口，适用于集成模式
        - 如果需要人工审批，会返回 status='pending' 和 approval_id
        - 调用方应订阅 on_wait_approval Hook 以处理审批流程
    """
    pass
```

### 3.4 代码注释规范

**使用注释的原则：**
- 注释解释"为什么"，而不是"是什么"
- 代码本身应该足够清晰，使得不需要注释就能理解"做什么"
- 对复杂逻辑、非直观的设计决策、边界情况使用注释

```python
# 好的注释
# 为了确保工具级插件优先使用，遍历工具配置而非全局配置
plugin_config = tool_definition.plugins.get(layer) or global_plugins.get(layer)

# 坏的注释（冗余）
# 获取插件
plugin = plugin_pool.get(plugin_id)

# TODO和FIXME的使用
# TODO: 实现LLM智能重试策略（当前仅支持固定延迟）
# FIXME: 线程安全性待验证，需要加锁保护_plugin_registry
```

### 3.5 代码格式和风格

**遵循 PEP8 标准，使用自动格式化工具：**

```bash
# 安装工具
pip install black flake8 isort

# 格式化代码
black src/slotagent tests/

# 检查代码风格
flake8 src/slotagent tests/ --max-line-length=100

# 排序导入
isort src/slotagent tests/
```

**pyproject.toml 配置示例：**
```toml
[tool.black]
line-length = 100
target-version = ['py38']

[tool.isort]
profile = "black"
line_length = 100

[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "E501"]  # E501由black处理
```

**代码风格约定：**
- 行长限制：100字符（考虑中文注释）
- 缩进：4个空格
- 导入顺序：标准库 → 第三方 → 本地模块，每组之间空一行
- 每个模块文件头部包含copyright声明和brief说明

```python
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
SlotAgent核心调度引擎实现。

负责插件链执行、事件分发和状态管理的极小内核。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult
```

---

## 4. 质量保障

### 4.1 代码审查流程

**所有代码提交必须通过代码审查（Code Review）：**

1. **自我检查**
   - [ ] 代码是否遵循命名规范
   - [ ] 是否有类型注解
   - [ ] docstring是否完整
   - [ ] 是否有适当的错误处理
   - [ ] 测试覆盖是否充分

2. **提交PR**
   - 标题格式：`[module] brief description` 如 `[core] implement plugin chain execution`
   - 描述包含：
     - 关联的Issue或规格文档
     - 实现概述
     - 关键设计决策
     - 测试覆盖说明
   - Checklist
   ```
   - [ ] 代码遵循DEVELOPMENT_RULES规范
   - [ ] 新增/修改了对应的规格文档
   - [ ] 编写了单元测试，覆盖率 ≥ 80%
   - [ ] 通过了所有本地测试和lint检查
   - [ ] commit信息符合规范
   ```

3. **审查者检查**
   - [ ] 实现是否符合规格文档（SDD）
   - [ ] 测试是否完整覆盖所有场景
   - [ ] 代码是否清晰易读
   - [ ] 是否有性能问题
   - [ ] 是否有安全隐患
   - [ ] 是否符合架构原则

4. **批准和合并**
   - 至少需要1名核心审查者的Approve
   - 所有CI检查（测试、lint、覆盖率）必须通过
   - Squash并合并到主分支

### 4.2 静态代码检查

**CI/CD流程中的自动检查（见 .github/workflows）：**

```yaml
# GitHub Actions示例
name: Code Quality Checks

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Lint检查
      - name: Lint with flake8
        run: flake8 src/slotagent tests/

      # 类型检查
      - name: Type check with mypy
        run: mypy src/slotagent --ignore-missing-imports

      # 测试和覆盖率
      - name: Run tests with coverage
        run: pytest --cov=src/slotagent --cov-report=xml tests/

      # 覆盖率检查
      - name: Check coverage
        run: |
          coverage report --fail-under=85
```

**本地运行检查（commit前必须）：**
```bash
# 完整检查脚本
#!/bin/bash
set -e

echo "Running code quality checks..."

# Format check
black --check src/slotagent tests/

# Lint check
flake8 src/slotagent tests/

# Type check (optional, 如果项目规模够大)
# mypy src/slotagent

# Test and coverage
pytest --cov=src/slotagent --cov-report=term tests/ \
  --cov-fail-under=85

echo "All checks passed!"
```

### 4.3 复杂度指标

**代码圈复杂度（Cyclomatic Complexity）限制：**
- 函数圈复杂度 ≤ 10
- 类平均复杂度 ≤ 8

**如何检查（使用radon）：**
```bash
pip install radon
radon cc -a src/slotagent  # Average complexity
radon mi src/slotagent     # Maintainability index
```

**过于复杂的代码应该重构：**
- 分解为多个小函数
- 使用设计模式简化逻辑
- 提取共同逻辑到helper函数

---

## 5. SlotAgent 特定规范

### 5.1 插件开发规范

**所有插件必须实现 PluginInterface：**

```python
class PluginInterface(ABC):
    """所有插件的基类"""

    # 类属性
    layer: str  # 插件层名称
    plugin_id: str  # 全局唯一ID

    @abstractmethod
    def validate(self) -> bool:
        """验证插件配置是否有效"""
        pass

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """执行插件逻辑"""
        pass
```

**插件类命名规范：**
- 格式：`{LayerName}{PluginName}` 如 `SchemaDefault`, `GuardHumanInLoop`, `HealingRetry`
- 插件ID：lowercase with underscores，如 `schema_default`, `guard_human_in_loop`

**插件测试要求：**
- 每个插件必须有单独的测试文件
- 覆盖正常情况、异常情况、边界值
- 测试插件在链中与其他插件的交互

### 5.2 工具定义规范

**工具定义必须包含完整的元数据和配置：**

```python
@dataclass
class ToolDefinition:
    # 标识
    tool_id: str                          # 全局唯一ID，lowercase_with_underscore
    name: str                             # 工具名称，可读
    description: str                      # 工具描述，说明功能和场景

    # 接口
    input_schema: Dict[str, Any]          # JSON Schema格式的参数定义
    output_schema: Dict[str, Any]         # 返回值的JSON Schema（可选）

    # 执行器
    executor: Callable                    # 实际执行工具的可调用对象

    # 插件配置
    plugins: Dict[str, str]               # 每层的插件选择
    # 示例：
    # {
    #     'schema': 'schema_strict',
    #     'guard': 'guard_human_in_loop',
    #     'healing': 'healing_retry',
    #     'reflect': 'reflect_simple',
    #     'observe': 'observe_log'
    # }

    # 元数据
    timeout: Optional[float] = None       # 执行超时（秒）
    max_retries: int = 0                  # 默认最大重试次数
    tags: List[str] = field(default_factory=list)  # 标签，如['payment', 'high-risk']
```

**工具配置验证：**
- tool_id必须唯一
- executor必须是可调用的
- input_schema必须符合JSON Schema规范
- plugins中指定的插件必须已注册

### 5.3 Hook事件规范

**Hook名称和时机：**

| Hook名称 | 触发时机 | 携带数据 |
|---------|---------|--------|
| `on_before_exec` | 工具执行前，Schema验证通过后 | tool_id, tool_name, params |
| `on_after_exec` | 工具执行成功后 | tool_id, result, execution_time |
| `on_fail` | 工具执行失败（且Healing未恢复） | tool_id, error, retry_count |
| `on_guard_block` | Guard插件拦截 | tool_id, reason, block_rule |
| `on_wait_approval` | GuardHumanInLoop插件等待审批 | approval_id, tool_id, params, approval_requester |
| `on_approve` | 审批通过 | approval_id, tool_id, approved_by |
| `on_reject` | 审批拒绝 | approval_id, tool_id, reject_reason |

**Hook订阅规范：**
```python
# 订阅Hook
hook_manager.subscribe('on_before_exec', my_callback_function)

# 回调函数签名
def my_callback_function(event: HookEvent) -> None:
    """处理Hook事件"""
    # 不应该抛出异常，若有异常应该自己处理
    try:
        # 处理逻辑
        pass
    except Exception as e:
        logger.error(f"Error handling hook event: {e}")
```

---

## 6. 版本管理和发布

### 6.1 版本号规范

遵循 Semantic Versioning (SemVer)：`MAJOR.MINOR.PATCH`

- **MAJOR**：不向后兼容的API变更
- **MINOR**：向后兼容的功能新增
- **PATCH**：bug修复

示例：`0.1.0` → `0.2.0` → `0.2.1` → `1.0.0`

### 6.2 Commit信息规范

遵循 Angular Commit Message Format：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type 包括：**
- `feat`: 新功能
- `fix`: bug修复
- `refactor`: 代码重构（不改变功能）
- `perf`: 性能优化
- `test`: 测试相关
- `docs`: 文档更新
- `chore`: 构建、依赖更新等

**示例：**
```
feat(plugin_pool): implement plugin priority resolution

添加插件优先级机制，工具级插件配置优先于全局插件。
实现了PluginPool.select_plugin()方法。

Closes #123
```

---

## 7. 附录：检查清单

### 新功能开发清单
- [ ] 规格文档已编写并通过审批
- [ ] 单元测试已编写，覆盖率 ≥ 80%
- [ ] 集成测试已编写（如适用）
- [ ] 所有测试通过
- [ ] 代码通过lint和类型检查
- [ ] 代码审查通过
- [ ] API文档已更新
- [ ] CHANGELOG已更新

### PR提交清单
- [ ] PR标题遵循规范
- [ ] 关联了对应的Issue或规格文档
- [ ] 描述清晰，包括设计决策说明
- [ ] commit信息规范
- [ ] 自测覆盖了关键场景
- [ ] 无调试代码或print语句
- [ ] 无硬编码的配置和密钥

### 代码审查清单
- [ ] 代码实现符合规格（SDD）
- [ ] 测试完整、合理
- [ ] 代码清晰、易读、有文档
- [ ] 没有明显的性能问题
- [ ] 没有安全隐患
- [ ] 符合项目架构和规范
- [ ] 向后兼容或有清楚的迁移说明

---

**文档版本：1.0**
**最后更新：2026-03-21**
**维护者：SlotAgent 核心团队**
