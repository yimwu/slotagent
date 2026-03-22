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

from slotagent.plugins.schema import SchemaDefault, SchemaStrict
from slotagent.plugins.guard import GuardDefault, GuardHumanInLoop
from slotagent.plugins.healing import HealingRetry
from slotagent.plugins.reflect import ReflectSimple
from slotagent.plugins.observe import LogPlugin

__all__ = [
    # Schema layer
    'SchemaDefault',
    'SchemaStrict',

    # Guard layer
    'GuardDefault',
    'GuardHumanInLoop',

    # Healing layer
    'HealingRetry',

    # Reflect layer
    'ReflectSimple',

    # Observe layer
    'LogPlugin',
]
