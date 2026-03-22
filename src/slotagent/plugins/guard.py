# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Guard layer plugins - Permission control and approval.

Provides whitelist/blacklist-based access control for tools.
"""

from typing import List

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult


class GuardDefault(PluginInterface):
    """
    Default Guard plugin - whitelist/blacklist based control.

    Controls tool access through:
    - Blacklist: Block specific tools
    - Whitelist: Allow specific tools (when whitelist_only=True)
    - Whitelist takes precedence over blacklist

    Examples:
        >>> # Blacklist mode (default)
        >>> plugin = GuardDefault(blacklist=['dangerous_tool'])
        >>>
        >>> # Whitelist-only mode
        >>> plugin = GuardDefault(whitelist=['safe_tool'], whitelist_only=True)
    """

    layer = 'guard'
    plugin_id = 'guard_default'

    def __init__(
        self,
        blacklist: List[str] = None,
        whitelist: List[str] = None,
        whitelist_only: bool = False
    ):
        """
        Initialize GuardDefault plugin.

        Args:
            blacklist: List of blocked tool IDs
            whitelist: List of allowed tool IDs
            whitelist_only: If True, only whitelisted tools are allowed
        """
        self.blacklist = set(blacklist or [])
        self.whitelist = set(whitelist or [])
        self.whitelist_only = whitelist_only

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute guard check.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with approval status
        """
        tool_id = context.tool_id

        # Whitelist takes precedence
        if tool_id in self.whitelist:
            return PluginResult(
                success=True,
                data={'approved': True, 'reason': 'Tool is whitelisted'}
            )

        # Check blacklist
        if tool_id in self.blacklist:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f"Tool '{tool_id}' is in blacklist"
                }
            )

        # Whitelist-only mode
        if self.whitelist_only:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f"Tool '{tool_id}' not in whitelist (whitelist-only mode)"
                }
            )

        # Allow by default
        return PluginResult(
            success=True,
            data={'approved': True}
        )
