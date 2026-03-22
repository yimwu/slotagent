# Approval Workflow Architecture

## 概述 (Overview)

Human-in-the-Loop (HITL) 审批系统是 SlotAgent 的生产级安全机制。通过审批流程，高风险操作（如支付退款、数据删除）必须经过人工审核才能执行，确保系统的安全性和可控性。

## 设计原则

1. **非阻塞**: 审批请求不阻塞主线程，通过 Hook 事件异步通知
2. **状态驱动**: 清晰的状态机，明确的状态转移
3. **超时保护**: 审批请求自动超时，避免永久挂起
4. **可追溯**: 完整记录审批历史，支持审计

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Approval System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │      GuardHumanInLoop (审批触发插件)             │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  - 生成 approval_id                              │      │
│  │  - 触发 WaitApprovalEvent Hook                   │      │
│  │  - 返回 should_continue=False                    │      │
│  └──────────────────────────────────────────────────┘      │
│                      ↓                                      │
│  ┌──────────────────────────────────────────────────┐      │
│  │       ApprovalManager (审批状态管理)             │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  - create_approval(context) -> approval_id       │      │
│  │  - approve(approval_id, approver)                │      │
│  │  - reject(approval_id, approver, reason)         │      │
│  │  - get_approval(approval_id) -> ApprovalRecord   │      │
│  │  - check_timeout() -> List[expired_ids]          │      │
│  └──────────────────────────────────────────────────┘      │
│                      ↓                                      │
│  ┌──────────────────────────────────────────────────┐      │
│  │        ApprovalRecord (审批记录)                 │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  - approval_id: str                              │      │
│  │  - status: ApprovalStatus                        │      │
│  │  - tool_id: str                                  │      │
│  │  - params: Dict                                  │      │
│  │  - created_at: float                             │      │
│  │  - timeout_at: float                             │      │
│  │  - approved_at: Optional[float]                  │      │
│  │  - approver: Optional[str]                       │      │
│  │  - reject_reason: Optional[str]                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         ↑                                           ↑
   CoreScheduler                            External Systems
   (触发审批)                               (处理审批)
```

## 核心组件

### 1. ApprovalStatus (审批状态)

```python
class ApprovalStatus(str, Enum):
    """Approval status enumeration."""
    PENDING = "pending"      # 等待审批
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
    TIMEOUT = "timeout"      # 已超时
