# SlotAgent v0.1.0-alpha

🎉 **Initial Alpha Release** - Industrial-grade LLM Agent Execution Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-96.66%25-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-179%20passed-brightgreen.svg)]()

---

## 🎯 What is SlotAgent?

SlotAgent is a **production-ready tool execution engine** designed for reliable, secure, and observable LLM agent systems.

### Key Highlights

- **🔧 Minimal Kernel** - Core scheduler handles only orchestration, zero business logic, no third-party dependencies
- **🧩 Plugin-Slot Architecture** - 5-layer plugin system (Schema/Guard/Healing/Reflect/Observe) with hot-swappable components
- **⚙️ Tool-Level Customization** - Each tool independently configures its plugin chain for optimal performance
- **🔒 Production-Ready** - Built-in support for human approval workflows, comprehensive observability, and audit logging
- **🔄 Dual-Mode Compatible** - Run standalone or embed into LangGraph/LangChain as the execution layer

---

## ✨ Features in v0.1.0-alpha

### 🏗️ Core Engine
- [x] **Minimal Kernel Scheduler** - Pure Python, zero third-party dependencies
- [x] **Plugin Pool** - Centralized plugin management with priority rules
- [x] **Tool Registry** - Tool registration and validation
- [x] **Event System** - Hook-driven observability with 5 event types
- [x] **State Management** - Execution context and status tracking

### 🔌 Plugin System (5 Layers)

| Layer | Built-in Plugins | Status |
|-------|------------------|--------|
| **Schema** | SchemaDefault, SchemaStrict | ✅ Production |
| **Guard** | GuardDefault, GuardHumanInLoop | ✅ Production |
| **Healing** | HealingRetry | ⚠️ Placeholder |
| **Reflect** | ReflectSimple | ⚠️ Placeholder |
| **Observe** | LogPlugin | ✅ Production |

### 👤 Human-in-the-Loop (HITL)
- [x] **ApprovalManager** - Production-ready approval workflow
- [x] **Timeout Handling** - Automatic timeout detection
- [x] **State Transitions** - PENDING → APPROVED/REJECTED/TIMEOUT
- [x] **Hook Integration** - `wait_approval` event for notifications

### 🪝 Hook Event System
- [x] `before_exec` - Before tool execution
- [x] `after_exec` - After successful execution
- [x] `fail` - On execution failure
- [x] `guard_block` - When guard blocks execution
- [x] `wait_approval` - When approval is required

---

## 📊 Quality Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Test Coverage** | 96.66% | ≥85% | ✅ Exceeded |
| **Tests Passing** | 179/179 | 100% | ✅ Perfect |
| **Code Files** | ~5,000+ LOC | - | ✅ Complete |
| **Documentation** | 18 docs | - | ✅ Complete |
| **Examples** | 3 scripts | - | ✅ Ready |

### Test Breakdown
- **Unit Tests**: 156 tests
- **Integration Tests**: 23 tests
- **Coverage by Module**:
  - `core/`: 97.4% average
  - `plugins/`: 92.7% average
  - `types.py`: 97.22%
  - `interfaces.py`: 90.32%

---

## 📚 Documentation

### Core Documentation
- 📖 [README](https://github.com/yimwu/slotagent/blob/main/README.md) - Project overview (English)
- 📖 [README.zh-CN](https://github.com/yimwu/slotagent/blob/main/README.zh-CN.md) - 项目概览（中文）
- 📘 [API Reference](https://github.com/yimwu/slotagent/blob/main/docs/api_reference.md) - Complete API documentation
- 📗 [User Guide](https://github.com/yimwu/slotagent/blob/main/docs/user_guide.md) - In-depth usage guide
- 📕 [FAQ](https://github.com/yimwu/slotagent/blob/main/docs/faq.md) - Frequently asked questions

### Architecture Documents
- [Core Scheduler Design](https://github.com/yimwu/slotagent/blob/main/docs/architecture/core_scheduler.md)
- [Plugin System Design](https://github.com/yimwu/slotagent/blob/main/docs/architecture/plugin_system.md)
- [Tool System Design](https://github.com/yimwu/slotagent/blob/main/docs/architecture/tool_system.md)
- [Hook System Design](https://github.com/yimwu/slotagent/blob/main/docs/architecture/hook_system.md)
- [Approval Workflow Design](https://github.com/yimwu/slotagent/blob/main/docs/architecture/approval_workflow.md)

### Examples
- 🎯 [Standalone Mode](https://github.com/yimwu/slotagent/blob/main/examples/standalone_mode_example.py) - Basic usage (5 scenarios)
- 🎨 [Custom Plugins](https://github.com/yimwu/slotagent/blob/main/examples/custom_plugin_example.py) - Plugin development (5 examples)
- 🔐 [Approval Workflow](https://github.com/yimwu/slotagent/blob/main/examples/approval_workflow_example.py) - HITL patterns (5 flows)

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yimwu/slotagent.git
cd slotagent

# Install in development mode
pip install -e .

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Hello World

```python
from slotagent.core import CoreScheduler
from slotagent.types import Tool

# 1. Create scheduler
scheduler = CoreScheduler()

# 2. Define a tool
def add_numbers(params):
    return {'result': params['a'] + params['b']}

calculator = Tool(
    tool_id='add',
    name='Add Numbers',
    description='Add two numbers together',
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

# 3. Register and execute
scheduler.register_tool(calculator)
context = scheduler.execute('add', {'a': 10, 'b': 32})

print(f"Result: {context.final_result}")  # {'result': 42}
```

### Running Examples

```bash
# Basic standalone mode
python examples/standalone_mode_example.py

# Custom plugin development
python examples/custom_plugin_example.py

# Human-in-the-loop approval
python examples/approval_workflow_example.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/slotagent --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_core_scheduler.py

# Run integration tests
pytest tests/integration/
```

**Current Results:**
- ✅ 179/179 tests passing
- ✅ 96.66% coverage

---

## 🗺️ Roadmap

### v0.2.0 (Planned)
- [ ] Async execution support (`async/await`)
- [ ] Performance benchmarking and optimization
- [ ] LangGraph integration example
- [ ] Distributed approval manager (Redis-based)
- [ ] Additional built-in plugins

### v0.3.0 (Future)
- [ ] Database persistence layer
- [ ] Advanced healing strategies
- [ ] Monitoring and alerting integrations
- [ ] Web UI for approval management
- [ ] Multi-tenancy support

---

## ⚠️ Alpha Release Notes

This is an **alpha release** intended for:
- ✅ Early adopters and testing
- ✅ Feedback collection
- ✅ API validation
- ⚠️ Not recommended for production use yet

**Known Limitations:**
- Healing and Reflect plugins are placeholders (will be fully implemented in v0.2.0)
- No async support yet (planned for v0.2.0)
- In-memory approval manager only (Redis version in v0.2.0)
- MyPy type checking has some warnings (non-blocking)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/yimwu/slotagent/blob/main/CONTRIBUTING.md) for:
- Development workflow
- Code style guidelines
- How to submit Pull Requests

---

## 📄 License

This project is licensed under the [MIT License](https://github.com/yimwu/slotagent/blob/main/LICENSE).

---

## 🙏 Acknowledgments

Thanks to all contributors who helped make SlotAgent v0.1.0-alpha possible!

---

## 📞 Support & Contact

- **Issues:** [GitHub Issues](https://github.com/yimwu/slotagent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yimwu/slotagent/discussions)
- **Repository:** https://github.com/yimwu/slotagent

---

**Made with ❤️ by the SlotAgent Team**
