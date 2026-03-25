# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0-alpha] - 2026-03-25

### Added
- HealingLLM self-repair demo using enumerated error keys in `llm_plugins_example.py`
- When a tool raises an error with available key enumeration, HealingLLM can autonomously select the correct key and retry

### Changed
- Updated `llm_plugins_example.py` Test 2 to use strict key validation with enumerated error messages instead of unreliable retry logic
- Recommended model updated to `qwen3-coder-next` (replaces `qwen3.5-plus` which has timeout issues on the coding endpoint)

### Fixed
- README.md: translated Chinese execution flow notes to English
- README.md / README.zh-CN.md: fixed duplicate `v0.3.0` roadmap entries
- README.zh-CN.md: updated stale test badge (179→243 tests, 96.66%→94.79% coverage)
- README.zh-CN.md: added missing `agent.py` to project structure

## [0.2.0-alpha] - 2026-03-24

### Added
- `SlotAgent` facade class (`src/slotagent/agent.py`) supporting independent and embedded modes
- `SlotAgent.run(user_query)` for natural language tool interaction (LLM selects tool and extracts params)
- LLM abstraction layer: `QwenLLM` and `MockLLM` implementations
- LLM-driven plugins: `HealingLLM` (auto-recovery) and `ReflectLLM` (task verification)
- `SlotAgent` exported from `slotagent.__init__`
- 30 unit tests for `agent.py` (100% coverage)

### Changed
- Total test suite: 243 tests, 94.79% coverage

## [0.1.0-alpha] - 2026-03-22

### Added
- Core scheduler (`CoreScheduler`) with 5-layer plugin chain execution
- Plugin pool (`PluginPool`) with global and per-tool plugin configuration
- Built-in plugins: `SchemaDefault`, `SchemaStrict`, `GuardDefault`, `GuardHumanInLoop`, `HealingRetry`, `HealingLLM`, `ReflectSimple`, `ReflectLLM`, `LogPlugin`
- Tool registry with per-tool plugin override support
- Hook system (`HookManager`) with 5 core events: `before_exec`, `after_exec`, `fail`, `guard_block`, `wait_approval`
- Approval workflow (`ApprovalManager`) for human-in-the-loop operations
- Complete documentation and examples
