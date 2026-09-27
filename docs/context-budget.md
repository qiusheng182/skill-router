# 上下文预算说明

## 问题

大多数 Skill 系统会把每个 Skill 的 `name` 和 `description` 带入每一次请求。

当 Skill 数量增长后，常驻上下文会出现三个问题：

- 成本持续增加
- 路由信噪比下降
- 无关描述干扰当前任务

## 两个工具

### context_budget.py

`context_budget.py` 用于调整 Skill 是否允许模型自动调用。

默认保留：

```text
skill-router
```

其余 Skill 会加入：

```yaml
disable-model-invocation: true
```

这会使其 description 退出模型自动可见范围，但文件本身仍然存在，仍可由用户显式调用，或由路由流程按路径读取。

### token_budget.py

`token_budget.py` 提供 profile 式管理：

- `report`：统计当前启用的 Skill、description 字符数和估算 token
- `apply`：创建 profile、备份并应用预算策略
- `restore`：按 profile 恢复
- `list-profiles`：查看历史 profile

## 典型流程

```powershell
python .\scripts\token_budget.py report --providers codex

python .\scripts\token_budget.py apply `
  --providers codex `
  --keep skill-router

python .\scripts\token_budget.py apply `
  --providers codex `
  --keep skill-router `
  --apply
```

恢复：

```powershell
python .\scripts\token_budget.py list-profiles
python .\scripts\token_budget.py restore --profile <profile-id> --apply
```

## 为什么不是直接删除 Skill

删除会丢失能力。

把 Skill 变为 user-invoked 不是删除，而是改变加载时机：

```text
之前：每个请求都加载所有 Skill 描述
现在：每轮只加载路由入口，使用时再读取
```

## 与 Context Compiler 的关系

`context_budget.py` 解决“哪些 Skill 的 description 常驻”。

`skill_context.py` 解决“选中 Skill 后，到底加载哪些章节”。

两者叠加后，上下文成本被拆成两级：

1. 路由级预算
2. 文档级预算

## 数字如何理解

估算使用字符数除以 4：

```text
approximate_tokens = characters / 4
```

它不是计费接口的精确值，但适合做版本之间和 Skill 之间的相对比较。

## 风险与回滚

修改 frontmatter 前会备份。恢复 profile 后，Skill 会回到应用前的可调用状态。

如果 Skill 需要重新自动触发，可以把它加入 `--keep` 列表：

```powershell
python .\scripts\context_budget.py `
  --provider codex `
  --keep skill-router,pdf,docx `
  --apply
```
