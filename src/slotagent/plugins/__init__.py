# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Built-in plugins package - Public API exports.

Contains official implementations of the 5 plugin layers:
- schema: Parameter validation
- guard: Permission control and approval
- healing: Auto-recovery on failure
- reflect: Task completion verification
- observe: Lifecycle observation
"""

from slotagent.plugins.guard import GuardDefault, GuardHumanInLoop
from slotagent.plugins.healing import HealingLLM, HealingRetry
from slotagent.plugins.observe import LogPlugin
from slotagent.plugins.reflect import ReflectLLM, ReflectSimple
from slotagent.plugins.schema import SchemaDefault, SchemaStrict

__all__ = [
    # Schema layer
    "SchemaDefault",
    "SchemaStrict",
    # Guard layer
    "GuardDefault",
    "GuardHumanInLoop",
    # Healing layer
    "HealingRetry",
    "HealingLLM",
    # Reflect layer
    "ReflectSimple",
    "ReflectLLM",
    # Observe layer
    "LogPlugin",
]
