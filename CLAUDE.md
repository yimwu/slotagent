# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands and Development Notes

- Build and test commands are not yet established; refer to project setup documentation.
- The project is structured as follows (per the development plan):
  - `src/slotagent/` - core engine source code
  - `docs/` - detailed architecture and usage documentation
  - `examples/` - example plugins and demo usages
  - `tests/` - unit and integration tests
  - `requirements.txt` and `requirements-dev.txt` for dependency management
- Dependencies managed via Python pip with version constraints.
- CI/CD pipeline configured via GitHub Actions for automated testing and releases.
- Code follows PEP8 standards and Angular-style commit messages (for contributions).

## High-Level Architecture Overview

**Project positioning:** Industrial-grade, self-developed LLM agent execution engine emphasizing:
- Minimal core kernel (exclusively handles scheduling, no business logic)
- Plugin slot architecture enabling loose coupling and flexible extension
- Fine-grained tool-level customization (each tool independently selects plugins)
- Reliable, secure, and observable LLM tool execution

**Core 6-layer architecture (execution order):**

1. **Usage modes:**
   - Independent mode: standalone agent processing user queries end-to-end
   - Embedded mode: bottom-layer execution engine for LangGraph/LangChain

2. **Interface layer (3 types):**
   - Execution: `run(user_query)`, `execute(tool_name, params)`, `batch_run(tasks)`
   - Hooks: `on_wait_approval`, `on_before_exec`, `on_after_exec`, `on_fail`, `on_guard_block` (for external subscriptions)
   - Plugin management & callbacks: `register_plugin()`, `approve()`, `reject()`

3. **Core scheduling engine:**
   - Minimal kernel: only scheduling and event dispatch, no business logic
   - Plugin chain execution: Schema validation → Guard → Tool execution → Healing → Reflect
   - Plugin priority: tool plugins override global plugins
   - Event forwarding to Hook subscribers
   - State management with approval callback support

4. **Plugin pool (PluginPool - "the core soul"):**
   - **5 layers of plugins** (each layer can have multiple interchangeable plugins):
     - **Schema:** parameter validation (SchemaDefault, SchemaStrict, SchemaCustom)
     - **Guard:** permission control & approval (GuardDefault, GuardPayment, GuardHumanInLoop)
     - **Healing:** auto-recovery on failure (HealingSimple, HealingRetry, HealingFallback)
     - **Reflect:** task completion verification (ReflectSimple, ReflectStrict)
     - **Observe:** lifecycle data collection (LogPlugin, MetricsPlugin, TracePlugin)

5. **Tool center (first-class citizens):**
   - Each tool independently selects one plugin per layer from the pool
   - Per-tool optimization: lightweight tools skip plugins, high-risk tools enable full chain
   - Independent state management per tool
   - Example configs: simple query tool vs. high-risk payment refund tool

6. **Dependency injection layer:**
   - LLM instance injected globally (for Healing/Reflect plugins)
   - Optional persistence layer for approval state, execution records, plugin configs
   - Support for any LLM provider (GPT-4o, Claude, 通义千问, etc.)

**Key design principles:**
- Hook-driven observability: framework only emits events via Hooks; external systems (monitoring, IM, frontend) subscribe and handle
- Human-in-the-Loop as plugin: approval flows via Hook + callback, non-blocking, production-ready
- Dual compatibility: works standalone or embeds in LangGraph/LangChain
- Zero third-party dependencies: pure self-developed for full enterprise control

**Core execution flows:**
- Independent mode: user query → LLM reasoning → tool selection → plugin chain execution → result return
- Embedded mode: LangGraph schedules flow → calls SlotAgent.execute() → SlotAgent handles tool reliability → returns to LangGraph
- Approval flow: GuardHumanInLoop triggered → on_wait_approval Hook emitted → external approver notified → approve/reject callback → execution resumed/terminated

