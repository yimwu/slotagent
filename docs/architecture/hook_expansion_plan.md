# Hook 细粒度事件扩展专项计划

**文档版本:** 1.0
**最后更新:** 2026-03-27
**状态:** Draft

---

## 1. 概述（Overview）

### 1.1 背景

当前 SlotAgent 仅提供 5 个核心 Hook 事件：`before_exec`、`after_exec`、`fail`、`guard_block`、`wait_approval`。这套模型能够覆盖粗粒度执行观测，但无法满足以下细粒度观测诉求：

- Schema 前后阶段可视化
- Guard 前置阶段可视化
- Healing 结果与重试启动可视化
- Reflect 完成后的结果观测
- 审批完成（批准 / 拒绝 / 超时）状态通知

本专项计划以“两批次推进”的方式补齐上述能力，同时保持 SlotAgent 既有原则：极小内核、插槽化插件、Hook 驱动可观测性、松耦合演进。

### 1.2 目标

1. 在**不破坏现有 5 个事件语义和订阅 API** 的前提下，新增细粒度 Hook 事件。
2. 将工作拆分为：
   - **第一批**：调度阶段细粒度事件
   - **第二批**：审批完成事件
3. 全程遵循项目既有 **SDD/TDD** 规范推进。
4. 在专项文档内维护里程碑追踪，并在 `PROJECT_PLAN.md` 中保留专项入口。

### 1.3 非目标

本专项**不包含**以下内容：

1. 不将 Hook 分发模型从同步改为异步。
2. 不新增外部消息平台、告警平台、前端通知等适配器。
3. 不在第二批内引入“审批通过后自动恢复执行”的 continuation / resume 机制。
4. 不额外补齐未明确提出的对称事件（如 `after_guard`、`before_healing`、`before_reflect`），避免事件数量无控制扩张。

---

## 2. 设计原理（Design Principles）

### 2.1 保持极小内核

新增能力应以“增加事件模型 + 增加 emit 点”为主，不把新的业务策略塞入 `CoreScheduler` 或 `ApprovalManager`。

### 2.2 向后兼容优先

已有事件类型、已有订阅接口、已有测试行为全部保持兼容。新增事件只能是**增量扩展**，不能改变旧事件触发时机与字段语义。

### 2.3 只扩展用户真正需要的事件

第一批仅覆盖当前明确提出的调度阶段事件；第二批审批事件统一收敛为一个 `approval_resolved` 事件，通过状态字段区分 approved / rejected / timeout，避免拆成三个新事件造成事件爆炸。

### 2.4 审批域与调度域分层

审批状态变化与工具调度继续解耦：

- `wait_approval` 属于调度链被 Guard 中断时的事件；
- `approval_resolved` 属于审批状态完成时的事件；
- 第二批只解决“审批结果可观测”，不把“审批通过后恢复执行”混入当前范围。

### 2.5 严格遵循 SDD/TDD

每一批次都按以下顺序推进：

1. **SDD**：先更新规格文档，冻结事件语义、字段、触发顺序。
2. **TDD Red**：先写失败测试，锁定行为边界。
3. **TDD Green**：实现最小代码使测试通过。
4. **TDD Blue**：重构、补文档、做回归验证。

---

## 3. 范围拆分（Scope & Batch Definition）

| 批次 | 目标 | 事件范围 | 核心约束 |
|------|------|---------|---------|
| 第一批 | 补齐调度阶段细粒度观测 | `before_schema`、`after_schema`、`before_guard`、`after_healing`、`after_reflect`、`retry_started` | 不改审批模型，不改变既有执行主流程 |
| 第二批 | 补齐审批完成状态通知 | `approval_resolved` | 只做状态通知，不做自动恢复执行 |

### 3.1 第一批边界

第一批仅处理 `CoreScheduler` 内部可直接插入的生命周期事件，属于**低风险、局部增强**：

- 事件源集中在 `src/slotagent/core/core_scheduler.py`
- 主要影响事件类型、Hook 注册表、订阅便利接口与测试
- 不要求新增新的执行状态枚举

### 3.2 第二批边界

第二批处理 `approval_resolved`，属于**跨组件边界增强**：

- 事件源来自审批状态从 `PENDING` 转为终态
- 涉及 `ApprovalManager` 与 Hook 系统的连接方式
- 需要明确“状态通知”和“恢复执行”是两个独立问题

