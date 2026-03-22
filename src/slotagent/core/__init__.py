# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Core package - Public API exports.

This module exports the core components of SlotAgent for external use.
"""

from slotagent.core.approval_manager import ApprovalManager
from slotagent.core.core_scheduler import CoreScheduler
from slotagent.core.hook_manager import HookManager
from slotagent.core.plugin_pool import PluginPool
from slotagent.core.tool_registry import ToolRegistry

__all__ = [
    "CoreScheduler",
    "PluginPool",
    "ToolRegistry",
    "HookManager",
    "ApprovalManager",
]
