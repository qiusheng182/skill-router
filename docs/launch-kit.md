# Launch Kit

This kit is for sharing `skill-router` with AI agent builders, tool makers, and
developers who are already feeling the cost of loading too many skills.

The goal is not to sound loud. The goal is to make one concrete problem obvious:

> Your agent should not carry every skill into every prompt.

## Positioning

### One-liner

`skill-router` is a context-budget manager and skill administrator for AI agents.

### Short pitch

Most agent systems keep every installed skill description in context. As the
skill library grows, routing gets noisier and every request pays the metadata
cost again. `skill-router` keeps one routing entry visible, scans only the
active provider, compiles task-scoped context packs, and turns repeated work
into tested improvements instead of uncontrolled self-modification.

### Proof points

- Clarify before scanning or invoking a skill.
- Keep one router visible instead of every skill description.
- Support Claude, OpenCode, Codex, Cursor, Gemini, and Windsurf roots.
- Build query-scoped context packs with omitted-section indexes and token
  estimates.
- Record task experience, run practice suites, compare versions, snapshot
  before apply, and synchronize across providers.
- Default to a conservative `propose` policy for skill changes.

## GitHub Release Copy

### Release title

`v0.1.0: Context budget, context compiler, and evidence-driven skill evolution`

### Release notes

The first public release of `skill-router`.

What is included:

- provider-aware skill discovery across six providers
- focused scan and confidence-based routing workflow
- `context_budget.py` for moving non-router skills out of always-loaded context
- `token_budget.py` for profiles, restore, apply, and history
- `skill_context.py` for query-scoped context packs
- `experience_store.py` and `practice_runner.py` for evidence-driven learning
- `validate_candidate.py`, `apply_candidate.py`, and `sync_skill.py` for
  controlled skill updates
- regression tests for the administrator tools

Why it exists:

Agent skills are becoming cheap to add and expensive to carry. This project
treats skill selection, context loading, and skill evolution as one engineering
workflow: clarify, route, compile, record, test, and apply only what is
verified.

If this problem is familiar, give the repository a star so more agent builders
can find it.

## Hacker News

### Title

`Show HN: Skill Router - keep agent skills out of every prompt`

### Body

I kept adding skills to my agent setup and eventually noticed that most of the
context cost was not the task. It was the metadata, descriptions, references,
and instructions for skills that were not relevant to the current request.

`skill-router` is my attempt to treat that as a routing and context-budget
problem.

The workflow is:

1. If the task is unclear, ask before scanning.
2. If it is clear, scan only the active provider for relevant skills.
3. If a skill is selected, compile a query-scoped context pack instead of
   loading the whole skill folder.
4. Record real outcomes so repeated work can become tested skill improvements.

It currently supports Claude, OpenCode, Codex, Cursor, Gemini, Windsurf, and
custom provider roots. The most useful piece is probably `skill_context.py`,
which reports token estimates, relevant sections, and line numbers for omitted
sections.

Repository: https://github.com/qiusheng182/skill-router

Feedback I would especially value:

- Is keeping only one router visible the right default?
- What should a context pack always include for safety?
- How should provider-specific skill copies be synchronized without drift?

## Reddit

Use this only in communities where project posts are welcome. Read each
subreddit's rules first and answer technical questions rather than dropping the
link and leaving.

### r/LocalLLaMA style

Title: `I built a skill router to stop every request from carrying every skill description`

Body:

As the number of agent skills grows, the always-loaded metadata becomes a
tax on every request. I built `skill-router` to keep one routing entry visible,
scan only the active provider, and compile a task-scoped context pack before
loading a skill's full documentation.

It also records experience, runs practice suites, and only applies skill
updates after validation and snapshotting. The idea is not to let the agent
freely rewrite itself; it is to make skill evolution testable and reversible.

Repo: https://github.com/qiusheng182/skill-router

Curious whether others here are hitting the same skill-metadata cost or if this
is mostly an issue in tool-heavy coding agents.

### r/ClaudeAI or r/ChatGPTCoding style

Title: `A skill router that keeps only one skill entry visible and loads context on demand`

Body:

Once a Claude/Codex/Cursor-style setup has many skills, every request can carry
descriptions of tools that are irrelevant to the task. `skill-router` adds a
clarification gate, a focused scan, and a context compiler that turns a target
skill into a task-scoped pack.

I published it as an open-source skill and included scripts for context budgets,
experience records, practice suites, validation, snapshots, and provider sync.

Repo: https://github.com/qiusheng182/skill-router

If you use a large skill library, I would like to know what your current
workflow does when the task is ambiguous.

## X / Twitter Thread

1. Agents are getting more skills.

