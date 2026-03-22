# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for Healing plugins.

Tests auto-retry and recovery logic.
"""

import time
import uuid

from slotagent.types import PluginContext


class TestHealingRetry:
    """Test HealingRetry plugin - auto-retry with exponential backoff"""

    def test_healing_retry_basic_attributes(self):
        """Test HealingRetry has correct attributes"""
        from slotagent.plugins.healing import HealingRetry

        assert HealingRetry.layer == "healing"
        assert HealingRetry.plugin_id == "healing_retry"

    def test_healing_retry_initialization(self):
        """Test HealingRetry initialization with custom settings"""
        from slotagent.plugins.healing import HealingRetry

        plugin = HealingRetry(max_retries=5, initial_delay=2.0)
        assert plugin.validate() is True

    def test_healing_retry_returns_not_recovered_by_default(self):
        """Test that HealingRetry indicates not recovered (Phase 3 simple version)"""
        from slotagent.plugins.healing import HealingRetry

        plugin = HealingRetry(max_retries=3)

        context = PluginContext(
            tool_id="test",
            tool_name="Test",
            params={},
            layer="healing",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
            metadata={"error": "Tool execution failed"},
        )

        result = plugin.execute(context)
        assert result.success is True
        # Phase 3: Simple implementation, just reports not recovered
        assert result.data["recovered"] is False
        assert "retry_count" in result.data or "max_retries" in result.data


class TestHealingPluginValidation:
    """Test Healing plugin validation"""

    def test_healing_retry_validates(self):
        """Test validate() returns True"""
        from slotagent.plugins.healing import HealingRetry

        plugin = HealingRetry()
        assert plugin.validate() is True
