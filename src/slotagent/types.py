# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
SlotAgent 核心数据类型定义。

本模块定义了 SlotAgent 的核心数据结构:
- PluginContext: 插件执行上下文
- PluginResult: 插件执行结果
- ToolExecutionContext: 工具执行上下文
- ExecutionStatus: 执行状态枚举
- Tool: 工具定义
- Hook Events: Hook 事件类型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class ExecutionStatus(str, Enum):
    """
    工具执行状态。

    状态转移:
    RUNNING → COMPLETED (执行成功)
    RUNNING → FAILED (执行失败)
    RUNNING → PENDING_APPROVAL (需要审批)
    PENDING_APPROVAL → RUNNING (审批通过)
    PENDING_APPROVAL → FAILED (审批拒绝)
    """

    RUNNING = "running"  # 执行中
    PENDING_APPROVAL = "pending"  # 等待审批
    COMPLETED = "completed"  # 执行成功
    FAILED = "failed"  # 执行失败


class ApprovalStatus(str, Enum):
    """
    审批状态。

    状态转移:
    PENDING → APPROVED (用户批准)
    PENDING → REJECTED (用户拒绝)
    PENDING → TIMEOUT (超时自动拒绝)
    """

    PENDING = "pending"  # 等待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    TIMEOUT = "timeout"  # 已超时