That is good for capability, but bad for context if every skill description is
loaded on every request.

I built `skill-router` to make skill loading on-demand:
https://github.com/qiusheng182/skill-router

2. The workflow has three gates:

- clarify the task first
- scan only relevant skills
- load only the context the task needs

No tool call should start just because a trigger word appeared.

3. The most useful piece is the context compiler.

`skill_context.py` builds a query-scoped pack with relevant sections, safety
and workflow sections, token estimates, and line numbers for omitted material.

4. It also treats skill evolution like software:

experience episode -> candidate update -> practice suite -> before/after
comparison -> validation -> snapshot -> apply -> sync

No uncontrolled self-rewrites.

5. It supports Claude, OpenCode, Codex, Cursor, Gemini, and Windsurf.

If your agent is carrying a library for every request, star the repo so more
builders can find it:
https://github.com/qiusheng182/skill-router

## LinkedIn

AI agents are becoming more capable by accumulating skills. They are also
becoming more expensive to operate when every request carries metadata for
skills that are not relevant.

`skill-router` is an open-source experiment in fixing that structure. It keeps
one routing entry visible, scans only the active provider, compiles context on
demand, and uses evidence from real tasks to improve skills through practice
and validation rather than uncontrolled self-modification.

Repository: https://github.com/qiusheng182/skill-router

The part I am most interested in discussing: when should an agent ask for
clarification before it scans tools, and when should it simply act?

## Chinese Platforms

### V2EX 分享创造

标题：`我写了一个 Skill Router，让 Agent 不要每次都背着一整库 Skill 描述`

正文：

当 Claude / Codex / Cursor 这类工具的 Skill 越装越多，真正被用到的可能
只有一个，但每次请求都可能携带大量无关的 description、references 和
说明文档。

`skill-router` 把这件事拆成三道门：

1. 任务不清楚，先问人，不扫描 Skill。
2. 任务清楚后，只扫描当前 provider 里相关的 Skill。
3. 选中 Skill 后，只为当前任务编译 context pack，而不是加载整个 Skill。

它还把经验记录、practice suite、版本对比、快照和同步放在同一条可验证的
流程里，默认不自动应用高风险更新。

项目地址：https://github.com/qiusheng182/skill-router

如果对你有帮助，求一个 star，也欢迎直接提 issue 讨论跨 provider 同步和
context pack 的设计。

### 掘金 / 知乎 / 公众号

标题：`当 AI 装了 100 个 Skill，真正的问题不是记得更多，而是每次都带得太多`

开头：

AI Agent 正在像手机一样安装越来越多的能力。写文档、读 PDF、处理表格、
做视频、安全审计，每一种能力都值得拥有。问题是，模型的每一次请求并不
需要认识所有专家。

`skill-router` 想做的是一个更基础的动作：先判断任务，再决定加载什么。

正文结构：

1. 为什么 Skill 越多，路由越不稳定。
2. 为什么“先澄清再扫描”比“关键词触发”更可靠。
3. 如何用 `context_budget.py` 把非路由 Skill 移出常驻上下文。
4. 如何用 `skill_context.py` 只为当前任务编译上下文。
5. 如何让 Skill 的进化留下证据、练习、快照和回滚路径。

结尾：

项目地址：https://github.com/qiusheng182/skill-router

如果它帮你少背了一点无关上下文，欢迎点一个 star。

## Launch Sequence

### Day 0: Prepare the repository

- Set a clear GitHub description and topics.
- Make the README show the problem, the outcome, and a quick start in the first
  screen.
- Publish a release with stable install instructions.
- Add a social preview image in GitHub repository settings.
- Pin the repository on the owner profile while sharing it.

### Day 1: Technical launch

- Post Show HN in the morning, US Pacific time.
- Post one tailored Reddit thread, then participate in comments for at least
  two hours.
- Post the X/Twitter thread with the repository link in the first post.
- Share a short Chinese version on V2EX.

### Day 2 to Day 7: Follow-up distribution

- Write one deep article about the context compiler.
- Write one practical article about reducing always-loaded skill descriptions.
- Open targeted PRs to `awesome-*` lists only where the list accepts tooling
  submissions.
- Answer related questions in agent-builder communities with real examples,
  not repeated link drops.
- Collect the best questions and add them to the README FAQ.

## Metrics To Watch

- stars in the first 24 hours and first 7 days
- GitHub referrers: Hacker News, Reddit, X, LinkedIn, search
- repository views and unique visitors from GitHub traffic
- clone count from GitHub traffic
- issues and discussions that ask real design questions

The most important signal is not raw star count. It is whether the right people
understand the problem and start a technical conversation about routing,
context, and skill evolution.
