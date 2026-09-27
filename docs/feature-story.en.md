# When Skills Learn to Save Context: The Story of an AI Administrator

> If every AI skill is an expert, the old approach puts every expert in the meeting room. `skill-router` keeps only a receptionist at the door.

## 1. The Problem Starts With Too Many Skills

AI agents are becoming as feature-rich as app stores.

There is a skill for documents, a skill for PDFs, a skill for spreadsheets, a skill for video engineering. Each capability is worth having. Each one also arrives with descriptions, instructions, references, and operational rules.

The model does not need every expert for every request.

When a user asks a simple question, the context may still carry dozens of unrelated skill descriptions. When the user explicitly asks for PDF work, the model may still read several unrelated automation descriptions first.

This is not a flaw in any single skill. It is a structural problem that appears when an AI skill ecosystem becomes mature.

That is where `skill-router` begins:

**Decide the task first. Decide the skills second.**

## 2. Not a Classifier, but a Gate

Many tools describe themselves as skill recommenders.

`skill-router` behaves more like a gate.

When a task arrives, it checks whether the task is clear enough to execute. If the deliverable, input, output, target environment, or acceptance condition is missing, it does not scan skills. It asks questions first.

That simple step changes everything downstream:

- the wrong skill is less likely to be selected for an unclear task
- a misunderstanding is caught before a tool call
- decisions that belong to the user are not silently made by the model

Once the task is clear, the gate opens.

Provider detection comes next, followed by a focused scan, candidate ranking, and a confidence check. When confidence is high, the router proceeds. When it is not, it presents 2 to 5 options and returns the decision to the user.

This is not about automating every decision. It is about giving certainty to the system and disagreement to the human.

## 3. The Standout Idea Is the Context Budget

Routing is only the first layer.

The second problem is subtler. Even when one skill is selected, it can bring a large set of references into the context.

`context_budget.py` addresses the cost of carrying unrelated skill descriptions on every request.

It marks non-router skills as user-invoked so their descriptions leave the always-loaded context. The router can still find them and read the right files when needed.

In the local Codex configuration, this strategy is estimated to reduce about `9.6k` context tokens per request.

The point is not to delete documentation. The point is to change when documentation enters the conversation.

## 4. Context Compiler: Documentation That Opens by Question

Saving tokens does not require losing capability.

`skill_context.py` acts as a context compiler. It builds a query-scoped pack:

- sections relevant to the current task
- important safety and workflow sections
- a reference index
- line numbers for omitted sections
- token estimates

It works like a reporter preparing a briefing pack before entering the field: carry the most relevant material first, then return to the archive only when necessary.

For large skills such as video-platform engineering, paper writing, or API security, loading the entire documentation set at the start is expensive. The context pack separates "begin the work" from "read everything."

## 5. Experience That Can Be Verified

Many systems claim to evolve.

But real evolution cannot be a model rewriting a prompt and hoping for the best.

`skill-router` takes a more disciplined path:

1. Record experience from a real task.
2. Mark failures, corrections, and evidence.
3. Build a skill scorecard.
4. Turn repeated patterns into a candidate update.
5. Run a practice suite.
6. Compare pass rate, duration, and output tokens before and after.
7. Validate.
8. Apply and synchronize with snapshots and rollback.

`experience_store.py` keeps the episodes.

`practice_runner.py` runs the practice and compares versions.

In other words, growth is not "I changed myself." It is "I experienced these tasks, left this evidence, passed these tests, and then changed."

## 6. A Unified Administrator Across Model Providers

Different tools keep skills in different directories:

- Claude
- OpenCode
- Codex
- Cursor
- Gemini
- Windsurf
- custom providers

`skill-router` does not assume that all skills live in one place. It discovers, scans, validates, and synchronizes across provider roots.

The result is a shared source of truth instead of separate copies that drift apart.

## 7. What Makes It Special

At a feature level, it looks like a collection of tools:

- scanning
- routing
- budgeting
- compiling
- recording
- practicing
- validating
- synchronizing

What makes it different is the order:

**Clarify before routing. Scan minimally before loading. Record evidence before updating. Validate before synchronizing.**

That turns AI capability management into an engineering system.

## 8. Boundaries Matter

`skill-router` does not bypass permissions. It does not automatically process unauthorized content. It does not skip safety review just because automation is possible.

High-risk changes, permission expansion, deletion, and unverified sources stop for approval.

That keeps evolution auditable, explainable, and reversible.

## 9. What Comes Next

The project is still evolving.

The most promising next steps are:

- more accurate skill-selection scoring
- finer context-budget profiles
- cross-provider experience aggregation
- automatic practice-suite generation
- scorecard-based promotion rules
- clearer visual reports

But one idea is already clear:

More AI capability does not have to mean more context on every request.

Sometimes progress is simply knowing:

**when to look, when not to look, and when looking halfway is enough.**