@dataclass(frozen=True)
class PluginContext:
    """
    插件执行上下文。

    携带插件执行所需的所有信息,包括工具信息、参数、前序结果等。

    Attributes:
        tool_id: 工具唯一标识 (lowercase_with_underscore)
        tool_name: 工具可读名称
        params: 工具参数,已通过 Schema 验证的参数字典
        layer: 当前插件所在层 ('schema', 'guard', 'healing', 'reflect', 'observe')
        execution_id: 执行ID,用于追踪和日志关联 (UUID格式)
        timestamp: 上下文创建时间戳 (Unix timestamp)
        previous_results: 前序插件的执行结果,key为插件层名称
        metadata: 扩展元数据,供插件自定义使用

    Examples:
        >>> context = PluginContext(
        ...     tool_id="weather_query",
        ...     tool_name="天气查询",
        ...     params={"location": "Beijing"},
        ...     layer="schema",
        ...     execution_id=str(uuid.uuid4()),
        ...     timestamp=time.time()
        ... )
    """

    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    layer: str
    execution_id: str
    timestamp: float
    previous_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证字段约束"""
        # 验证 layer
        valid_layers = {"schema", "guard", "healing", "reflect", "observe"}
        if self.layer not in valid_layers:
            raise ValueError(f"Invalid layer '{self.layer}'. Must be one of: {valid_layers}")

        # 验证 tool_id 格式
        if not self.tool_id or not isinstance(self.tool_id, str):
            raise ValueError("tool_id must be a non-empty string")

        # 验证 execution_id
        if not self.execution_id or not isinstance(self.execution_id, str):
            raise ValueError("execution_id must be a non-empty string")


@dataclass
class PluginResult:
    """
    插件执行结果。

    统一封装插件执行状态、结果数据和错误信息。

    Attributes:
        success: 插件是否成功完成任务
        should_continue: 是否继续执行插件链,默认 True
        data: 插件返回的数据,可以是任意类型
        error: 错误信息,success=False 时应提供
        error_type: 错误类型,如 'ValidationError', 'PermissionDenied'
        metadata: 插件自定义元数据
        execution_time: 插件执行耗时(秒)

    Examples:
        >>> # 成功执行
        >>> result = PluginResult(success=True, data={'validated': True})
        >>>
        >>> # 执行失败
        >>> result = PluginResult(
        ...     success=False,
        ...     error="参数 'location' 不能为空",
        ...     error_type="ValidationError",
        ...     should_continue=False
        ... )
        >>>
        >>> # Guard 拦截
        >>> result = PluginResult(
        ...     success=True,
        ...     should_continue=False,
        ...     data={'blocked': True, 'reason': '需要人工审批'}
        ... )
    """

    success: bool
    should_continue: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None


@dataclass
class ToolExecutionContext:
    """
    工具执行上下文。

    存储工具执行的完整状态,包括工具定义、执行状态、插件链结果等。

    Attributes:
        tool_id: 工具ID
        tool_name: 工具名称
        params: 工具参数
        execution_id: 执行ID (UUID)
        status: 执行状态枚举
        start_time: 开始时间戳
        plugin_results: 各插件层执行结果,key为插件层名称
        final_result: 最终执行结果
        error: 错误信息
        approval_id: 审批ID (如需审批)
        end_time: 结束时间戳
        execution_time: 总执行耗时(秒)

    Examples:
        >>> context = ToolExecutionContext(
        ...     tool_id="weather_query",
        ...     tool_name="天气查询",
        ...     params={"location": "Beijing"},
        ...     execution_id=str(uuid.uuid4()),
        ...     status=ExecutionStatus.RUNNING,
        ...     start_time=time.time()
        ... )
    """

    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    execution_id: str
    status: ExecutionStatus
    start_time: float
    plugin_results: Dict[str, PluginResult] = field(default_factory=dict)
    final_result: Optional[Any] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    end_time: Optional[float] = None
    execution_time: Optional[float] = None

    def is_terminal(self) -> bool:
        """
        检查是否为终态。

        Returns:
            bool: True 表示终态 (COMPLETED 或 FAILED)
        """
        return self.status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}

    def is_pending_approval(self) -> bool:
        """
        检查是否在等待审批。

        Returns:
            bool: True 表示等待审批
        """
        return self.status == ExecutionStatus.PENDING_APPROVAL


@dataclass
class Tool:
    """
    Tool definition - first-class citizen in SlotAgent.

    Each tool can independently configure its plugin chain for
    fine-grained optimization.

    Attributes:
        tool_id: Unique tool identifier (lowercase_with_underscore)
        name: Display name
        description: Detailed description
        input_schema: JSON Schema for input validation
        execute_func: Tool execution function
        plugins: Tool-level plugin configuration (layer -> plugin_id)
        metadata: Additional metadata

    Examples:
        >>> def simple_query(params):
        ...     return {"results": [...]}
        >>>
        >>> tool = Tool(
        ...     tool_id="simple_query",
        ...     name="Simple Query",
        ...     description="Query data from local database",
        ...     input_schema={
        ...         "type": "object",
        ...         "properties": {
        ...             "table": {"type": "string"}
        ...         },
        ...         "required": ["table"]
        ...     },
        ...     execute_func=simple_query
        ... )
    """

    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    execute_func: Callable[[Dict[str, Any]], Any]
    plugins: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Hook Event Types
# =============================================================================


@dataclass
class HookEvent:
    """
    Base class for all Hook events.

    All fields are required to avoid dataclass inheritance issues.

    Attributes:
        event_type: Event type identifier
        execution_id: Execution ID (UUID)
        tool_id: Tool identifier
        tool_name: Tool name
        timestamp: Event timestamp (Unix timestamp)
        metadata: Optional metadata
    """

    event_type: str
    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BeforeExecEvent:
    """
    Event fired before tool execution starts.

    Triggered after schema validation and guard checks pass,
    right before calling tool.execute_func().
    """

    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    event_type: str = "before_exec"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AfterExecEvent:
    """
    Event fired after tool execution completes successfully.

    Triggered after tool.execute_func() returns, before reflect plugin.
    """

    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    result: Any
    execution_time: float
    event_type: str = "after_exec"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FailEvent:
    """
    Event fired when tool execution fails.

    Triggered when tool.execute_func() raises exception,
    or plugin chain fails.
    """

    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    error: str
    error_type: str
    failed_stage: str
    event_type: str = "fail"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GuardBlockEvent:
    """
    Event fired when Guard plugin blocks execution.

    Triggered when guard plugin returns should_continue=False
    (but not pending approval).
    """

    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    reason: str
    guard_plugin_id: str
    event_type: str = "guard_block"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WaitApprovalEvent:
    """
    Event fired when execution is pending approval.

    Triggered when GuardHumanInLoop plugin requires approval.
    """

    execution_id: str
    tool_id: str
    tool_name: str
    timestamp: float
    params: Dict[str, Any]
    approval_id: str
    approval_context: Optional[Dict[str, Any]] = None
    event_type: str = "wait_approval"
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Approval System Types
# =============================================================================


@dataclass
class ApprovalRecord:
    """
    Approval record for tracking approval requests.

    Attributes:
        approval_id: Unique approval identifier (UUID)
        status: Current approval status
        execution_id: Associated execution ID
        tool_id: Tool identifier
        tool_name: Tool name
        params: Tool parameters
        created_at: Creation timestamp
        timeout_at: Timeout timestamp
        approved_at: Approval timestamp (None if not approved)
        rejected_at: Rejection timestamp (None if not rejected)
        approver: Approver identifier
        reject_reason: Rejection reason
        metadata: Additional context for approval
    """

    approval_id: str
    status: ApprovalStatus
    execution_id: str
    tool_id: str
    tool_name: str
    params: Dict[str, Any]
    created_at: float
    timeout_at: float
    approved_at: Optional[float] = None
    rejected_at: Optional[float] = None
    approver: Optional[str] = None
    reject_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
