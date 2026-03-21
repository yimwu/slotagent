# SlotAgent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

**SlotAgent** 是一款工业级、自研的 LLM Agent 执行引擎,采用插件插槽架构,强调松耦合和灵活扩展。

## 📖 项目定位

- **极小内核** - 核心调度引擎只负责调度,不含业务逻辑,无第三方依赖
- **插槽化插件** - 5层插件系统(Schema/Guard/Healing/Reflect/Observe),可插拔替换
- **工具级定制** - 每个工具独立配置插件链,按需优化(轻量工具跳过插件,高危工具全链路)
- **可靠与可观测** - Hook驱动的事件系统,支持人工审批(Human-in-the-Loop),生产就绪
- **双模式兼容** - 既可独立运行,也可嵌入 LangGraph/LangChain 作为底层执行引擎

## ✨ 核心特性

### 🧩 6层架构设计

1. **Usage Modes** - 独立模式 & 嵌入模式
2. **Interface Layer** - 执行接口、Hook接口、插件管理接口
3. **Core Scheduler** - 极小内核调度引擎(插件链执行、事件分发、状态管理)
4. **Plugin Pool** - 5层插件池(Schema/Guard/Healing/Reflect/Observe)
5. **Tool Center** - 工具中心,每个工具独立配置插件
6. **Dependency Injection** - LLM实例注入、可选持久化层

### 🔌 5层插件系统

| 插件层 | 职责 | 典型插件 |
|--------|------|--------|
| **Schema** | 参数验证 | SchemaDefault, SchemaStrict |
| **Guard** | 权限控制 & 审批 | GuardDefault, GuardHumanInLoop |
| **Healing** | 失败自愈 | HealingSimple, HealingRetry |
| **Reflect** | 任务反思 | ReflectSimple, ReflectStrict |
| **Observe** | 生命周期观测 | LogPlugin, MetricsPlugin, TracePlugin |

### 🎯 工具级插件配置

```python
# 轻量工具 - 跳过大部分插件
weather_tool = ToolDefinition(
    tool_id="weather_query",
    plugins={
        'schema': 'schema_default',  # 仅轻量验证
    }
)

# 高危工具 - 启用完整插件链
payment_tool = ToolDefinition(
    tool_id="payment_refund",
    plugins={
        'schema': 'schema_strict',
        'guard': 'guard_human_in_loop',  # 人工审批
        'healing': 'healing_retry',
        'reflect': 'reflect_strict',
        'observe': 'observe_full',
    }
)
```

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yimwu/slotagent.git
cd slotagent

# 安装依赖(开发模式)
pip install -e .
pip install -r requirements-dev.txt
```

### 快速示例

```python
from slotagent import SlotAgent
from slotagent.plugins import SchemaDefault, GuardDefault

# 初始化
agent = SlotAgent()

# 注册全局插件
agent.register_plugin(SchemaDefault(), layer='schema')
agent.register_plugin(GuardDefault(), layer='guard')

# 注册工具
agent.register_tool(weather_tool)

# 执行工具
result = agent.execute('weather_query', {'location': 'Beijing'})
print(result)
```

更多示例见 [examples/](examples/) 目录。

## 📚 文档

- [项目架构](CLAUDE.md) - 整体架构和设计原则
- [开发规范](DEVELOPMENT_RULES.md) - SDD/TDD规范、代码规范
- [项目计划](PROJECT_PLAN.md) - 开发计划和里程碑
- [详细文档](docs/) - 架构设计、接口规范、流程说明

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 生成覆盖率报告
pytest --cov=src/slotagent --cov-report=html tests/

# 查看覆盖率报告
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## 🛠️ 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 代码格式化
black src/slotagent tests/

# Lint检查
flake8 src/slotagent tests/

# 类型检查
mypy src/slotagent

# 运行完整质量检查
./scripts/quality_check.sh  # (Phase 1后添加)
```

## 🤝 贡献

欢迎贡献! 请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解:

- 开发流程和分支策略
- 代码规范和提交规范
- 如何提交 PR

## 📋 开发状态

当前版本: **v0.1.0-alpha**

- [x] Phase 1: 项目基础设施搭建
- [ ] Phase 2: 核心调度引擎与插件池
- [ ] Phase 3: 基础插件实现
- [ ] Phase 4: 工具中心与配置系统
- [ ] Phase 5: Hook系统与可观测性
- [ ] Phase 6: Human-in-the-Loop审批系统
- [ ] Phase 7: 测试与文档完善
- [ ] Phase 8: 示例与集成验证

详见 [PROJECT_PLAN.md](PROJECT_PLAN.md)

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。

## 🙏 致谢

感谢所有贡献者对 SlotAgent 项目的支持!

---

**项目维护:** SlotAgent 核心团队
**问题反馈:** [GitHub Issues](https://github.com/yimwu/slotagent/issues)
**设计讨论:** [GitHub Discussions](https://github.com/yimwu/slotagent/discussions)
