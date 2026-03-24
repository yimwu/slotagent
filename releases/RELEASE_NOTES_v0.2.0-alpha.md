# SlotAgent v0.2.0-alpha

🎉 **LLM Integration Release** - Natural Language Tool Interaction

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-95.38%25-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-243%20passed-brightgreen.svg)]()

---

## 🎯 What's New in v0.2.0-alpha

SlotAgent now features a **unified facade class** (`SlotAgent`) supporting both independent and embedded modes, plus a **real LLM integration layer** for intelligent plugins.

### Key Highlights

- **🚀 SlotAgent Facade** - Simple unified API for all modes: `SlotAgent.run()`, `.execute()`, `.batch_run()`
- **🧠 LLM Abstraction Layer** - Unified `LLMInterface` supporting Qwen, OpenAI, and custom providers
- **🔧 LLM-Driven Plugins** - `HealingLLM` auto-fixes failures, `ReflectLLM` verifies completion quality
- **💬 Natural Language** - Independent mode processes natural language queries via LLM tool selection
- **📚 Rich Examples** - Working examples with real Qwen LLM demonstrating full 6-layer plugin chain

---

## ✨ New Features

### 🏗️ SlotAgent Facade (Interface Layer)
- [x] **SlotAgent Class** - Unified facade for independent and embedded modes
- [x] **Independent Mode** - `run(query)` for natural language interaction
- [x] **Embedded Mode** - `execute(tool, params)` for direct tool control
- [x] **Batch Execution** - `batch_run(tasks)` for multiple tool calls
- [x] **Hook Convenience Methods** - `on_before_exec`, `on_after_exec`, `on_fail`, `on_guard_block`, `on_wait_approval`
- [x] **Approval Management** - Built-in `approve()`, `reject()` methods

### 🧠 LLM Abstraction Layer
- [x] **LLMInterface** - Abstract base for all LLM providers
- [x] **QwenLLM** - Alibaba Cloud Bailian (通义千问) integration
- [x] **MockLLM** - Testing and development without real API calls
- [x] **Message Types** - `LLMMessage` and `LLMResponse` standard interfaces

### 🔌 LLM-Driven Plugins

| Plugin | Function | Trigger |
|--------|----------|---------|
| **HealingLLM** | Analyzes failures, fixes params via LLM, retries | Tool execution fails |
| **ReflectLLM** | Verifies task completion quality via LLM | After successful execution |

### ⚡ Execution Flow Visualization

```
Normal Flow:
Schema → Guard → Execute → Reflect → Observe

Failure + Healing Flow:
Schema → Guard → Execute (fail) → Healing (LLM fix) → Execute (retry) → Reflect → Observe
```

### 📚 New Examples
- `independent_mode_example.py` - Complete 6-layer plugin chain demo with real LLM
- `llm_plugins_example.py` - HealingLLM and ReflectLLM usage with Qwen

---

## 📊 Quality Metrics

| Metric | Value |
|--------|-------|
| Test Coverage | **95.38%** |
| Tests Passing | **243/243** |
| Lines of Code | ~5,000+ |
| Documentation | Complete |

---

## 🔄 Migration from v0.1.0-alpha

### Before (v0.1.0)
```python
from slotagent.core import CoreScheduler, HookManager
from slotagent.plugins import SchemaDefault

hook_mgr = HookManager()
scheduler = CoreScheduler(hook_manager=hook_mgr)
scheduler.plugin_pool.register_global_plugin(SchemaDefault())

context = scheduler.execute('weather_query', {'location': 'Beijing'})
```

### After (v0.2.0) - Recommended
```python
from slotagent import SlotAgent
from slotagent.plugins import SchemaDefault

agent = SlotAgent()
agent.register_plugin(SchemaDefault())

# Embedded mode
context = agent.execute('weather_query', {'location': 'Beijing'})

# Independent mode (NEW)
context = agent.run('What is the weather in Beijing?')
```

### CoreScheduler Still Available
The `CoreScheduler` class remains available for advanced use cases requiring direct access to the core engine.

---

## 🚀 Quick Start with Real LLM

```python
from slotagent import SlotAgent
from slotagent.llm import QwenLLM

# Create LLM
llm = QwenLLM(api_key="your-key", model="qwen3.5-plus")

# Create agent with LLM
agent = SlotAgent(llm=llm)

# Natural language query - LLM selects tool
result = agent.run("What's the weather in Shanghai?")
print(result.final_result)
```

---

## 🐛 Bug Fixes

- **Windows Console Encoding** - UTF-8 handling for non-ASCII output
- **SchemaDefault Fallback** - Uses tool schema when no explicit schema provided
- **QwenLLM Timeout** - Increased default timeout to 60s for LLM calls

---

## 📚 Documentation

- Updated [README.md](README.md) with execution flow diagrams
- Updated [README.zh-CN.md](README.zh-CN.md) Chinese documentation
- New examples demonstrating real LLM usage

---

## 🤝 Contributors

Thanks to all contributors who helped make SlotAgent v0.2.0-alpha possible!

---

**Full Changelog**: Compare with v0.1.0-alpha on GitHub
