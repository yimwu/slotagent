# SlotAgent

[English](README.md) | [中文](README.zh-CN.md)

[![Release](https://img.shields.io/github/v/release/yimwu/slotagent?include_prereleases)](https://github.com/yimwu/slotagent/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-95.38%25-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-243%20passed-brightgreen.svg)]()
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

**SlotAgent** is an industrial-grade, self-developed LLM Agent execution engine featuring a plugin-slot architecture that emphasizes loose coupling and flexible extension.

## 🎯 Project Vision

SlotAgent is a **production-ready tool execution engine** designed for reliable, secure, and observable LLM agent systems.

### Key Design Principles

- **🔧 Minimal Kernel** - Core scheduler handles only orchestration, zero business logic, no third-party dependencies
- **🧩 Plugin-Slot Architecture** - 5-layer plugin system (Schema/Guard/Healing/Reflect/Observe) with hot-swappable components
- **⚙️ Tool-Level Customization** - Each tool independently configures its plugin chain for optimal performance
- **🔒 Production-Ready** - Built-in support for human approval workflows, comprehensive observability, and audit logging
- **🔄 Dual-Mode Compatible** - Run standalone or embed into LangGraph/LangChain as the execution layer

---

## ✨ Core Features

### 🏗️ 6-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  1. Usage Modes                                          │
│     Independent Mode  │  Embedded Mode (LangGraph)       │
├─────────────────────────────────────────────────────────┤
│  2. Interface Layer                                      │
│     • run(query) - Natural language tool interaction     │
│     • execute(tool, params) - Direct tool execution      │
│     • Hook API (event subscription)                      │
│     • Plugin Management API                              │
├─────────────────────────────────────────────────────────┤
│  3. Core Scheduler (Minimal Kernel)                      │
│     Plugin chain execution → Event dispatch → State mgmt │
├─────────────────────────────────────────────────────────┤
│  4. Plugin Pool (5 Layers)                               │
│     Schema → Guard → Execute → Healing → Reflect → Observe│
├─────────────────────────────────────────────────────────┤
│  5. Tool Center                                          │
│     Tool registry with per-tool plugin configuration     │
├─────────────────────────────────────────────────────────┤
│  6. Dependency Injection Layer                           │
│     LLM instances, persistence, external services        │
└─────────────────────────────────────────────────────────┘
```

### 🔌 5-Layer Plugin System

Plugins execute in a fixed order to ensure predictability and security:

| Layer | Responsibility | Built-in Plugins |
|-------|---------------|------------------|
| **Schema** | Parameter validation | `SchemaDefault`, `SchemaStrict` |
| **Guard** | Access control & approval | `GuardDefault`, `GuardHumanInLoop` |
| **Healing** | Auto-recovery on failure | `HealingRetry`, `HealingLLM` (LLM-driven) |
| **Reflect** | Task completion verification | `ReflectSimple`, `ReflectLLM` (LLM-driven) |
| **Observe** | Lifecycle observation | `LogPlugin` |

### ⚡ Execution Flow

```
Schema → Guard → Execute → [Healing] → Reflect → Observe
                      ↑
                      └── Healing triggered on Execute failure (fixes params and retries)
```

**Notes:**
- Execute is the core tool execution layer, runs for every tool
- Healing is **optional**, only triggered when Execute fails
- Success path: Schema → Guard → Execute → Reflect → Observe
- Failure retry: Schema → Guard → Execute (fail) → Healing → Execute (retry) → Reflect → Observe

### 🎯 Tool-Level Plugin Configuration

Different tools can use different plugin strategies:

```python
from slotagent.core import CoreScheduler
from slotagent.plugins import SchemaDefault, GuardHumanInLoop
from slotagent.types import Tool

scheduler = CoreScheduler()

# Lightweight tool - minimal plugins
weather_tool = Tool(
    tool_id='weather_query',
    name='Weather Query',
    description='Get weather information',
    input_schema={...},
    execute_func=get_weather
    # No plugins config - uses global plugins (if any)
)

# High-risk tool - full plugin chain
payment_tool = Tool(
    tool_id='payment_refund',
    name='Payment Refund',
    description='Process payment refund',
    input_schema={...},
    execute_func=process_refund,
    plugins={
        'schema': 'schema_strict',           # Strict validation
        'guard': 'guard_human_in_loop'      # Human approval required
    }
)

scheduler.register_tool(weather_tool)
scheduler.register_tool(payment_tool)
```

### 🪝 Hook-Driven Observability

Event-driven system with 5 core events:

```python
from slotagent.core import HookManager

hook_manager = HookManager()

# Subscribe to events
hook_manager.subscribe('before_exec', lambda e: log.info(f"Starting: {e.tool_id}"))
hook_manager.subscribe('after_exec', lambda e: metrics.record(e.execution_time))
hook_manager.subscribe('fail', lambda e: alert.send(e.error))
hook_manager.subscribe('guard_block', lambda e: audit.log(e.reason))
hook_manager.subscribe('wait_approval', lambda e: notify_approver(e.approval_id))

scheduler = CoreScheduler(hook_manager=hook_manager)
```

### 👤 Human-in-the-Loop (HITL)

Built-in approval workflow for high-risk operations:

```python
from slotagent.core import ApprovalManager
from slotagent.plugins import GuardHumanInLoop

approval_manager = ApprovalManager(default_timeout=600.0)  # 10 minutes

scheduler.plugin_pool.register_global_plugin(
    GuardHumanInLoop(approval_manager=approval_manager)
)

# Execute high-risk operation
context = scheduler.execute('payment_refund', {'amount': 10000})

# Execution pauses, status = PENDING_APPROVAL
assert context.status == ExecutionStatus.PENDING_APPROVAL

# Approver reviews and approves
approval_manager.approve(context.approval_id, approver='finance@company.com')

# Or rejects
approval_manager.reject(context.approval_id, approver='..', reason='...')
```

---

## 🚀 Quick Start

### Installation

**Option 1: Install from GitHub Release (Recommended for users)**

```bash
# Install latest release directly from GitHub
pip install git+https://github.com/yimwu/slotagent.git@v0.3.0-alpha

# Or download and install from source
wget https://github.com/yimwu/slotagent/archive/refs/tags/v0.3.0-alpha.tar.gz
tar -xzf v0.3.0-alpha.tar.gz
cd slotagent-0.3.0-alpha
pip install .
```

**Option 2: Install from source (For developers)**

```bash
# Clone repository
git clone https://github.com/yimwu/slotagent.git
cd slotagent

# Install in development mode
pip install -e .

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

**Requirements:**
- Python 3.8 or higher
- No third-party dependencies for core functionality

### Hello World Example

```python
from slotagent import SlotAgent
from slotagent.types import Tool

# 1. Create agent
agent = SlotAgent()

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
agent.register_tool(calculator)
context = agent.execute('add', {'a': 10, 'b': 32})

print(f"Result: {context.final_result}")  # {'result': 42}
```

### With Plugin Chain

```python
from slotagent import SlotAgent
from slotagent.plugins import SchemaDefault, GuardDefault, LogPlugin

agent = SlotAgent()

# Register plugins
agent.register_plugin(SchemaDefault())
agent.register_plugin(GuardDefault(blacklist=['dangerous_tool']))
agent.register_plugin(LogPlugin())

# Execute with full plugin chain
context = agent.execute('add', {'a': 10, 'b': 32})
# Output: Plugin chain executes → Schema validates → Guard checks → Tool runs → Observe logs
```

### Independent Mode (Natural Language)

```python
from slotagent import SlotAgent
from slotagent.llm import QwenLLM  # or any LLM implementing LLMInterface
from slotagent.plugins import HealingLLM, ReflectLLM

# Use a real LLM for tool selection and LLM-driven plugins
llm = QwenLLM(api_key="your-api-key", model="qwen3-coder-next")

agent = SlotAgent(llm=llm)

# Register LLM-powered plugins
agent.register_plugin(HealingLLM(llm=llm))  # Auto-recovery on failure
agent.register_plugin(ReflectLLM(llm=llm))   # Task completion verification

# Register tools...
agent.register_tool(weather_tool)

# Natural language query - LLM picks tool and extracts params
context = agent.run("What's the weather in Beijing?")
print(f"Result: {context.final_result}")
```

---

## 📚 Documentation

### Core Documentation

- **[API Reference](docs/api_reference.md)** - Complete API documentation
- **[User Guide](docs/user_guide.md)** - In-depth usage guide and tutorials
- **[FAQ](docs/faq.md)** - Frequently asked questions
- **[Architecture (CLAUDE.md)](CLAUDE.md)** - System architecture and design principles
- **[Development Rules](DEVELOPMENT_RULES.md)** - SDD/TDD practices and code standards

### Specifications

- **[Architecture Docs](docs/architecture/)** - Detailed design documents
  - Core Scheduler, Plugin System, Tool System, Hook System, Approval Workflow
- **[Interface Specs](docs/interfaces/)** - Interface contracts
- **[Data Models](docs/data_models/)** - Data structure definitions
- **[Workflows](docs/workflows/)** - Process flows and state machines

### Examples

- **[Independent Mode](examples/independent_mode_example.py)** - Natural language tool interaction with real LLM (full 6-layer plugin chain demo)
- **[LLM Plugins](examples/llm_plugins_example.py)** - HealingLLM and ReflectLLM with real Qwen LLM
- **[Standalone Mode](examples/standalone_mode_example.py)** - Basic usage with CoreScheduler
- **[Custom Plugins](examples/custom_plugin_example.py)** - Custom plugin development
- **[Approval Workflow](examples/approval_workflow_example.py)** - Human-in-the-loop patterns

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

**Test Coverage:** 95.38% (243/243 tests passing)

---

## 🛠️ Development

### Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run code formatter
black src/slotagent tests/

# Run linter
flake8 src/slotagent tests/

# Run type checker (optional)
mypy src/slotagent
```

### Project Structure

```
slotagent/
├── src/slotagent/          # Source code
│   ├── core/               # Core engine
│   │   ├── core_scheduler.py
│   │   ├── plugin_pool.py
│   │   ├── tool_registry.py
│   │   ├── hook_manager.py
│   │   └── approval_manager.py
│   ├── plugins/            # Built-in plugins
│   │   ├── schema.py
│   │   ├── guard.py
│   │   ├── healing.py
│   │   ├── reflect.py
│   │   └── observe.py
│   ├── llm/                # LLM abstraction layer
│   │   ├── interface.py
│   │   ├── qwen_llm.py
│   │   └── mock_llm.py
│   ├── interfaces.py       # Plugin interfaces
│   ├── types.py            # Data types
│   └── agent.py            # SlotAgent facade (independent + embedded mode)
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
├── examples/               # Example scripts
└── scripts/                # Utility scripts
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development workflow and branching strategy
- Code style and commit message conventions
- How to submit a Pull Request

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write code following our [Development Rules](DEVELOPMENT_RULES.md)
4. Write tests (TDD approach)
5. Ensure tests pass and coverage remains high
6. Commit changes using Angular commit format
7. Push to your fork and submit a Pull Request

---

## 📋 Roadmap

### v0.1.0-alpha (Previous) ✅

- [x] Core scheduler with plugin chain execution
- [x] 5-layer plugin system (Schema, Guard, Healing, Reflect, Observe)
- [x] Tool registry with per-tool plugin configuration
- [x] Hook-based event system
- [x] Human-in-the-loop approval workflow
- [x] Comprehensive test suite
- [x] Complete documentation and examples

### v0.2.0-alpha (Previous) ✅

- [x] SlotAgent facade (independent + embedded mode)
- [x] LLM abstraction layer with QwenLLM and MockLLM
- [x] LLM-driven plugins (HealingLLM, ReflectLLM)
- [x] Natural language tool interaction (SlotAgent.run)
- [x] Comprehensive examples with real LLM

### v0.3.0-alpha (Current) ✅

- [x] LLM self-healing with enumerated error keys
- [x] Improved examples demonstrating HealingLLM self-repair

### v0.4.0 (Planned)

- [ ] Async execution support (`async/await`)
- [ ] Performance benchmarking and optimization
- [ ] LangGraph integration example
- [ ] Distributed approval manager (Redis-based)
- [ ] Additional built-in plugins
- [ ] Database persistence layer
- [ ] Advanced healing strategies
- [ ] Monitoring and alerting integrations

### Future Plans

- **JavaScript/TypeScript Version**: We plan to create a JavaScript/TypeScript version of SlotAgent to bring the same plugin-slot architecture and reliability guarantees to Node.js and browser environments. This will maintain API compatibility with the Python version while enabling integration with the broader JavaScript ecosystem.

---

## 📊 Project Status

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Infrastructure | ✅ | 2026-03-22 |
| Phase 2: Core Engine | ✅ | 2026-03-22 |
| Phase 3: Basic Plugins | ✅ | 2026-03-22 |
| Phase 4: Tool System | ✅ | 2026-03-22 |
| Phase 5: Hook System | ✅ | 2026-03-22 |
| Phase 6: Approval System | ✅ | 2026-03-22 |
| Phase 7: Testing & Docs | ✅ | 2026-03-22 |
| Phase 8: Examples | 🚧 | Core examples done |

**Current Metrics:**
- Lines of Code: ~5,000+
- Test Coverage: 95.38%
- Tests: 243/243 passing
- Documentation: Complete docs + examples

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

Thanks to all contributors who have helped make SlotAgent better!

---

## 📞 Support & Contact

- **Issues:** [GitHub Issues](https://github.com/yimwu/slotagent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yimwu/slotagent/discussions)
- **Maintainers:** SlotAgent Core Team

---

**Made with ❤️ by the SlotAgent Team**
