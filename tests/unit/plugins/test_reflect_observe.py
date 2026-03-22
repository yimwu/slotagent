# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for Reflect and Observe plugins.
"""

import time
import uuid


from slotagent.types import PluginContext


class TestReflectSimple:
    """Test ReflectSimple plugin"""

    def test_reflect_simple_attributes(self):
        """Test ReflectSimple has correct attributes"""
        from slotagent.plugins.reflect import ReflectSimple

        assert ReflectSimple.layer == "reflect"
        assert ReflectSimple.plugin_id == "reflect_simple"

    def test_reflect_simple_reports_completed(self):
        """Test ReflectSimple reports task completed"""
        from slotagent.plugins.reflect import ReflectSimple

        plugin = ReflectSimple()

        context = PluginContext(
            tool_id="test",
            tool_name="Test",
            params={},
            layer="reflect",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.data["task_completed"] is True

    def test_reflect_simple_validates(self):
        """Test validate() returns True"""
        from slotagent.plugins.reflect import ReflectSimple

        plugin = ReflectSimple()
        assert plugin.validate() is True


class TestLogPlugin:
    """Test LogPlugin"""

    def test_log_plugin_attributes(self):
        """Test LogPlugin has correct attributes"""
        from slotagent.plugins.observe import LogPlugin

        assert LogPlugin.layer == "observe"
        assert LogPlugin.plugin_id == "observe_log"

    def test_log_plugin_logs_execution(self):
        """Test LogPlugin logs execution info"""
        from slotagent.plugins.observe import LogPlugin

        plugin = LogPlugin(level="INFO")

        context = PluginContext(
            tool_id="test",
            tool_name="Test",
            params={},
            layer="observe",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.data["logged"] is True
        assert result.data["execution_id"] == context.execution_id

    def test_log_plugin_validates(self):
        """Test validate() returns True"""
        from slotagent.plugins.observe import LogPlugin

        plugin = LogPlugin()
        assert plugin.validate() is True
