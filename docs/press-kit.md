# 发布资料包

## 一句话介绍

`skill-router` 是一个面向 AI Agent 的 Skill 管理员：先澄清任务，再最小化路由，按需加载上下文，并让 Skill 通过经验、练习和版本对比受控进化。

## 100 字摘要

当 AI 安装了越来越多 Skill，每个请求都会携带大量无关描述。`skill-router` 把 Skill 使用拆成澄清、路由、上下文预算、按需编译和经验进化五层。它只保留一个常驻入口，让其他 Skill 退出每轮上下文，并在真实任务后记录经验、运行练习、比较版本，验证通过才升级。

## 300 字新闻稿

AI Agent 的能力正在增长，但上下文成本也在同步增长。大量 Skill 的 description、references 和说明文档会在每次请求中重复进入模型上下文，造成 token 浪费和路由噪声。

开源项目 `skill-router` 试图解决这个问题。它不是再增加一个业务 Skill，而是充当 Skill 生态的路由器和管理员。任务不清楚时，它先向用户提问；任务清楚后，它只扫描当前 provider 中相关的 Skill，并在不确定时列出候选项。

项目最特别的地方是两级上下文控制。第一级通过 `context_budget.py` 让非路由 Skill 退出常驻上下文，只保留 `skill-router` 作为入口。第二级通过 `skill_context.py` 为目标 Skill 生成 query-scoped context pack，只加载当前任务需要的章节，其余文档保留行号和 token 索引。

它还把“自我进化”做成可验证流程：`experience_store.py` 记录每次任务的经验、失败、修正和指标；`practice_runner.py` 运行固定练习集并比较升级前后的通过率、耗时和 token；只有通过验证的候选更新才会被应用和同步，并保留快照与回滚路径。

## 亮点清单

- 任务澄清优先于 Skill 调用
- 只保留一个常驻 Skill 入口
- 跨 Claude、OpenCode、Codex、Cursor、Gemini、Windsurf
- 扫描默认只返回最小信息
- 支持 query-scoped context pack
- 支持 experience episode 和能力画像
- 支持 practice suite 和版本对比
- 默认 `propose`，高风险更新不自动应用
- 应用前快照，同步前备份
- 三端同步并保留验证证据

## 建议标题

1. 当 Skill 学会节省上下文
2. 不只是 Skill 路由器：一个会练习、会复盘、会进化的 AI 管理员
3. AI Agent 的下一场效率战，可能从“少加载一点”开始
4. 从 9.6k token 到一次提问：Skill Router 如何重构 AI 工作流
5. 不让所有专家都站在会议室里

## 社交媒体短文

### 版本 A

AI Agent 不缺 Skill，缺的是一个知道“什么时候该用什么”的管理员。

`skill-router` 先澄清任务，再最小化路由；平时只保留一个入口，使用时才生成 query-scoped context pack。真实任务还能沉淀成 episode、scorecard、practice suite，让 Skill 通过证据进化，而不是盲目自改。

### 版本 B

很多 AI 工作流的隐藏成本，不是回答太慢，而是每次请求都带着几十个无关 Skill 的描述。

`skill-router` 的思路很简单：先问清楚，再只加载需要的。它把上下文预算、按需编译、经验记录和版本验证放在同一个管理员里。

### 版本 C

Skill 也可以像运动员一样练习。

记录体验、形成能力画像、跑固定练习集、比较升级前后的通过率和 token。只有验证通过的更新才进入正式版本，并保留快照和回滚。

## 关键数字

- 20 个发布文件
- 约 3,000 行代码与文档
- 支持 6 类 provider
- 8 项回归测试
- Codex 环境估算每轮减少约 9.6k token

## 适合追问的问题

- 为什么不直接删除不用的 Skill？
- 上下文编译会不会漏掉关键安全说明？
- 如何防止 Skill 自动改坏自己？
- 经验记录如何避免保存敏感信息？
- 多 provider 同步冲突怎么处理？
- 什么情况下应该把 Skill 重新设为自动调用？
