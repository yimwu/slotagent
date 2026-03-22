# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for Guard plugins.

Tests permission control and blocking logic.
"""

import time
import uuid

from slotagent.types import PluginContext


class TestGuardDefault:
    """Test GuardDefault plugin - whitelist/blacklist control"""

    def test_guard_default_allows_by_default(self):
        """Test that GuardDefault allows all by default"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault()

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is True
        assert result.data["approved"] is True

    def test_guard_default_blocks_blacklisted_tool(self):
        """Test that GuardDefault blocks blacklisted tools"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault(blacklist=["dangerous_tool", "risky_tool"])

        context = PluginContext(
            tool_id="dangerous_tool",
            tool_name="Dangerous",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is False
        assert result.data["blocked"] is True
        assert "blacklist" in result.data["reason"].lower()

    def test_guard_default_allows_non_blacklisted(self):
        """Test that GuardDefault allows non-blacklisted tools"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault(blacklist=["dangerous_tool"])

        context = PluginContext(
            tool_id="safe_tool",
            tool_name="Safe",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is True

    def test_guard_default_whitelist_only_mode(self):
        """Test GuardDefault in whitelist-only mode"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault(whitelist=["approved_tool"], whitelist_only=True)

        # Non-whitelisted tool should be blocked
        context = PluginContext(
            tool_id="other_tool",
            tool_name="Other",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is False
        assert result.data["blocked"] is True

    def test_guard_default_allows_whitelisted(self):
        """Test that GuardDefault allows whitelisted tools"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault(whitelist=["approved_tool"], whitelist_only=True)

        context = PluginContext(
            tool_id="approved_tool",
            tool_name="Approved",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is True

    def test_guard_default_whitelist_overrides_blacklist(self):
        """Test that whitelist takes precedence over blacklist"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault(
            whitelist=["special_tool"],
            blacklist=["special_tool"],  # Also in blacklist
            whitelist_only=False,
        )

        context = PluginContext(
            tool_id="special_tool",
            tool_name="Special",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        # Whitelist should override blacklist
        assert result.success is True
        assert result.should_continue is True

    def test_guard_default_validation_passes(self):
        """Test that validate() returns True"""
        from slotagent.plugins.guard import GuardDefault

        plugin = GuardDefault()
        assert plugin.validate() is True


class TestGuardPluginAttributes:
    """Test Guard plugin class attributes"""

    def test_guard_default_has_correct_attributes(self):
        """Test GuardDefault has correct layer and plugin_id"""
        from slotagent.plugins.guard import GuardDefault

        assert GuardDefault.layer == "guard"
        assert GuardDefault.plugin_id == "guard_default"
