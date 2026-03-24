# SlotAgent FAQ (常见问题)

**版本：** 0.2.0-alpha
**最后更新��** 2026-03-22

本文档回答 SlotAgent 使用过程中的常见问题。

---

## 目录

- [一般问题](#一般问题)
- [架构与设计](#架构与设计)
- [使用问题](#使用问题)
- [性能与优化](#性能与优化)
- [部署与生产](#部署与生产)

---

## 一般问题

### Q1: SlotAgent 是什么？适用于什么场景？

**A:** SlotAgent 是一个工业级的 LLM Agent 执行引擎，专注于工具执行的**可靠性、安全性和可观测性**。

**适用场景：**
- ✅ 需要严格参数验证的 LLM 工具调用
- ✅ 高风险操作需要人工审批的场景
- ✅ 需要细粒度权限控制（工具级、用户级）
- ✅ 需要完整可观测性和审计日志的企业应用
- ✅ 现有 LangGraph/LangChain 应用需要增强工具执行层

**不适用场景：**
- ❌ 简单的函数调用（过度设计）
- ❌ 对性能要求极高的实时系统（插件链有少量开销）
- ❌ 不需要任何控制和验证的原型开发

---

### Q2: SlotAgent 与 LangChain/LangGraph 的关系？

**A:** SlotAgent 可以**独立使用**或**嵌入到 LangChain/LangGraph**。

**两种模式：**

1. **独立模式**：SlotAgent 作为完整的 Agent 执行引擎
   - 适合：构建新的 Agent 应用
   - 优势：完全控制、无依赖、轻量

2. **嵌入模式**：作为 LangGraph 的工具执行层
   - 适合：增强现有 LangGraph 应用的工具执行
   - 优势：插件化增强、保留 LangGraph 的状态管理和流程控制

**示例（嵌入模式）：**
```python
from langgraph.graph import StateGraph
from slotagent.core import CoreScheduler

scheduler = CoreScheduler()

def tool_node(state):
    """在 LangGraph 节点中调用 SlotAgent"""
    context = scheduler.execute(state['tool_id'], state['params'])
    return {'result': context.final_result, 'status': context.status}

graph = StateGraph()
graph.add_node('tool_execution', tool_node)
```

---

### Q3: SlotAgent 是否支持异步执行？

**A:** 当前版本 (0.2.0-alpha) **暂不支持异步**，所有执行都是同步的。

**路线图：**
- Phase 9（计划中）：添加异步支持（`async def execute()`, `await tool.execute_func()`）

**��前解决方案：**
- 如需异步，可在外层使用 `asyncio.run_in_executor()` 包装
- 或使用线程池并发执行多个工具

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)

async def execute_tool_async(scheduler, tool_id, params):
    loop = asyncio.get_event_loop()
    context = await loop.run_in_executor(
        executor,
        scheduler.execute,
        tool_id,
        params
    )
    return context
```

---

## 架构与设计

### Q4: 为什么插件必须按固定顺序执行？

**A:** 固定顺序保证了**可预测性**和**安全性**。

**执行顺序逻辑：**
```
Schema → Guard → [Tool] → Healing → Reflect → Observe
```

- **Schema 在最前**：确保无效参数不会进入后续环节
- **Guard 在 Schema 后**：在验证通过的基础上做权限检查
- **Tool 执行在中间**：前置验证通过后才执行
- **Healing 在 Tool 后**：工具失败后尝试恢复
- **Reflect 在 Healing 后**：判断最终结果是否符合预期
- **Observe 在最后**：记录完整流程（包括失败和恢复）

**为什么不允许自定义顺序？**
- 防止安全漏洞（如在 Guard 前执行工具）
- 统一架构，降低理解成本
- 简化插件开发（每层职责清晰）

---

### Q5: 工具级插件配置的优先级是怎样的？

**A:** **工具级插件 > 全局插件**（完全覆盖，不是合并）

**示例：**
```python
# 全局插件
scheduler.plugin_pool.register_global_plugin(SchemaDefault(...))  # id: schema_default
scheduler.plugin_pool.register_global_plugin(GuardDefault(...))   # id: guard_default

# 工具A：使用全局插件
tool_a = Tool(tool_id='a', ..., plugins=None)
# 实际使用：schema_default, guard_default

# 工具B：覆盖 schema 层
tool_b = Tool(tool_id='b', ..., plugins={'schema': 'schema_strict'})
# 实际使用：schema_strict, guard_default（guard 仍使用全局）

# 工具C：覆盖多层
tool_c = Tool(tool_id='c', ..., plugins={'schema': 'schema_strict', 'guard': 'guard_human_in_loop'})
# 实际使用：schema_strict, guard_human_in_loop
```

**注意：** 未在 `plugins` 中指定的层仍使用全局插件。

---

### Q6: 如果不想用某一层的插件怎么办？

**A:** 不注册该层的全局插件，也不在工具级配置该层，该层就会被**跳过**。

**示例：**
```python
# 只注册 schema 和 observe，不注册 guard/healing/reflect
scheduler.plugin_pool.register_global_plugin(SchemaDefault(...))
scheduler.plugin_pool.register_global_plugin(LogPlugin())

# 执行时插件链为：schema → [tool] → observe
# guard/healing/reflect 层被跳过
```

**最佳实践：**
- 轻量级工具：只用 schema + observe
- 中等风险工具：schema + guard + observe
- 高风险工具：schema + guard + healing + reflect + observe

---

## 使用问题

### Q7: 如何在工具执行函数中访问上下文信息（如用户ID）？

**A:** 当前版本工具函数签名为 `lambda params: ...`，**不直接传递上下文**。

**解决方案 1：通过 params 传递**
```python
# 调用时包含上下文信息
scheduler.execute('my_tool', {
    'user_id': 'user123',
    'action': 'delete',
    'item_id': 'item456'
})

# 工具函数中使用
def my_tool_func(params):
    user_id = params['user_id']
    # ... 使用 user_id ...
    return result
```

**解决方案 2：使用闭包捕获上下文**
```python
class ToolFactory:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger

    def create_tool(self):
        def execute_func(params):
            # 可访问 self.db, self.logger
            self.logger.info(f"Executing tool with {params}")
            return self.db.query(params['id'])

        return Tool(
            tool_id='my_tool',
            execute_func=execute_func,
            ...
        )

factory = ToolFactory(db=db, logger=logger)
tool = factory.create_tool()
scheduler.register_tool(tool)
```

**计划改进（v0.2.0）：**
```python
# 未来可能支持
def execute_func(params, context: ExecutionContext):
    user_id = context.metadata['user_id']
    ...
```

---

### Q8: 如何在自定义插件中访问 PluginContext 的额外信息？

**A:** `PluginContext.metadata` 和 `PluginContext.previous_results` 可用于传递信息。

**示例：自定义 Guard 插件检查用户角色**
```python
class GuardRBAC(PluginInterface):
    layer = 'guard'
    plugin_id = 'guard_rbac'

    def __init__(self, permissions):
        self.permissions = permissions

    def execute(self, context: PluginContext) -> PluginResult:
        # 从 metadata 获取用户信息
        user_role = context.metadata.get('user_role', 'guest')
        required_roles = self.permissions.get(context.tool_id, [])

        if user_role in required_roles:
            return PluginResult(success=True)
        else:
            return PluginResult(
                success=True,
                should_continue=False,
                data={'reason': f'Role {user_role} not authorized'}
            )
```

**如何设置 metadata？**
- 当前版本：需要在 `CoreScheduler.execute()` 前通过某种方式注入（如修改源码或使用包装器）
- 计划改进：`scheduler.execute(tool_id, params, metadata={...})`

---

### Q9: 审批流程中，如何关联审批请求和原始执行？

**A:** 使用 `execution_id` 和 `approval_id` 进行关联。

**完整流程：**
```python
# 1. 执行工具（触发审批）
context = scheduler.execute('payment_refund', {'amount': 1000})

execution_id = context.execution_id
approval_id = context.approval_id

# 2. 保存关联关系
pending_executions[approval_id] = {
    'execution_id': execution_id,
    'tool_id': context.tool_id,
    'params': context.params,
    'timestamp': context.start_time
}

# 3. 审批通过后处理
def handle_approval(approval_id, approved):
    exec_info = pending_executions.pop(approval_id)

    if approved:
        # 记录审批通过
        audit_log.record(
            execution_id=exec_info['execution_id'],
            approval_id=approval_id,
            status='approved'
        )
        # 执行后续操作...
    else:
        # 记录审批拒绝
        audit_log.record(
            execution_id=exec_info['execution_id'],
            approval_id=approval_id,
            status='rejected'
        )
```

---

### Q10: Hook 订阅者抛出异常会影响工具执行吗？

**A:** **不会影响**。订阅者异常被捕获并记录，不影响主流程。

**设计原则：** Hook 系统是**旁路观测**，不应该影响核心执行。

**示例：**
```python
def buggy_subscriber(event):
    raise ValueError("Subscriber error")

hook_manager.subscribe('before_exec', buggy_subscriber)

# 工具仍正常执行
context = scheduler.execute('my_tool', {})
assert context.status == ExecutionStatus.COMPLETED

# 异常会被记录（如果启用日志）
# [WARNING] Subscriber error in 'before_exec': Subscriber error
```

**最佳实践：**
- 在订阅者内部捕获和处理异常
- 使用日志记录而不是抛出异常
- 关键逻辑不要依赖 Hook（Hook 是辅助功能）

---

## 性能与优化

### Q11: 插件链会带来多少性能开销？

**A:** 插件链开销通常在 **微秒到毫秒级**，对大部分场景可忽略。

**基准测试（初步数据）：**
- 无插件执行：~0.1ms
- 5层空插件链：~0.5ms
- 5层实际插件（schema+guard+log）：~2-5ms
- 复杂工具执行（如 HTTP 请求）：100ms-1000ms

**结论：** 插件开销通常远小于工具本身的执行时间（如网络请求、数据库查询）。

**优化建议：**
- 轻量级工具：减少插件层数（只用必要的）
- 避免在插件中做复杂计算
- LogPlugin 在生产环境可替换为轻量级日志

---

### Q12: 如何优化高频调用场景的性能？

**A:** 采用以下策略：

**1. 减少插件层数**
```python
# 高频工具：最小��件配置
high_freq_tool = Tool(
    tool_id='cache_query',
    plugins={'observe': 'log_plugin'},  # 只用 observe
    ...
)
```

**2. 复用 CoreScheduler 实例**
```python
# 好：复用实例
scheduler = CoreScheduler()
for i in range(1000):
    scheduler.execute('tool', {})

# 差：每次创建新实例
for i in range(1000):
    scheduler = CoreScheduler()  # 开销大
    scheduler.execute('tool', {})
```

**3. 批量执行（计划中功能）**
```python
# 未来支持
results = scheduler.batch_execute([
    ('tool_a', params_a),
    ('tool_b', params_b),
    ...
])
```

**4. 使用工具级插件优化**
```python
# 低频工具：完整插件链
low_freq_tool = Tool(
    tool_id='complex_task',
    plugins={
        'schema': 'schema_strict',
        'guard': 'guard_human_in_loop',
        'observe': 'log_plugin'
    }
)

# 高频工具：最小插件
high_freq_tool = Tool(
    tool_id='fast_query',
    plugins={}  # 不用插件，直接执行
)
```

---

## 部署与生产

### Q13: 在生产环境如何管理审批请求？

**A:** 建议使用**持久化存储 + 后台服务**。

**架构建议：**

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  SlotAgent  │─────>│  消息队列   │─────>│  审批服务    │
│  (执行层)   │      │  (Redis/MQ) │      │  (Web UI)    │
└─────────────┘      └─────────────┘      └──────────────┘
       │                                          │
       │                                          │
       └──────────────┬───────────────────────────┘
                      │
               ┌──────▼──────┐
               │ 审批记录DB  │
               │ (PostgreSQL)│
               └─────────────┘
```

**代码示例：**
```python
# 1. 使用 Redis 存储审批状态
import redis
import json

r = redis.Redis()

def on_wait_approval(event):
    # 将审批请求写入 Redis
    approval_data = {
        'approval_id': event.approval_id,
        'tool_id': event.tool_id,
        'params': event.params,
        'timestamp': event.timestamp
    }

    r.lpush('pending_approvals', json.dumps(approval_data))
    r.hset(f'approval:{event.approval_id}', mapping=approval_data)

    # 发送通知
    notify_approver(event.approval_id)

hook_manager.subscribe('wait_approval', on_wait_approval)

# 2. 审批服务处理请求
def approval_service():
    while True:
        # 从队列获取待审批请求
        data = r.brpop('pending_approvals', timeout=1)
        if data:
            approval_data = json.loads(data[1])
            # 显示在 Web UI，等待审批人操作
            show_approval_ui(approval_data)

# 3. 审批人操作后调用
def approve_request(approval_id, approver):
    approval_manager.approve(approval_id, approver)
    r.delete(f'approval:{approval_id}')

def reject_request(approval_id, approver, reason):
    approval_manager.reject(approval_id, approver, reason)
    r.delete(f'approval:{approval_id}')
```

---

### Q14: 如何处理审批超时？

**A:** 使用**后台定时任务**检查超时。

**方案 1：使用 APScheduler**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler_bg = BackgroundScheduler()

def check_timeouts_job():
    expired_ids = approval_manager.check_timeouts()
    for approval_id in expired_ids:
        record = approval_manager.get_approval(approval_id)
        logger.warning(f"Approval {approval_id} timed out")

        # 通知相关人员
        notify_timeout(record.tool_id, record.params, approval_id)

# 每分钟检查一次
scheduler_bg.add_job(check_timeouts_job, 'interval', minutes=1)
scheduler_bg.start()
```

**方案 2：使用 Celery 定时任务**
```python
from celery import Celery
from celery.schedules import crontab

app = Celery('slotagent_tasks')

@app.task
def check_approval_timeouts():
    expired_ids = approval_manager.check_timeouts()
    # ... 处理超时 ...

app.conf.beat_schedule = {
    'check-timeouts-every-minute': {
        'task': 'tasks.check_approval_timeouts',
        'schedule': 60.0,  # 每60秒
    },
}
```

---

### Q15: 如何实现审计日志和合规性？

**A:** 使用 **Hook 系统 + 持久化存储**。

**完整审计方案：**

```python
import logging
from datetime import datetime

# 1. 配置审计日志
audit_logger = logging.getLogger('slotagent.audit')
audit_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('/var/log/slotagent/audit.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
audit_logger.addHandler(file_handler)

# 2. 记录所有工具执行
def audit_execution(event):
    audit_logger.info(json.dumps({
        'event_type': event.event_type,
        'execution_id': event.execution_id,
        'tool_id': event.tool_id,
        'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
        'params': event.params if hasattr(event, 'params') else None,
        'result': event.result if hasattr(event, 'result') else None,
        'error': event.error if hasattr(event, 'error') else None
    }))

hook_manager.subscribe('before_exec', audit_execution)
hook_manager.subscribe('after_exec', audit_execution)
hook_manager.subscribe('fail', audit_execution)
hook_manager.subscribe('guard_block', audit_execution)

# 3. 记录审批操作
def audit_approval(approval_id, action, approver, reason=None):
    record = approval_manager.get_approval(approval_id)

    audit_logger.info(json.dumps({
        'event_type': 'approval_action',
        'approval_id': approval_id,
        'execution_id': record.execution_id,
        'tool_id': record.tool_id,
        'action': action,  # 'approved' | 'rejected'
        'approver': approver,
        'reason': reason,
        'timestamp': datetime.now().isoformat()
    }))

# 审批时调用
approval_manager.approve(approval_id, approver)
audit_approval(approval_id, 'approved', approver)
```

**审计日志格式（示例）：**
```json
{
  "event_type": "before_exec",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_id": "payment_refund",
  "timestamp": "2026-03-22T10:30:45.123456",
  "params": {"amount": 1000, "order_id": "ORD-12345"}
}

{
  "event_type": "approval_action",
  "approval_id": "660e8400-e29b-41d4-a716-446655440001",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_id": "payment_refund",
  "action": "approved",
  "approver": "admin@company.com",
  "timestamp": "2026-03-22T10:32:10.456789"
}

{
  "event_type": "after_exec",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_id": "payment_refund",
  "timestamp": "2026-03-22T10:32:11.789012",
  "result": {"refunded": 1000, "status": "success"}
}
```

---

### Q16: SlotAgent 支持分布式部署吗？

**A:** **当前版本不直接支持**，但可通过外部组件实现。

**单机部署（当前）：**
- CoreScheduler 是无状态的（每次执行独立）
- ApprovalManager 使用内存存储（不跨进程共享）

**分布式方案（需要额外工作）：**

1. **工具执行分布式**：使用任务队列
```python
# 使用 Celery 分发工具执行
@app.task
def execute_tool_task(tool_id, params):
    scheduler = CoreScheduler()
    context = scheduler.execute(tool_id, params)
    return context.__dict__

# 调用
result = execute_tool_task.delay('my_tool', {'key': 'value'})
```

2. **审批状态共享**：使用 Redis
```python
class RedisApprovalManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    def create_approval(self, ...):
        approval_id = str(uuid.uuid4())
        self.redis.hset(f'approval:{approval_id}', mapping={...})
        return approval_id

    def approve(self, approval_id, approver):
        # 使用 Redis 事务保证原子性
        ...
```

**计划改进（v0.3.0）：**
- 提供 `RedisApprovalManager` 实现
- 支持分布式 Hook 事件（通过消息队列）

---

**文档版本：** 1.0
**维护者：** SlotAgent 核心团队

**未找到答案？**
- 查看 [API Reference](./api_reference.md)
- 查看 [User Guide](./user_guide.md)
- 提交 Issue: https://github.com/yimwu/slotagent/issues
