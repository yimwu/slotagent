# 贡献指南 (Contributing Guide)

感谢你对 SlotAgent 项目的关注! 我们欢迎所有形式的贡献,包括但不限于:

- 🐛 Bug 报告和修复
- ✨ 新功能建议和实现
- 📖 文档改进
- 🧪 测试用例补充
- 💡 设计讨论和改进建议

## 📋 行为准则 (Code of Conduct)

请保持尊重和专业的态度与其他贡献者交流。我们致力于营造友好、包容的开源社区氛围。

## 🚀 开始贡献

### 1. Fork 和 Clone

```bash
# Fork 仓库到你的账号
# 然后 clone 到本地
git clone https://github.com/YOUR_USERNAME/slotagent.git
cd slotagent

# 添加上游仓库
git remote add upstream https://github.com/yimwu/slotagent.git
```

### 2. 创建功能分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-number-description
```

### 3. 设置开发环境

```bash
# 安装开发依赖
pip install -e .
pip install -r requirements-dev.txt

# 验证环境
pytest tests/
```

## 📐 开发规范

### SDD (Specification-Driven Development)

**所有功能开发必须先编写规格文档!**

1. **规格文档位置**: `docs/` 对应子目录
2. **规格内容**: 参考 [DEVELOPMENT_RULES.md](DEVELOPMENT_RULES.md) 第1节
3. **评审流程**: 提交 PR 或 Issue,邀请核心贡献者评审

### TDD (Test-Driven Development)

**所有功能开发必须遵循 TDD 流程!**

1. **Red**: 根据规格编写失败的测试
2. **Green**: 编写最小化代码使测试通过
3. **Blue**: 重构和优化

**测试覆盖率要求:**
- 核心模块 (core/): ≥ 95%
- 插件模块: ≥ 80%
- 整体: ≥ 85%

### 代码规范

遵循 [DEVELOPMENT_RULES.md](DEVELOPMENT_RULES.md) 第3节:

- **命名**: PascalCase(类), snake_case(函数/变量), UPPER_SNAKE_CASE(常量)
- **类型注解**: 所有公共接口必须包含类型注解
- **文档字符串**: Google风格,包含 Args/Returns/Raises/Examples
- **格式化**: 使用 black (line-length=100)

**提交前检查:**

```bash
# 格式化
black src/slotagent tests/

# Lint
flake8 src/slotagent tests/

# 测试和覆盖率
pytest --cov=src/slotagent tests/
```

### Commit 规范

遵循 Angular Commit Message Format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type 类型:**
- `feat`: 新功能
- `fix`: Bug修复
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `docs`: 文档更新
- `chore`: 构建、依赖等

**示例:**

```
feat(plugin_pool): implement plugin priority resolution

添加插件优先级机制,工具级插件配置优先于全局插件。
实现了 PluginPool.select_plugin() 方法。

Closes #123
```

## 🔄 提交 Pull Request

### PR 标题格式

```
[module] Brief description
```

示例: `[core] implement plugin chain execution`

### PR 描述模板

```markdown
## 关联 Issue
Closes #<issue_number>

## 规格文档
链接到对应的规格文档(如果适用)

## 实现概述
- 简要描述实现方案
- 关键设计决策
- 与其他模块的交互

## 测试覆盖
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试(如适用)
- [ ] 所有测试通过

## 检查清单
- [ ] 代码遵循 DEVELOPMENT_RULES.md 规范
- [ ] 新增/修改了对应的规格文档
- [ ] 编写了单元测试
- [ ] 通过了所有本地测试和 lint 检查
- [ ] commit 信息符合规范
- [ ] 更新了相关文档
```

### 审查流程

1. 提交 PR 后,CI/CD 会自动运行测试和检查
2. 至少需要 1 名核心审查者的 Approve
3. 所有 CI 检查必须通过
4. 审查通过后,会 Squash 并合并到主分支

## 🐛 报告 Bug

使用 [GitHub Issues](https://github.com/yimwu/slotagent/issues) 报告 Bug,请包含:

1. **环境信息**: Python版本、操作系统
2. **复现步骤**: 详细的步骤说明
3. **预期行为**: 你期望发生什么
4. **实际行为**: 实际发生了什么
5. **错误日志**: 完整的错误堆栈
6. **最小复现示例**: 可运行的代码片段

## 💡 功能建议

使用 [GitHub Discussions](https://github.com/yimwu/slotagent/discussions) 讨论新功能:

1. **使用场景**: 为什么需要这个功能
2. **设计建议**: 你的实现思路
3. **替代方案**: 是否有其他解决方案
4. **影响范围**: 对现有功能的影响

## 📚 文档贡献

文档改进也是重要的贡献!

- **架构文档**: `docs/architecture/`
- **接口文档**: `docs/interfaces/`
- **流程文档**: `docs/workflows/`
- **示例代码**: `examples/`

## 🎯 开发路线图

查看 [PROJECT_PLAN.md](PROJECT_PLAN.md) 了解当前开发阶段和计划。

如果你想参与某个 Phase 的开发,可以:

1. 查看对应 Phase 的任务列表
2. 在 GitHub Issues 中认领任务
3. 按照 SDD/TDD 流程开发
4. 提交 PR

## ❓ 获取帮助

- **技术问题**: [GitHub Discussions - Q&A](https://github.com/yimwu/slotagent/discussions/categories/q-a)
- **设计讨论**: [GitHub Discussions - Ideas](https://github.com/yimwu/slotagent/discussions/categories/ideas)
- **Bug 反馈**: [GitHub Issues](https://github.com/yimwu/slotagent/issues)

## 🙏 致谢

感谢你的贡献! 每一个 PR、Issue、讨论都对项目至关重要。

---

**Happy Coding! 🎉**