---

## 4. 接口规格（Interface Specification）

### 4.1 新增事件类型

| 事件名 | 批次 | 触发时机 | 建议关键字段 | 说明 |
|------|------|---------|-------------|------|
| `before_schema` | 第一批 | Schema 插件执行前 | `execution_id`、`tool_id`、`tool_name`、`params` | 仅在存在 Schema 插件时触发 |
| `after_schema` | 第一批 | Schema 插件返回后 | `execution_id`、`tool_id`、`params`、`success`、`should_continue`、`schema_plugin_id`、`error` | 无论校验是否通过都应触发一次 |
| `before_guard` | 第一批 | Guard 插件执行前 | `execution_id`、`tool_id`、`tool_name`、`params` | 仅在存在 Guard 插件时触发 |
| `after_healing` | 第一批 | Healing 插件执行后 | `execution_id`、`tool_id`、`attempt`、`max_attempts`、`recovered`、`fixed_params_applied`、`healing_plugin_id` | 仅在工具执行失败且实际进入 Healing 时触发 |
| `after_reflect` | 第一批 | Reflect 插件执行后 | `execution_id`、`tool_id`、`reflect_plugin_id`、`success`、`should_continue`、`error` | 仅在存在 Reflect 插件时触发 |
| `retry_started` | 第一批 | Healing 判定可恢复、准备进入下一次工具执行前 | `execution_id`、`tool_id`、`attempt`、`next_attempt`、`max_attempts`、`reason` | 用于观测“将要重试”的瞬间 |
| `approval_resolved` | 第二批 | 审批状态从 `PENDING` 进入终态时 | `approval_id`、`execution_id`、`tool_id`、`resolution`、`approver`、`reason`、`resolved_at` | `resolution` 取值：`approved` / `rejected` / `timeout` |

### 4.2 对外订阅接口增量

`SlotAgent` 对外增加以下便利订阅方法：

- `on_before_schema(handler)`
- `on_after_schema(handler)`
- `on_before_guard(handler)`
- `on_after_healing(handler)`
- `on_after_reflect(handler)`
- `on_retry_started(handler)`
- `on_approval_resolved(handler)`

**兼容性要求：**

1. 现有 `on_before_exec()`、`on_after_exec()`、`on_fail()`、`on_guard_block()`、`on_wait_approval()` 保持不变。
2. `HookManager.VALID_EVENT_TYPES` 仅做增量扩展，不重命名旧事件。
3. 旧订阅者无需改代码即可继续工作。

### 4.3 预计影响文件

#### 第一批

- `src/slotagent/types.py`
- `src/slotagent/core/hook_manager.py`
- `src/slotagent/core/core_scheduler.py`
- `src/slotagent/agent.py`
- `tests/unit/test_hook_manager.py`
- `tests/unit/test_core_scheduler.py`
- `tests/unit/test_agent.py`
- `tests/integration/test_complete_workflow.py`

#### 第二批

- `src/slotagent/types.py`
- `src/slotagent/core/approval_manager.py`
- `src/slotagent/agent.py`
- `src/slotagent/core/hook_manager.py`
- `tests/unit/test_approval_manager.py`
- `tests/unit/test_agent.py`
- `tests/integration/test_complete_workflow.py`

---

## 5. 流程与状态（Workflow & State Machines）

### 5.1 第一批目标流程

```text
before_schema
  -> schema execute
  -> after_schema
      -> before_guard
          -> guard execute
              -> wait_approval / guard_block / before_exec
                  -> tool execute success
                      -> after_exec
                      -> reflect execute
                      -> after_reflect
                      -> observe
                      -> completed
                  -> tool execute fail
                      -> fail
                      -> healing execute
                      -> after_healing
                          -> recovered = true
                              -> retry_started
                              -> retry tool execute
                          -> recovered = false
                              -> failed
```

### 5.2 第一批触发规则

1. **`before_schema` / `after_schema`**：仅当 Schema 插件真实执行时触发。
2. **`before_guard`**：仅当 Guard 插件真实执行时触发。
3. **`after_healing`**：仅当工具执行失败且 Healing 插件被调用时触发。
4. **`retry_started`**：仅当 Healing 明确给出“可恢复并继续下一次尝试”时触发。
5. **`after_reflect`**：仅当 Reflect 插件真实执行时触发。

