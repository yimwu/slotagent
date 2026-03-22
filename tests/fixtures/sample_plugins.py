# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Test fixtures for SlotAgent tests.

Provides sample plugins, tools, and mock objects for testing.
"""

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

# =============================================================================
# Sample Plugins for Testing
# =============================================================================


class MockSchemaPlugin(PluginInterface):
    """Mock Schema plugin for testing"""

    layer = "schema"
    plugin_id = "schema_mock"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"validated": True, "plugin": "schema_mock"})


class MockGuardPlugin(PluginInterface):
    """Mock Guard plugin for testing"""

    layer = "guard"
    plugin_id = "guard_mock"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"approved": True, "plugin": "guard_mock"})


class MockHealingPlugin(PluginInterface):
    """Mock Healing plugin for testing"""

    layer = "healing"
    plugin_id = "healing_mock"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"recovered": False, "plugin": "healing_mock"})


class MockReflectPlugin(PluginInterface):
    """Mock Reflect plugin for testing"""

    layer = "reflect"
    plugin_id = "reflect_mock"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"task_completed": True, "plugin": "reflect_mock"})


class MockObservePlugin(PluginInterface):
    """Mock Observe plugin for testing"""

    layer = "observe"
    plugin_id = "observe_mock"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"logged": True, "plugin": "observe_mock"})


class AlternativeSchemaPlugin(PluginInterface):
    """Alternative Schema plugin for testing priority"""

    layer = "schema"
    plugin_id = "schema_alternative"

    def validate(self) -> bool:
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True, data={"validated": True, "plugin": "schema_alternative"})


class FailingValidationPlugin(PluginInterface):
    """Plugin that fails validation"""

    layer = "schema"
    plugin_id = "schema_failing"

    def validate(self) -> bool:
        return False

    def execute(self, context: PluginContext) -> PluginResult:
        return PluginResult(success=True)
