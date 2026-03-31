# SlotAgent

[English](README.md) | [中文](README.zh-CN.md)

[![Release](https://img.shields.io/github/v/release/yimwu/slotagent?include_prereleases)](https://github.com/yimwu/slotagent/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-94.79%25-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-243%20passed-brightgreen.svg)]()
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

**SlotAgent** 是一个工业级自研 LLM Agent 执行引擎，采用插件插槽架构，强调松耦合和灵活扩展。

## 🎯 项目愿景

SlotAgent 是一个**生产就绪的工具执行引擎**，专为可靠、安全、可观测的 LLM Agent 系统而设计。

### 核心设计原则

- **🔧 极小内核** - 核心调度器仅负责编排，零业务逻辑，无第三方依赖
- **🧩 插件插槽架构** - 5层插件系统（Schema/Guard/Healing/Reflect/Observe），组件可热插拔
- **⚙️ 工具级定制** - 每个工具独立配置插件链，实现最优性能
- **🔒 生产就绪** - 内置人工审批工作流、全面可观测性和审计日志
- **🔄 双模式兼容** - 可独立运行或嵌入 LangGraph/LangChain 作为执行层

---

## ✨ 核心特性

### 🏗️ 6层架构

```
┌─────────────────────────────────────────────────────────┐
│  1. 使用模式                                             │
│     独立模式（Independent）│  嵌入模式（LangGraph）       │
├─────────────────────────────────────────────────────────┤
│  2. 接口层                                               │
│     • run(query) - 自然语言工具交互                       │
│     • execute(tool, params) - 直接工具执行               │
│     • Hook API（事件订阅）                               │
│     • 插件管理 API                                       │
├─────────────────────────────────────────────────────────┤
│  3. 核心调度器（极小内核）                               │
│     插件链执行 → 事件分发 → 状态管理                     │
├─────────────────────────────────────────────────────────┤
│  4. 插件池（5层）                                        │
│     Schema → Guard → Execute → Healing → Reflect → Observe│
├─────────────────────────────────────────────────────────┤
│  5. 工具中心                                             │
│     工具注册表，支持工具级插件配置                        │
├─────────────────────────────────────────────────────────┤
│  6. 依赖注入层                                           │
│     LLM 实例、持久化、外部服务                           │
└─────────────────────────────────────────────────────────┘
```

### 🔌 5层插件系统

插件按固定顺序执行，确保可预测性和安全性：

| 层级 | 职责 | 内置插件 |
|-------|---------------|---------------------|
| **Schema** | 参数验证 | `SchemaDefault`、`SchemaStrict` |
| **Guard** | 访问控制与审批 | `GuardDefault`、`GuardHumanInLoop` |
| **Healing** | 失败自动恢复 | `HealingRetry`、`HealingLLM`（LLM驱动） |
| **Reflect** | 任务完成度验证 | `ReflectSimple`、`ReflectLLM`（LLM驱动） |
| **Observe** | 生命周期观测 | `LogPlugin` |

### ⚡ 执行流程

```
Schema → Guard → Execute → [Healing] → Reflect → Observe
                      ↑
                      └── 失败时触发 Healing（修复参数后重试）
```

**说明：**
- Execute 是核心工具执行层，每个工具都会执行
- Healing 是**可选的**，只在 Execute 失败时触发
- 成功流程：Schema → Guard → Execute → Reflect → Observe
- 失败重试：Schema → Guard → Execute (失败) → Healing → Execute (重试) → Reflect → Observe

### 🎯 工具级插件配置

不同工具可以使用不同的插件策略：

```python
from slotagent.core import CoreScheduler
from slotagent.plugins import SchemaDefault, GuardHumanInLoop
from slotagent.types import Tool

scheduler = CoreScheduler()

# 轻量级工具 - 最小化插件
weather_tool = Tool(
    tool_id='weather_query',
    name='天气查询',
    description='获取天气信息',
    input_schema={...},
    execute_func=get_weather
    # 无插件配置 - 使用全局插件（如果有）
)

# 高风险工具 - 完整插件链
payment_tool = Tool(
    tool_id='payment_refund',
    name='支付退款',
    description='处理支付退款',
    input_schema={...},
    execute_func=process_refund,
    plugins={
        'schema': 'schema_strict',           # 严格验证
        'guard': 'guard_human_in_loop'      # 需要人工审批
    }
)

scheduler.register_tool(weather_tool)
scheduler.register_tool(payment_tool)
```

### 🪝 Hook驱动可观测性

事件驱动系统，包含5个核心事件：

```python
from slotagent.core import HookManager

hook_manager = HookManager()

# 订阅事件
hook_manager.subscribe('before_exec', lambda e: log.info(f"开始执行: {e.tool_id}"))
hook_manager.subscribe('after_exec', lambda e: metrics.record(e.execution_time))
hook_manager.subscribe('fail', lambda e: alert.send(e.error))
hook_manager.subscribe('guard_block', lambda e: audit.log(e.reason))
hook_manager.subscribe('wait_approval', lambda e: notify_approver(e.approval_id))

scheduler = CoreScheduler(hook_manager=hook_manager)
```

### 👤 人工审批（HITL）

内置高风险操作审批工作流：

```python
from slotagent.core import ApprovalManager
from slotagent.plugins import GuardHumanInLoop

approval_manager = ApprovalManager(default_timeout=600.0)  # 10分钟

scheduler.plugin_pool.register_global_plugin(
    GuardHumanInLoop(approval_manager=approval_manager)
)

# 执行高风险操作
context = scheduler.execute('payment_refund', {'amount': 10000})

# 执行暂停，状态 = PENDING_APPROVAL
assert context.status == ExecutionStatus.PENDING_APPROVAL

# 审批者审核并批准
approval_manager.approve(context.approval_id, approver='finance@company.com')

# 或拒绝
approval_manager.reject(context.approval_id, approver='...', reason='...')
```

---

## 🚀 快速开始

### 安装

**方式一：从 GitHub Release 安装（推荐用户使用）**

```bash
# 直接从 GitHub 安装最新 release
pip install git+https://github.com/yimwu/slotagent.git@v0.3.0-alpha

# 或下载源码安装
wget https://github.com/yimwu/slotagent/archive/refs/tags/v0.3.0-alpha.tar.gz
tar -xzf v0.3.0-alpha.tar.gz
cd slotagent-0.3.0-alpha
pip install .
```

**方式二：从源码安装（开发者使用）**

```bash
# 克隆仓库
git clone https://github.com/yimwu/slotagent.git
cd slotagent

# 开发模式安装
pip install -e .

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

**系统要求：**
- Python 3.8 或更高版本
- 核心功能无第三方依赖

### Hello World 示例

```python
from slotagent.core import CoreScheduler
from slotagent.types import Tool

# 1. 创建调度器
scheduler = CoreScheduler()

# 2. 定义工具
def add_numbers(params):
    return {'result': params['a'] + params['b']}

calculator = Tool(
    tool_id='add',
    name='加法计算器',
    description='将两个数字相加',
    input_schema={
        'type': 'object',
        'properties': {
            'a': {'type': 'number'},
            'b': {'type': 'number'}
        },
        'required': ['a', 'b']
    },
    execute_func=add_numbers
)

# 3. 注册并执行
scheduler.register_tool(calculator)
context = scheduler.execute('add', {'a': 10, 'b': 32})

print(f"结果: {context.final_result}")  # {'result': 42}
```

### 使用插件链

```python
from slotagent.plugins import SchemaDefault, GuardDefault, LogPlugin

# 注册插件
scheduler.plugin_pool.register_global_plugin(
    SchemaDefault(schema=calculator.input_schema)
)
scheduler.plugin_pool.register_global_plugin(
    GuardDefault(blacklist=['dangerous_tool'])
)
scheduler.plugin_pool.register_global_plugin(LogPlugin())

# 执行完整插件链
context = scheduler.execute('add', {'a': 10, 'b': 32})
# 输出：插件链执行 → Schema验证 → Guard检查 → 工具运行 → 日志记录
```

---

## 📚 文档

### 核心文档

- **[API 参考](docs/api_reference.md)** - 完整 API 文档
- **[用户指南](docs/user_guide.md)** - 深入使用指南和教程
- **[FAQ](docs/faq.md)** - 常见问题解答
- **[架构说明（CLAUDE.md）](CLAUDE.md)** - 系统架构和设计原则
- **[开发规范](DEVELOPMENT_RULES.md)** - SDD/TDD 实践和代码标准

### 规格文档

- **[架构文档](docs/architecture/)** - 详细设计文档
  - 核心调度器、插件系统、工具系统、Hook系统、审批工作流
- **[接口规范](docs/interfaces/)** - 接口契约
- **[数据模型](docs/data_models/)** - 数据结构定义
- **[工作流程](docs/workflows/)** - 流程和状态机

### 示例

- **[独立模式](examples/standalone_mode_example.py)** - 基础使用示例
- **[自定义插件](examples/custom_plugin_example.py)** - 自定义插件开发
- **[审批工作流](examples/approval_workflow_example.py)** - 人工审批模式

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行覆盖率测试
pytest --cov=src/slotagent --cov-report=term-missing

# 运行指定测试文件
pytest tests/unit/test_core_scheduler.py

# 运行集成测试
pytest tests/integration/
```

**测试覆盖率：** 94.79%（243/243 个测试通过）

---

## 🛠️ 开发

### 设置

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行代码格式化
black src/slotagent tests/

# 运行代码检查
flake8 src/slotagent tests/

# 运行类型检查（可选）
mypy src/slotagent
```

### 项目结构

```
slotagent/
├── src/slotagent/          # 源代码
│   ├── core/               # 核心引擎
│   │   ├── core_scheduler.py
│   │   ├── plugin_pool.py
│   │   ├── tool_registry.py
│   │   ├── hook_manager.py
│   │   └── approval_manager.py
│   ├── plugins/            # 内置插件
│   │   ├── schema.py
│   │   ├── guard.py
│   │   ├── healing.py
│   │   ├── reflect.py
│   │   └── observe.py
│   ├── interfaces.py       # 插件接口
│   ├── types.py            # 数据类型
│   └── agent.py            # SlotAgent 门面（独立模式 + 嵌入模式）
├── tests/                  # 测试套件
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── docs/                   # 文档
├── examples/               # 示例脚本
└── scripts/                # 工具脚本
```

---

## 🤝 贡献

我们欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解：

- 开发工作流和分支策略
- 代码风格和提交信息规范
- 如何提交 Pull Request

### 开发工作流

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 按照我们的 [开发规范](DEVELOPMENT_RULES.md) 编写代码
4. 编写测试（TDD 方法）
5. 确保测试通过且覆盖率保持高水平
6. 使用 Angular 提交格式提交更改
7. 推送到您的 fork 并提交 Pull Request

---

## 📊 项目状态

| 阶段 | 状态 | 完成时间 |
|-------|--------|--------------|
| Phase 1: 基础设施 | ✅ | 2026-03-22 |
| Phase 2: 核心引擎 | ✅ | 2026-03-22 |
| Phase 3: 基础插件 | ✅ | 2026-03-22 |
| Phase 4: 工具系统 | ✅ | 2026-03-22 |
| Phase 5: Hook 系统 | ✅ | 2026-03-22 |
| Phase 6: 审批系统 | ✅ | 2026-03-22 |
| Phase 7: 测试与文档 | ✅ | 2026-03-22 |
| Phase 8: 示例 | 🚧 | 核心示例已完成 |

**当前指标：**
- 代码行数：~5,000+
- 测试覆盖率：95.38%
- 测试：243/243 通过
- 文档：完整文档和示例

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

感谢所有为 SlotAgent 做出贡献的开发者！

---

## 📞 支持与联系

- **Issues：** [GitHub Issues](https://github.com/yimwu/slotagent/issues)
- **讨论：** [GitHub Discussions](https://github.com/yimwu/slotagent/discussions)
- **维护者：** SlotAgent 核心团队

---

**Made with ❤️ by the SlotAgent Team**