### 5.3 第二批目标流程

```text
wait_approval
  -> approval pending
      -> approve()      -> approval_resolved(resolution=approved)
      -> reject()       -> approval_resolved(resolution=rejected)
      -> check_timeouts -> approval_resolved(resolution=timeout)
```

### 5.4 第二批状态约束

1. `approval_resolved` 只对应审批状态机终态迁移，不等价于“工具继续执行”。
2. 第二批不新增 `PENDING_APPROVAL -> RUNNING` 的恢复执行链路。
3. 同一个 `approval_id` 只能产生一次 `approval_resolved` 终态事件。

---

## 6. 第一批工作计划（调度阶段细粒度 Hook）

### 6.1 交付目标

交付调度阶段 6 个新事件，并保证既有 5 个事件行为不回归。

### 6.2 分阶段任务

| 阶段 | 类型 | 任务 | 产出 |
|------|------|------|------|
| B1-S1 | SDD | 明确 6 个事件的字段、触发顺序、兼容边界 | 本专项文档定稿 + 相关规格文档更新清单 |
| B1-S2 | TDD Red | 先补失败测试：事件注册、触发顺序、失败分支、重试分支 | 新增/更新单元测试与集成测试 |
| B1-S3 | TDD Green | 最小实现：事件类型、HookManager、Scheduler emit 点、Agent 订阅包装 | 可通过测试的代码实现 |
| B1-S4 | TDD Blue | 重构命名、减少重复、补 API 文档与用户指南 | 代码清理 + 文档同步 |

### 6.3 第一批测试清单

#### 单元测试

1. `test_hook_manager.py`
   - 新事件可以成功订阅 / 取消订阅 / 计数
   - 非法事件类型仍被拒绝

2. `test_core_scheduler.py`
   - 有 Schema 插件时触发 `before_schema` → `after_schema`
   - Schema 失败时仍触发 `after_schema`，随后触发 `fail`
   - 有 Guard 插件时触发 `before_guard`
   - Healing 成功恢复时触发 `after_healing` 与 `retry_started`
   - Reflect 执行后触发 `after_reflect`

3. `test_agent.py`
   - 新增便利订阅接口都能注册到正确的 event_type

#### 集成测试

1. 完整成功流程包含：`before_schema`、`after_schema`、`before_guard`、`before_exec`、`after_exec`、`after_reflect`
2. 重试流程包含：`fail`、`after_healing`、`retry_started`
3. Guard 审批 / 拦截分支不被第一批改坏

### 6.4 第一批验收标准

- [ ] 6 个新事件均有明确数据模型
- [ ] 6 个新事件均进入 `HookManager.VALID_EVENT_TYPES`
- [ ] `SlotAgent` 暴露对应订阅便利方法
- [ ] 既有 5 个事件触发顺序不回归
- [ ] Healing 恢复场景下 `after_healing` 与 `retry_started` 顺序稳定
- [ ] 单元测试与集成测试全部通过

---

## 7. 第二批工作计划（审批完成 Hook）

### 7.1 交付目标

交付统一的 `approval_resolved` 事件，覆盖：

- 批准（approved）
- 拒绝（rejected）
- 超时（timeout）

### 7.2 关键设计决策

1. **单事件 + 状态字段**
   - 不拆成 `approval_approved` / `approval_rejected` / `approval_timeout`
   - 用 `resolution` 字段统一表达审批结果

2. **状态通知与恢复执行分离**
   - 第二批只交付审批结果通知
   - 若未来要支持 approve 后恢复执行，应另立专题规格，不与本批混做

3. **避免 ApprovalManager 直接绑定业务处理器**
   - 需要设计“审批状态变化 -> Hook 事件”的桥接方案
   - 目标是保持审批管理和事件分发的职责边界清晰

### 7.3 分阶段任务

| 阶段 | 类型 | 任务 | 产出 |
|------|------|------|------|
| B2-S1 | SDD | 冻结 `approval_resolved` 字段、触发语义、一次性约束 | 审批事件规格定稿 |
| B2-S2 | TDD Red | 先补失败测试：approve/reject/timeout 三类终态均触发事件 | 单元测试与集成测试 |
| B2-S3 | TDD Green | 实现审批状态变化与 Hook 的桥接 | 可通过测试的代码实现 |
| B2-S4 | TDD Blue | 清理边界逻辑、补审批文档、验证不引入自动恢复执行 | 文档同步 + 回归验证 |

