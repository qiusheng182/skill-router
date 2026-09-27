---
name: skill-router
description: Priority skill gate and administrator. Always run before any other skill. Clarify unclear tasks, scan only the active provider, and ask when uncertain. Use for routing, recommendations, skill audits/updates/sync, and learning from repeated failures.
allowed-tools: [bash, python, powershell]
---

# Skill Router

This skill is the gatekeeper and administrator for skill use. Do not invoke another skill before completing this flow.

## Administrator Mode

When the user asks to learn, audit, validate, update, roll back, or synchronize skills, follow [references/self-evolution.md](references/self-evolution.md). The safe default policy is `propose`: record and prepare a change, but do not modify an installed skill without approval.

Bundled tools:

- `scripts/learning_store.py`: record, list, and show learnings or update candidates.
- `scripts/experience_store.py`: record per-skill practice episodes and generate scorecards.
- `scripts/practice_runner.py`: run repeatable practice suites and compare versions.
- `scripts/validate_candidate.py`: validate a candidate and its target skill.
- `scripts/apply_candidate.py`: snapshot, enforce policy, and apply a validated candidate.
- `scripts/context_budget.py`: keep only selected skills model-invoked and make the rest user-invoked.
- `scripts/sync_skill.py`: synchronize provider copies and back up changed destinations.

Before applying a skill change, run:

```powershell
python <this-skill-folder>\tests\test_admin_tools.py
```

### Context Budget

When per-request context is the bottleneck, keep only `skill-router` model-invoked and hide the remaining skill descriptions from automatic invocation:

```powershell
python <this-skill-folder>\scripts\context_budget.py --provider codex --keep skill-router --apply
```

Run the command without `--apply` first to preview the estimated token reduction. Backups are written under `~/.codex/skill-evolution/context-backups/`.

### Context Compiler

When another skill is selected, avoid loading its entire documentation by default. Build a query-scoped pack first:

```powershell
python <this-skill-folder>\scripts\skill_context.py pack --skill-path <target-skill> --query "<task>" --budget 1500
```

Use the included sections and reference index. Load omitted sections or references only when the task actually needs them. Run `skill_context.py audit` to find skills with the largest lazy-loading opportunities.

## Priority Gate

Follow this order for any non-trivial task that might invoke a skill:

0. Clarify the task before scanning. If the request is ambiguous, incomplete, or cannot be turned into concrete deliverables, ask the user questions until it is executable. Do not scan or invoke skills during this phase.
1. Detect the active provider and its skill roots.
2. Scan only with a focused query. Never dump the full skill inventory for normal routing.
3. Shortlist candidates automatically.
4. If confidence is at least 0.9 and the task is low-risk, state the route and proceed. Otherwise, ask the user to choose from 2-5 options.

## Clarification Gate

Before scanning, confirm that the output, scope, input, target environment, and acceptance condition are clear. If any one is unclear, ask one focused question at a time until the task can be executed. Do not recommend a skill while the task itself is still unclear.

## Provider Adaptation

The scanner auto-detects Claude, OpenCode, Codex, Cursor, Gemini, and Windsurf roots, honoring each provider's `*_SKILLS_PATH` environment variable. Restrict the scan to the active provider with `-Provider`.

For a custom provider or one-off root:

```powershell
... -Roots "MyVendor=C:\path\to\skills"
```

## Workflow

### 1. Detect Providers

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <this-skill-folder>\scripts\scan-skills.ps1 -ListProviders
```

If the active provider is not detected correctly, select it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <this-skill-folder>\scripts\scan-skills.ps1 -Provider Claude,OpenCode -Query "pdf"
```

### 2. Scan Narrowly

Start with names only:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <this-skill-folder>\scripts\scan-skills.ps1 -Query "pdf" -Brief -Top 10
```

The scanner defaults to brief output. Use `-Compact` for short descriptions, `-Full` for complete metadata, and `-Raw` for one entry per provider. `-Top 0` is only for an explicit full audit.

### 3. Shortlist

Score candidates by meaning, not keywords:

1. The user explicitly named a skill or a near-exact phrase.
2. An artifact-specific skill matches the file type: PDF, DOCX, PPTX, XLSX, APK, image, video, browser, Notion, Linear, GitHub, and similar.
3. A domain workflow matches: debugging, TDD, review, implementation, paper reading, figure prompting, content writing, app automation, file organization.
4. A task phase matches: brainstorm, plan, implement, verify, handoff, package.
5. The active provider is direct.

Read full `SKILL.md` only for the top 2-5 candidates.

### 4. Decide Or Ask

Confidence at least 0.9 and low-risk: proceed with the route. Otherwise, list 2-5 named options with a one-line tradeoff each and wait for the user's choice. Treat an explicit instruction to proceed as confirmation of the current best route.

### 5. Output The Route

```markdown
## Confirmed Route
Primary skill: `[direct|sync-first|not-needed] skill-name`
Skill chain: `skill-a -> skill-b -> skill-c`
Next action: <one concrete next action>

## Rationale
Match: <why this route matches>
Alternative: <nearby skills and why they are not first choice>
Confidence: <0.0-1.0>

## Available Providers
Claude: <available/missing>
OpenCode: <available/missing>
Codex: <available/missing/reference-only>
```

Keep the output compact. Do not include the full inventory.

## Safety And Boundary Rules

For APK modification, reverse engineering, account automation, scraping, credentialed services, external APIs, or anything that could affect third-party systems, check authorization and intent first. Recommend only authorized-maintenance or defensive skills when appropriate.

Do not route to a powerful automation skill when a safer local workflow is enough.

## Maintenance Rule

Never rely on a hardcoded skill list. New skills are discoverable as soon as their folder contains a valid `SKILL.md` under a configured provider root.
