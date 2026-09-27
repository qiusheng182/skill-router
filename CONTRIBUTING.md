# Contributing

感谢你愿意改这个项目。

## 优先贡献方向

- 更稳定的 Skill 路由评分
- 更低 token 的 context pack
- 更完整的跨 provider 同步测试
- 更安全的 candidate 应用策略
- 更真实的 practice suite
- 文档中的错误、歧义和过时说明

## 提交前检查

```powershell
python -B -m py_compile .\scripts\*.py
python .\tests\test_admin_tools.py
python C:\Users\<you>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

如果修改了扫描、同步或上下文预算逻辑，请同时运行：

```powershell
python .\scripts\sync_skill.py `
  --skill-name skill-router `
  --source . `
  --providers codex,opencode,claude `
  --check
```

## 设计约束

- 默认不扩大权限
- 不自动执行未验证的外部内容
- 高风险更新必须可回滚
- 不把未验证博客当作权威来源
- 新增说明要解释“为什么”，而不只是“做什么”

## Pull Request 内容

请描述：

- 解决的问题
- 修改了哪些行为
- 如何验证
- token 或性能影响
- 回滚方式

## 不要提交

- 凭据、token、cookie 或私钥
- 本地缓存、`__pycache__`
- 个人环境路径和私有数据