### 7.4 第二批测试清单

#### 单元测试

1. `test_approval_manager.py`
   - approve 后触发一次 `approval_resolved(approved)`
   - reject 后触发一次 `approval_resolved(rejected)`
   - timeout 后触发一次 `approval_resolved(timeout)`
   - 非法状态迁移不重复触发事件

2. `test_agent.py`
   - `on_approval_resolved()` 正确注册订阅者

#### 集成测试

1. `wait_approval -> approve -> approval_resolved`
2. `wait_approval -> reject -> approval_resolved`
3. `wait_approval -> timeout -> approval_resolved`
4. 上述流程均不自动进入 `before_exec` / `after_exec`

### 7.5 第二批验收标准

- [ ] `approval_resolved` 覆盖 approved / rejected / timeout
- [ ] 事件字段包含 `approval_id` 与 `execution_id`
- [ ] 同一审批记录只会发出一次终态事件
- [ ] 不引入审批通过后的自动恢复执行副作用
- [ ] 审批管理现有状态转移测试保持通过

---

## 8. 非功能要求（Non-Functional Requirements）

### 8.1 兼容性

1. 旧事件名称、旧订阅方式、旧测试行为必须保持兼容。
2. 未订阅新事件时，不应影响现有业务逻辑。

### 8.2 性能

1. 新增事件仅允许引入常量级额外判断与对象创建。
2. 不允许为了新增 Hook 引入网络 I/O 或持久化 I/O。

### 8.3 可靠性

1. 订阅者异常继续隔离，不影响主流程。
2. `approval_resolved` 不得重复发送。
3. `retry_started` 的 attempt 编号必须可预测、可测试。

### 8.4 可追踪性

1. 所有新事件必须携带 `execution_id`。
2. 审批相关事件必须同时携带 `approval_id`。
3. 事件顺序应可被测试稳定断言。

---

## 9. 里程碑与登记规则（Milestones & Registration）

### 9.1 专项里程碑表

| 里程碑 | 批次 | 完成标志 | 状态 | 实际完成日期 | Commit / PR |
|-------|------|---------|------|-------------|------------|
| HX-M1 | 第一批 | 6 个调度阶段事件交付完成，测试通过，文档同步 | ✅ | 2026-03-28 | 8065e41 |
| HX-M2 | 第二批 | `approval_resolved` 交付完成，测试通过，文档同步 | ✅ | 2026-03-28 | 17f3a4f |

### 9.2 登记位置

达到里程碑后，按以下位置同步登记：

1. **本专项文档**：更新 9.1 表格状态、完成日期、Commit / PR。
2. **`PROJECT_PLAN.md`**：保留专项入口链接，不在主 Phase 表中重复展开专项细节。
3. **相关规格文档**：同步更新 `docs/architecture/hook_system.md`、`docs/data_models/hook_events.md` 等正式规格。
4. **变更历史**：在本文件 Changelog 中记录里程碑完成情况。

### 9.3 登记规则

达到里程碑时，执行以下检查：

1. 关键任务全部完成；
2. 验收标准全部满足；
3. 相关规格文档已同步；
4. 测试通过且无既有行为回归；
5. 记录对应 commit hash 与 PR 链接。

---

## 10. 风险与缓解（Risks）

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 事件数量继续膨胀 | 维护成本升高 | 只交付本次明确需求，不补对称事件 |
| `approval_resolved` 与恢复执行边界混淆 | 设计失控 | 第二批文档明确“只通知，不恢复” |
| Hook 顺序不稳定 | 测试脆弱、外部订阅者难依赖 | 在 TDD 中显式断言顺序 |
| 旧事件回归 | 破坏现有用户 | 对既有 5 事件保留回归测试 |

---

## 11. 变更历史（Changelog）

- **2026-03-27 / v1.0**：创建 Hook 细粒度事件扩展专项计划，定义两批次范围、接口增量、TDD 路线与里程碑登记规则。
- **2026-03-28 / v1.1**：HX-M1 完成，交付 6 个调度阶段细粒度事件（commit 8065e41）。HX-M2 完成，交付 approval_resolved 事件（commit 17f3a4f）。专项全部里程碑达成。