```

**状态转移**:
```
PENDING → APPROVED   (用户批准)
PENDING → REJECTED   (用户拒绝)
PENDING → TIMEOUT    (超时自动拒绝)
```

**不可逆转移**: 一旦进入 APPROVED/REJECTED/TIMEOUT，状态不可再改变

### 2. ApprovalRecord (审批记录)

```python
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
        timeout_at: Timeout timestamp (created_at + timeout_seconds)
        approved_at: Approval timestamp (None if not approved)
        rejected_at: Rejection timestamp (None if not rejected)
        approver: Approver identifier (username/user_id)
        reject_reason: Rejection reason
        metadata: Additional context for approval decision
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
```

### 3. ApprovalManager (审批管理器)

```python
class ApprovalManager:
    """
    Approval manager for managing approval lifecycle.

    Thread-safe implementation for concurrent approval operations.
    """

    def __init__(self, default_timeout: float = 300.0):
        """
        Initialize ApprovalManager.

        Args:
            default_timeout: Default approval timeout in seconds (default: 5 min)
        """
        self._approvals: Dict[str, ApprovalRecord] = {}
        self._lock = threading.Lock()
        self._default_timeout = default_timeout

    def create_approval(
        self,
        execution_id: str,
        tool_id: str,
        tool_name: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an approval request.

        Args:
            execution_id: Execution ID
            tool_id: Tool identifier
            tool_name: Tool name
            params: Tool parameters
            timeout: Custom timeout (seconds), uses default if None
            metadata: Additional approval context

        Returns:
            approval_id: Generated approval ID (UUID)

        Postconditions:
            - New ApprovalRecord created with status=PENDING
            - Record stored in _approvals
        """
        pass

    def approve(
        self,
        approval_id: str,
        approver: str
    ) -> ApprovalRecord:
        """
        Approve an approval request.

        Args:
            approval_id: Approval ID
            approver: Approver identifier

        Returns:
            Updated ApprovalRecord

        Raises:
            ValueError: If approval_id not found
            ValueError: If approval is not in PENDING status

        Postconditions:
            - status changed to APPROVED
            - approved_at set to current timestamp
            - approver recorded
        """
        pass

    def reject(
        self,
        approval_id: str,
        approver: str,
        reason: str
    ) -> ApprovalRecord:
        """
        Reject an approval request.

        Args:
            approval_id: Approval ID
            approver: Approver identifier
            reason: Rejection reason

        Returns:
            Updated ApprovalRecord

        Raises:
            ValueError: If approval_id not found
            ValueError: If approval is not in PENDING status

        Postconditions:
            - status changed to REJECTED
            - rejected_at set to current timestamp
            - approver and reject_reason recorded
        """
        pass

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """
        Get approval record by ID.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalRecord if found, None otherwise
        """
        pass

    def check_timeouts(self) -> List[str]:
        """
        Check for timed-out approvals and mark them.

        Returns:
            List of approval_ids that were marked as timeout

        Postconditions:
            - All PENDING approvals past timeout_at are marked TIMEOUT
        """
        pass

    def list_pending(self) -> List[ApprovalRecord]:
        """
        List all pending approvals.

        Returns:
            List of ApprovalRecords with status=PENDING
        """
        pass
```

### 4. GuardHumanInLoop (审批触发插件)

```python
class GuardHumanInLoop(PluginInterface):
    """
    Human-in-the-Loop guard plugin.

    Triggers approval workflow for high-risk operations.

    Examples:
        >>> plugin = GuardHumanInLoop(
        ...     approval_manager=manager,
        ...     timeout=600.0  # 10 minutes
        ... )
    """

    layer = 'guard'
    plugin_id = 'guard_human_in_loop'

    def __init__(
        self,
        approval_manager: ApprovalManager,
        timeout: Optional[float] = None,
        approval_required_always: bool = True
    ):
        """
        Initialize GuardHumanInLoop.

        Args:
            approval_manager: ApprovalManager instance
            timeout: Approval timeout (seconds)
            approval_required_always: If True, always require approval
        """
        self.approval_manager = approval_manager
        self.timeout = timeout
        self.approval_required_always = approval_required_always

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute human-in-the-loop check.

        Creates approval request and returns should_continue=False.

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
```

## 执行流程

### 正常审批流程

```
1. Tool 执行开始
   ↓
2. Schema 验证通过
   ↓
3. Guard 层: GuardHumanInLoop 执行
   ↓
4. ApprovalManager.create_approval()
   - 生成 approval_id
   - 创建 ApprovalRecord (status=PENDING)
   ↓
5. 返回 PluginResult(should_continue=False)
   ↓
6. CoreScheduler 检测到 pending_approval
   - 设置 context.status = PENDING_APPROVAL
   - 设置 context.approval_id
   ↓
7. CoreScheduler 触发 WaitApprovalEvent Hook
   ↓
8. 外部系统订阅者接收 Hook
   - 发送 IM 通知
   - 展示审批界面
   - 等待用户操作
   ↓
9a. 用户批准:
    - 调用 approval_manager.approve(approval_id, approver)
    - ApprovalRecord.status = APPROVED
    - 外部系统重新调用 scheduler.execute() (Phase 6 简化：不自动恢复)
    ↓
9b. 用户拒绝:
    - 调用 approval_manager.reject(approval_id, approver, reason)
    - ApprovalRecord.status = REJECTED
    - 执行终止
```

### 超时流程

```
1. ApprovalRecord 创建时设置 timeout_at
   ↓
2. 后台定时任务调用 check_timeouts()
   ↓
3. 检测到 current_time > timeout_at
   ↓
4. 标记 status = TIMEOUT
   ↓
5. 执行终止 (Phase 6 不自动发送通知)
```

## 设计决策

### D1: 审批不阻塞调度器
- **决策**: approve/reject 只更新状态，不触发自动恢复执行
- **理由**:
  - 保持调度器无状态
  - 避免复杂的执行恢复逻辑
  - 外部系统可选择是否重新执行
- **Phase 6 范围**: 仅实现状态管理，不实现自动恢复

### D2: 超时处理
- **决策**: check_timeouts() 由外部定时调用，不内置定时器
- **理由**:
  - 避免后台线程复杂性
  - 灵活的超时检查频率
  - 便于测试
- **Phase 6 范围**: 提供 check_timeouts() 方法，不自动调用

### D3: 审批记录持久化
- **决策**: Phase 6 仅内存存储，不持久化
- **理由**:
  - 简化实现
  - 持久化由外部系统决定
- **未来扩展**: Phase 7+ 可添加持久化层

### D4: 审批权限控制
- **决策**: Phase 6 不实现权限验证
- **理由**:
  - 权限系统应由外部实现
  - ApprovalManager 专注状态管理
- **未来扩展**: 外部系统在调用 approve/reject 前验证权限

## 集成示例

### 示例1: 配置审批插件

```python
# Create approval manager
approval_manager = ApprovalManager(default_timeout=300.0)  # 5 minutes

# Register GuardHumanInLoop plugin
plugin_pool.register_global_plugin(GuardHumanInLoop(
    approval_manager=approval_manager,
    timeout=600.0  # 10 minutes for this tool
))

# Register high-risk tool with approval
tool_registry.register(Tool(
    tool_id="payment_refund",
    name="Payment Refund",
    description="Refund payment to customer",
    input_schema={...},
    execute_func=refund_func,
    plugins={
        "guard": "guard_human_in_loop"  # Use approval guard
    }
))
```

### 示例2: 订阅审批事件

```python
def handle_approval_request(event: WaitApprovalEvent):
    """Handle approval request from Hook."""
    approval_id = event.approval_id

    # Get approval details
    approval = approval_manager.get_approval(approval_id)

    # Send IM notification
    send_im_message(
        channel="#approvals",
        message=f"⚠️ Approval Required\n"
                f"Tool: {approval.tool_name}\n"
                f"ID: {approval_id}\n"
                f"Timeout: {approval.timeout_at - time.time():.0f}s\n"
                f"[Approve] [Reject]"
    )

# Subscribe to wait_approval event
scheduler.hook_manager.subscribe('wait_approval', handle_approval_request)
```

### 示例3: 处理审批操作

```python
# User approves
approval_manager.approve(approval_id, approver="user@example.com")

# User rejects
approval_manager.reject(
    approval_id,
    approver="user@example.com",
    reason="Insufficient justification"
)

# Check status
approval = approval_manager.get_approval(approval_id)
if approval.status == ApprovalStatus.APPROVED:
    # Optionally re-execute tool
    # scheduler.execute(approval.tool_id, approval.params)
    pass
```

## 测试策略

### 单元测试

1. **ApprovalManager 测试**:
   - 创建审批请求
   - approve/reject 状态转移
   - 超时检测
   - 并发安全

2. **GuardHumanInLoop 测试**:
   - 触发审批流程
   - 返回正确的 PluginResult

3. **ApprovalRecord 测试**:
   - 数据完整性
   - 状态转移验证

### 集成测试

1. **完整审批流程**:
   - Tool 执行 → 审批触发 → Hook 事件 → approve → 状态更新

2. **超时流程**:
   - 创建审批 → 等待超时 → check_timeouts() → 状态变为 TIMEOUT

## 版本历史

- **1.0** (2026-03-22): 初始版本，定义审批工作流架构和核心接口
