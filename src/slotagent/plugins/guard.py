# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Guard layer plugins - Permission control and approval.

Provides whitelist/blacklist-based access control and human-in-the-loop approval.
"""

from typing import List, Optional, TYPE_CHECKING

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

if TYPE_CHECKING:
    from slotagent.core.approval_manager import ApprovalManager


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


class GuardHumanInLoop(PluginInterface):
    """
    Human-in-the-Loop guard plugin.

    Triggers approval workflow for high-risk operations.
    Execution is paused until human approver makes decision.

    Examples:
        >>> from slotagent.core.approval_manager import ApprovalManager
        >>> manager = ApprovalManager()
        >>> plugin = GuardHumanInLoop(
        ...     approval_manager=manager,
        ...     timeout=600.0  # 10 minutes
        ... )
    """

    layer = 'guard'
    plugin_id = 'guard_human_in_loop'

    def __init__(
        self,
        approval_manager: 'ApprovalManager',
        timeout: Optional[float] = None
    ):
        """
        Initialize GuardHumanInLoop.

        Args:
            approval_manager: ApprovalManager instance
            timeout: Approval timeout (seconds), uses manager default if None
        """
        self.approval_manager = approval_manager
        self.timeout = timeout

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute human-in-the-loop check.

        Creates approval request and returns should_continue=False
        to pause execution.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with:
                - success=True
                - should_continue=False
                - data={'pending_approval': True, 'approval_id': ...}
        """
        # Create approval request
        approval_id = self.approval_manager.create_approval(
            execution_id=context.execution_id,
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            params=context.params,
            timeout=self.timeout,
            metadata={
                'plugin_id': self.plugin_id,
                'timestamp': context.timestamp
            }
        )

        return PluginResult(
            success=True,
            should_continue=False,
            data={
                'pending_approval': True,
                'approval_id': approval_id,
                'approval_context': {
                    'tool_id': context.tool_id,
                    'tool_name': context.tool_name,
                    'params_summary': self._summarize_params(context.params)
                }
            }
        )

    def _summarize_params(self, params: dict) -> str:
        """
        Summarize parameters for approval context.

        Args:
            params: Tool parameters

        Returns:
            Human-readable parameter summary
        """
        if not params:
            return "No parameters"

        # Simple summary: show top-level keys and values
        items = []
        for key, value in list(params.items())[:5]:  # Limit to 5 params
            if isinstance(value, (str, int, float, bool)):
                items.append(f"{key}={value}")
            elif isinstance(value, dict):
                items.append(f"{key}={{...}}")
            elif isinstance(value, list):
                items.append(f"{key}=[{len(value)} items]")
            else:
                items.append(f"{key}=<{type(value).__name__}>")

        summary = ", ".join(items)
        if len(params) > 5:
            summary += f" (+ {len(params) - 5} more)"

        return summary
