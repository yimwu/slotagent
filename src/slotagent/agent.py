# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
SlotAgent - Main entry point for the SlotAgent execution engine.

Provides a unified facade for tool execution, plugin management,
hook subscriptions, and approval workflows.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from slotagent.core.approval_manager import ApprovalManager
from slotagent.core.core_scheduler import CoreScheduler
from slotagent.core.hook_manager import HookManager
from slotagent.core.plugin_pool import PluginPool
from slotagent.core.tool_registry import ToolRegistry
from slotagent.llm.interface import LLMMessage
from slotagent.types import ApprovalRecord, Tool, ToolExecutionContext

if TYPE_CHECKING:
    from slotagent.interfaces import PluginInterface
    from slotagent.llm.interface import LLMInterface

logger = logging.getLogger("slotagent.agent")


class SlotAgent:
    """
    SlotAgent - The unified entry point for the SlotAgent execution engine.

    Supports two operating modes:
    - **Embedded mode**: called directly by external orchestrators (LangGraph etc.)
      via ``execute(tool_id, params)`` or ``batch_run(tasks)``.
    - **Independent mode**: processes natural-language queries end-to-end via
      ``run(user_query)`` using LLM-driven tool selection (requires ``llm``).

    Examples:
        >>> agent = SlotAgent()
        >>> agent.register_plugin(SchemaDefault())
        >>> agent.register_tool(weather_tool)
        >>> ctx = agent.execute("weather_query", {"location": "Beijing"})
        >>> print(ctx.status)  # ExecutionStatus.COMPLETED

        >>> # Independent mode
        >>> agent = SlotAgent(llm=my_llm)
        >>> ctx = agent.run("What is the weather in Shanghai?")
    """

    def __init__(
        self,
        llm: Optional["LLMInterface"] = None,
        plugin_pool: Optional[PluginPool] = None,
        tool_registry: Optional[ToolRegistry] = None,
        hook_manager: Optional[HookManager] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        """
        Initialize SlotAgent.

        Args:
            llm: LLM instance for independent mode and LLM-driven plugins.
            plugin_pool: Shared PluginPool (creates new if None).
            tool_registry: Shared ToolRegistry (creates new if None).
            hook_manager: Shared HookManager (creates new if None).
            approval_manager: Shared ApprovalManager (creates new if None).
        """
        if plugin_pool is None:
            plugin_pool = PluginPool()
        if tool_registry is None:
            tool_registry = ToolRegistry(plugin_pool)
        if hook_manager is None:
            hook_manager = HookManager()
        if approval_manager is None:
            approval_manager = ApprovalManager()

        self.plugin_pool = plugin_pool
        self.tool_registry = tool_registry
        self.hook_manager = hook_manager
        self.approval_manager = approval_manager
        self.llm = llm

        self._scheduler = CoreScheduler(
            plugin_pool=plugin_pool,
            tool_registry=tool_registry,
            hook_manager=hook_manager,
            llm=llm,
        )

    # -------------------------------------------------------------------------
    # Tool / Plugin management
    # -------------------------------------------------------------------------

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool for execution.

        Args:
            tool: Tool instance to register.

        Raises:
            ValueError: If tool_id already registered or validation fails.

        Examples:
            >>> agent.register_tool(weather_tool)
        """
        self.tool_registry.register(tool)

    def register_plugin(self, plugin: "PluginInterface") -> None:
        """
        Register a global plugin.

        Args:
            plugin: Plugin instance to register globally.

        Examples:
            >>> agent.register_plugin(SchemaDefault())
        """
        self.plugin_pool.register_global_plugin(plugin)

    # -------------------------------------------------------------------------
    # Execution interfaces
    # -------------------------------------------------------------------------

    def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
        """
        Execute a tool directly (embedded mode).

        Args:
            tool_id: Registered tool identifier.
            params: Tool parameters.

        Returns:
            ToolExecutionContext with execution state and results.

        Raises:
            ToolNotFoundError: If tool_id is not registered.

        Examples:
            >>> ctx = agent.execute("weather_query", {"location": "Beijing"})
        """
        return self._scheduler.execute(tool_id, params)

    def batch_run(self, tasks: List[Dict[str, Any]]) -> List[ToolExecutionContext]:
        """
        Execute multiple tools sequentially.

        Args:
            tasks: List of task dicts, each with ``tool_id`` and optional ``params``.
                   Example: ``[{"tool_id": "foo", "params": {"x": 1}}, ...]``

        Returns:
            List of ToolExecutionContext, one per task (in order).

        Examples:
            >>> results = agent.batch_run([
            ...     {"tool_id": "weather_query", "params": {"location": "Beijing"}},
            ...     {"tool_id": "weather_query", "params": {"location": "Shanghai"}},
            ... ])
        """
        results = []
        for task in tasks:
            tool_id = task["tool_id"]
            params = task.get("params", {})
            ctx = self._scheduler.execute(tool_id, params)
            results.append(ctx)
        return results

    def run(self, user_query: str) -> ToolExecutionContext:
        """
        Process a natural-language query in independent mode.

        Uses the injected LLM to select the appropriate tool and extract
        parameters from the query, then executes it through the normal
        plugin chain.

        Args:
            user_query: Natural-language query from the user.

        Returns:
            ToolExecutionContext from selected tool execution.

        Raises:
            ValueError: If no LLM is configured, no tools are registered,
                        or LLM returns an unparseable response.

        Examples:
            >>> agent = SlotAgent(llm=my_llm)
            >>> agent.register_tool(weather_tool)
            >>> ctx = agent.run("What's the weather in Beijing?")
        """
        if self.llm is None:
            raise ValueError(
                "LLM is required for independent mode. Pass llm= to SlotAgent()."
            )

        tools = self.tool_registry.list_tools()
        if not tools:
            raise ValueError("No tools registered. Use register_tool() first.")

        # Build tool descriptions for the LLM prompt
        tool_descriptions = [
            {
                "tool_id": t.tool_id,
                "name": t.name,
                "description": t.description,
                "schema": t.input_schema,
            }
            for t in tools
        ]

        prompt = (
            "You are a tool selector. Based on the user query and the available tools, "
            "select the most appropriate tool and extract the required parameters.\n\n"
            f"Available tools:\n{json.dumps(tool_descriptions, ensure_ascii=False, indent=2)}\n\n"
            f"User query: {user_query}\n\n"
            'Respond with JSON only (no markdown fences): '
            '{"tool_id": "<selected tool_id>", "params": {<extracted parameters>}}'
        )

        messages = [LLMMessage(role="user", content=prompt)]
        response = self.llm.complete(messages, temperature=0.1)

        try:
            parsed = json.loads(response.content)
            tool_id = parsed["tool_id"]
            params = parsed.get("params", {})
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(
                f"LLM returned invalid JSON response: {response.content!r}"
            ) from exc

        logger.info("run() selected tool=%s params=%s", tool_id, params)
        return self._scheduler.execute(tool_id, params)

    # -------------------------------------------------------------------------
    # Hook subscriptions (convenience wrappers)
    # -------------------------------------------------------------------------

    def on_before_schema(self, handler: Callable) -> None:
        """Subscribe to before_schema events."""
        self.hook_manager.subscribe("before_schema", handler)

    def on_after_schema(self, handler: Callable) -> None:
        """Subscribe to after_schema events."""
        self.hook_manager.subscribe("after_schema", handler)

    def on_before_guard(self, handler: Callable) -> None:
        """Subscribe to before_guard events."""
        self.hook_manager.subscribe("before_guard", handler)

    def on_before_exec(self, handler: Callable) -> None:
        """Subscribe to before_exec events."""
        self.hook_manager.subscribe("before_exec", handler)

    def on_after_exec(self, handler: Callable) -> None:
        """Subscribe to after_exec events."""
        self.hook_manager.subscribe("after_exec", handler)

    def on_fail(self, handler: Callable) -> None:
        """Subscribe to fail events."""
        self.hook_manager.subscribe("fail", handler)

    def on_after_healing(self, handler: Callable) -> None:
        """Subscribe to after_healing events."""
        self.hook_manager.subscribe("after_healing", handler)

    def on_retry_started(self, handler: Callable) -> None:
        """Subscribe to retry_started events."""
        self.hook_manager.subscribe("retry_started", handler)

    def on_after_reflect(self, handler: Callable) -> None:
        """Subscribe to after_reflect events."""
        self.hook_manager.subscribe("after_reflect", handler)

    def on_guard_block(self, handler: Callable) -> None:
        """Subscribe to guard_block events."""
        self.hook_manager.subscribe("guard_block", handler)

    def on_wait_approval(self, handler: Callable) -> None:
        """Subscribe to wait_approval events."""
        self.hook_manager.subscribe("wait_approval", handler)

    # -------------------------------------------------------------------------
    # Approval management (convenience wrappers)
    # -------------------------------------------------------------------------

    def approve(self, approval_id: str, approver: str = "system") -> ApprovalRecord:
        """
        Approve a pending execution.

        Args:
            approval_id: Approval request identifier.
            approver: Approver identifier (user/system name).

        Returns:
            Updated ApprovalRecord.

        Examples:
            >>> record = agent.approve(ctx.approval_id, approver="admin")
        """
        return self.approval_manager.approve(approval_id, approver=approver)

    def reject(
        self,
        approval_id: str,
        approver: str = "system",
        reason: str = "",
    ) -> ApprovalRecord:
        """
        Reject a pending execution.

        Args:
            approval_id: Approval request identifier.
            approver: Approver identifier.
            reason: Rejection reason.

        Returns:
            Updated ApprovalRecord.

        Examples:
            >>> record = agent.reject(ctx.approval_id, approver="admin", reason="Too risky")
        """
        return self.approval_manager.reject(approval_id, approver=approver, reason=reason)

    def list_pending_approvals(self) -> List[ApprovalRecord]:
        """
        List all pending approval requests.

        Returns:
            List of ApprovalRecord with PENDING status.

        Examples:
            >>> pending = agent.list_pending_approvals()
        """
        return self.approval_manager.list_pending()
