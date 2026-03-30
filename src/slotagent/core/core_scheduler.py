# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
CoreScheduler - Core execution engine for SlotAgent.

Manages plugin chain execution, state transitions, and Hook event dispatching.
This is the minimal kernel - only scheduling, no business logic.
"""

import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from slotagent.core.hook_manager import HookManager
from slotagent.core.plugin_pool import PluginPool
from slotagent.interfaces import ToolNotFoundError
from slotagent.types import (
    AfterExecEvent,
    AfterHealingEvent,
    AfterReflectEvent,
    AfterSchemaEvent,
    BeforeExecEvent,
    BeforeGuardEvent,
    BeforeSchemaEvent,
    ExecutionStatus,
    FailEvent,
    GuardBlockEvent,
    PluginContext,
    PluginResult,
    RetryStartedEvent,
    ToolExecutionContext,
    WaitApprovalEvent,
)

if TYPE_CHECKING:
    from slotagent.core.tool_registry import ToolRegistry
    from slotagent.llm.interface import LLMInterface


class CoreScheduler:
    """
    Core scheduling engine - the minimal kernel of SlotAgent.

    Responsibilities:
    - Execute plugin chains in correct order
    - Manage execution state transitions
    - Dispatch Hook events (Phase 5)
    - Coordinate approval workflow (Phase 6)

    Design Principles:
    - Minimal kernel: only scheduling, no business logic
    - All business logic in plugins
    - Hook-driven observability

    Usage:
        >>> from slotagent.core.tool_registry import ToolRegistry
        >>> plugin_pool = PluginPool()
        >>> tool_registry = ToolRegistry(plugin_pool)
        >>> scheduler = CoreScheduler(plugin_pool, tool_registry)
        >>> plugin_pool.register_global_plugin(SchemaDefault())
        >>> tool_registry.register(weather_tool)
        >>> context = scheduler.execute('weather_query', {'location': 'Beijing'})
        >>> print(context.status)  # ExecutionStatus.COMPLETED
    """

    def __init__(
        self,
        plugin_pool: Optional[PluginPool] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        hook_manager: Optional[HookManager] = None,
        llm: Optional["LLMInterface"] = None,
    ):
        """
        Initialize core scheduler.

        Args:
            plugin_pool: Optional PluginPool instance (creates new if None)
            tool_registry: Optional ToolRegistry instance (creates new if None)
            hook_manager: Optional HookManager instance (creates new if None)
            llm: Optional LLM instance for Healing/Reflect plugins (Phase 2)
        """
        if plugin_pool is None:
            plugin_pool = PluginPool()
        if tool_registry is None:
            # Import here to avoid circular dependency
            from slotagent.core.tool_registry import ToolRegistry

            tool_registry = ToolRegistry(plugin_pool)
        if hook_manager is None:
            hook_manager = HookManager()

        self.plugin_pool = plugin_pool
        self.tool_registry = tool_registry
        self.hook_manager = hook_manager
        self.llm = llm  # 新增: LLM 实例

    def register_tool(self, tool: Any) -> None:
        """
        Register a tool for execution.

        Deprecated: Use tool_registry.register() instead.

        Args:
            tool: Tool instance with tool_id, name, and execute() method

        Raises:
            ValueError: If tool_id already registered

        Examples:
            >>> scheduler.register_tool(weather_tool)
        """
        self.tool_registry.register(tool)

    def get_tool(self, tool_id: str) -> Optional[Any]:
        """
        Get registered tool by ID.

        Deprecated: Use tool_registry.get_tool() instead.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool instance or None if not found

        Examples:
            >>> tool = scheduler.get_tool('weather_query')
        """
        return self.tool_registry.get_tool(tool_id)

    def execute(self, tool_id: str, params: Dict[str, Any]) -> ToolExecutionContext:
        """
        Execute a tool with plugin chain processing.

        This is the main entry point for tool execution. It:
        1. Validates tool exists
        2. Creates execution context
        3. Executes plugin chain (schema → guard → tool → healing → reflect → observe)
        4. Manages state transitions
        5. Returns complete execution context

        Args:
            tool_id: Tool identifier (must be registered)
            params: Tool parameters (will be validated by Schema plugin)

        Returns:
            ToolExecutionContext with complete execution state and results

        Raises:
            ToolNotFoundError: If tool_id not registered

        Contract:
            Precondition:
                - tool_id is registered
                - params is not None (can be empty dict)

            Postcondition:
                - Returns non-None context
                - context.status is terminal (COMPLETED/FAILED/PENDING_APPROVAL)
                - context.execution_time is set

        Examples:
            >>> context = scheduler.execute('weather_query', {'location': 'Beijing'})
            >>> if context.status == ExecutionStatus.COMPLETED:
            ...     print(context.final_result)
        """
        # 1. Validate tool exists
        tool = self.get_tool(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{tool_id}' not found")

        # 2. Create execution context
        context = ToolExecutionContext(
            tool_id=tool_id,
            tool_name=tool.name,
            params=params,
            execution_id=str(uuid.uuid4()),
            status=ExecutionStatus.RUNNING,
            start_time=time.time(),
        )

        try:
            # 3. Execute plugin chain
            context = self._execute_plugin_chain(context, tool)

        except Exception as e:
            # Catch any unexpected errors
            context.status = ExecutionStatus.FAILED
            context.error = str(e)

        finally:
            # 4. Record execution time
            context.end_time = time.time()
            context.execution_time = context.end_time - context.start_time

        return context

    def _execute_plugin_chain(
        self, context: ToolExecutionContext, tool: Any
    ) -> ToolExecutionContext:
        """
        Execute complete plugin chain for a tool.

        Plugin execution order:
        1. Schema - parameter validation
        2. Guard - permission control & approval
        3. Tool execution
        4. Healing - auto-recovery on failure (Phase 3)
        5. Reflect - task verification (Phase 3)
        6. Observe - lifecycle observation (Phase 3)

        Args:
            context: Execution context
            tool: Tool instance

        Returns:
            Updated execution context
        """
        previous_results = {}

        # 1. Schema layer
        schema_plugin = self.plugin_pool.get_plugin("schema", context.tool_id)
        if schema_plugin:
            self.hook_manager.emit(
                BeforeSchemaEvent(
                    execution_id=context.execution_id,
                    tool_id=context.tool_id,
                    tool_name=context.tool_name,
                    timestamp=time.time(),
                    params=context.params,
                )
            )
            result = self._execute_plugin(schema_plugin, context, previous_results, tool)
            context.plugin_results["schema"] = result
            previous_results["schema"] = result.data

            self.hook_manager.emit(
                AfterSchemaEvent(
                    execution_id=context.execution_id,
                    tool_id=context.tool_id,
                    tool_name=context.tool_name,
                    timestamp=time.time(),
                    params=context.params,
                    success=result.success,
                    should_continue=result.should_continue,
                    schema_plugin_id=schema_plugin.plugin_id,
                    error=result.error or "",
                )
            )

            if not result.should_continue:
                context.status = ExecutionStatus.FAILED
                context.error = result.error
                # Emit fail event for schema validation failure
                self.hook_manager.emit(
                    FailEvent(
                        execution_id=context.execution_id,
                        tool_id=context.tool_id,
                        tool_name=context.tool_name,
                        timestamp=time.time(),
                        params=context.params,
                        error=result.error or "Schema validation failed",
                        error_type=result.error_type or "ValidationError",
                        failed_stage="schema",
                    )
                )
                return context

        # 2. Guard layer
        guard_plugin = self.plugin_pool.get_plugin("guard", context.tool_id)
        if guard_plugin:
            self.hook_manager.emit(
                BeforeGuardEvent(
                    execution_id=context.execution_id,
                    tool_id=context.tool_id,
                    tool_name=context.tool_name,
                    timestamp=time.time(),
                    params=context.params,
                )
            )
            result = self._execute_plugin(guard_plugin, context, previous_results, tool)
            context.plugin_results["guard"] = result
            previous_results["guard"] = result.data

            if not result.should_continue:
                # Check if pending approval
                if result.data and result.data.get("pending_approval"):
                    context.status = ExecutionStatus.PENDING_APPROVAL
                    context.approval_id = result.data.get("approval_id")
                    # Emit wait_approval event
                    self.hook_manager.emit(
                        WaitApprovalEvent(
                            execution_id=context.execution_id,
                            tool_id=context.tool_id,
                            tool_name=context.tool_name,
                            timestamp=time.time(),
                            params=context.params,
                            approval_id=context.approval_id or "",
                            approval_context=result.data.get("approval_context"),
                        )
                    )
                else:
                    # Guard blocked
                    context.status = ExecutionStatus.FAILED
                    context.error = result.data.get("reason", "Blocked by guard")
                    # Emit guard_block event
                    self.hook_manager.emit(
                        GuardBlockEvent(
                            execution_id=context.execution_id,
                            tool_id=context.tool_id,
                            tool_name=context.tool_name,
                            timestamp=time.time(),
                            params=context.params,
                            reason=context.error,
                            guard_plugin_id=guard_plugin.plugin_id,
                        )
                    )

                return context

        # Emit before_exec event
        self.hook_manager.emit(
            BeforeExecEvent(
                execution_id=context.execution_id,
                tool_id=context.tool_id,
                tool_name=context.tool_name,
                timestamp=time.time(),
                params=context.params,
            )
        )

        # 3. Execute tool with Healing retry support
        healing_plugin = self.plugin_pool.get_plugin("healing", context.tool_id)
        max_attempts = 1 + (getattr(healing_plugin, "max_retries", 1) if healing_plugin else 0)

        tool_succeeded = False
        for attempt in range(max_attempts):
            try:
                final_result = tool.execute_func(context.params)
                context.final_result = final_result

                # Store result for Reflect plugin
                previous_results["result"] = final_result
                tool_succeeded = True

                # Emit after_exec event
                self.hook_manager.emit(
                    AfterExecEvent(
                        execution_id=context.execution_id,
                        tool_id=context.tool_id,
                        tool_name=context.tool_name,
                        timestamp=time.time(),
                        params=context.params,
                        result=final_result,
                        execution_time=time.time() - context.start_time,
                    )
                )
                break  # Success — exit retry loop

            except Exception as e:
                tool_error = str(e)
                previous_results["error"] = tool_error
                previous_results["error_type"] = type(e).__name__

                # Emit fail event for each attempt
                self.hook_manager.emit(
                    FailEvent(
                        execution_id=context.execution_id,
                        tool_id=context.tool_id,
                        tool_name=context.tool_name,
                        timestamp=time.time(),
                        params=context.params,
                        error=tool_error,
                        error_type=type(e).__name__,
                        failed_stage="execute",
                    )
                )

                # 4. Healing layer — try to recover before next attempt
                if healing_plugin and attempt < max_attempts - 1:
                    healing_result = self._execute_plugin(
                        healing_plugin, context, previous_results, tool
                    )
                    context.plugin_results["healing"] = healing_result
                    previous_results["healing"] = healing_result.data

                    fixed_params = healing_result.data.get("fixed_params") if healing_result.data else None
                    fixed_params_applied = bool(fixed_params)
                    if fixed_params:
                        context.params = fixed_params

                    recovered = bool(
                        healing_result.success
                        and healing_result.data
                        and healing_result.data.get("recovered")
                    )

                    self.hook_manager.emit(
                        AfterHealingEvent(
                            execution_id=context.execution_id,
                            tool_id=context.tool_id,
                            tool_name=context.tool_name,
                            timestamp=time.time(),
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            recovered=recovered,
                            fixed_params_applied=fixed_params_applied,
                            healing_plugin_id=healing_plugin.plugin_id,
                            error=healing_result.error or "",
                        )
                    )

                    if recovered:
                        self.hook_manager.emit(
                            RetryStartedEvent(
                                execution_id=context.execution_id,
                                tool_id=context.tool_id,
                                tool_name=context.tool_name,
                                timestamp=time.time(),
                                attempt=attempt + 1,
                                next_attempt=attempt + 2,
                                max_attempts=max_attempts,
                                reason=healing_result.error or "Recovered by healing plugin",
                            )
                        )
                        continue  # Retry with fixed params

                # Healing unavailable or failed — mark execution as failed
                context.status = ExecutionStatus.FAILED
                context.error = f"Tool execution failed: {tool_error}"
                return context

        if not tool_succeeded:
            # All retries exhausted (should not normally reach here)
            return context

        # 5. Reflect layer
        reflect_plugin = self.plugin_pool.get_plugin("reflect", context.tool_id)
        if reflect_plugin:
            result = self._execute_plugin(reflect_plugin, context, previous_results, tool)
            context.plugin_results["reflect"] = result
            previous_results["reflect"] = result.data
            self.hook_manager.emit(
                AfterReflectEvent(
                    execution_id=context.execution_id,
                    tool_id=context.tool_id,
                    tool_name=context.tool_name,
                    timestamp=time.time(),
                    reflect_plugin_id=reflect_plugin.plugin_id,
                    success=result.success,
                    should_continue=result.should_continue,
                    error=result.error or "",
                )
            )

        # 6. Observe layer
        observe_plugin = self.plugin_pool.get_plugin("observe", context.tool_id)
        if observe_plugin:
            result = self._execute_plugin(observe_plugin, context, previous_results, tool)
            context.plugin_results["observe"] = result
            previous_results["observe"] = result.data

        # 6. Mark as completed
        context.status = ExecutionStatus.COMPLETED

        return context

    def _execute_plugin(
        self, plugin: Any, context: ToolExecutionContext, previous_results: Dict[str, Any], tool: Any
    ) -> PluginResult:
        """
        Execute a single plugin.

        Args:
            plugin: Plugin instance
            context: Tool execution context
            previous_results: Results from previous plugins
            tool: Tool instance (for accessing description and schema)

        Returns:
            Plugin execution result
        """
        # Create plugin context
        plugin_context = PluginContext(
            tool_id=context.tool_id,
            tool_name=context.tool_name,
            params=context.params,
            layer=plugin.layer,
            execution_id=context.execution_id,
            timestamp=time.time(),
            previous_results=previous_results if previous_results else None,
            tool_description=tool.description,  # 新增: 工具描述
            tool_schema=tool.input_schema,  # 新增: 工具schema
        )

        # Execute plugin
        try:
            result = plugin.execute(plugin_context)
            return result

        except Exception as e:
            # Plugin execution failed
            return PluginResult(
                success=False,
                should_continue=False,
                error=f"Plugin execution error: {str(e)}",
                error_type="PluginExecutionError",
            )
