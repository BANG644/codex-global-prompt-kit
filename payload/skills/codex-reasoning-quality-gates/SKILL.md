---
name: codex-reasoning-quality-gates
description: Use when choosing a model or reasoning effort, considering an Advisor, deciding whether to brainstorm or use TDD, or setting verification depth for a Codex task. Use the runtime's confirmed capabilities and risk, not assumptions.
---

# Codex Reasoning and Quality Gates

The active conversation model is the executor. A prompt or config preference does not prove that a model or reasoning level was selected; verify the runtime when routing matters.

## Model and reasoning selection

- Use the active executor for the primary work. Do not automatically route execution to GPT-6 Astra or a GPT-5.6 model. Use another executor only when the user explicitly requests it and the runtime confirms it is available.
- For GPT-6 Luna, use the highest reasoning level confirmed by the current model catalog/runtime. `max` is the last documented verified level; use `ultra` only when the runtime explicitly exposes it. Never write an unsupported level into config or infer support from a model name.
- When a subagent is genuinely needed, select its model and reasoning effort for the work package. Simple, bounded, independently verifiable execution may use a lower supported level; architecture, root-cause, complex integration, security, permissions, data loss, and autonomous judgment need the highest verified level. Do not lower a complex task just to save tokens.
- Resolve routing precedence as: task-level explicit choice > role default > global `[agents]` default > parent/platform default.
- If observed routing violates the applicable model boundary, record it and stop that dispatch rather than silently rerouting.

## Advisor gate

The default read-only Advisor is GPT-6.1 Sol at `ultra`, but call it only when the runtime exposes that exact model and level. If unavailable, record `Advisor unavailable`; do not substitute another model by guesswork.

Consult an Advisor for high-risk or irreversible actions, security or permission decisions, external publication, architecture migration, conflicting evidence, two consecutive failures of the same class, or an explicit user request. For cross-system choices with a real design disagreement, consultation is optional. Skip it for ordinary reading, mechanical edits, routine checks, and completion summaries. Use at most one consultation per task; a second requires a material new risk, evidence conflict, or changed approach.

The Advisor returns advice only and never performs side effects. Provide the smallest necessary, redacted context. If it fails, ordinary work continues; an unresolved high-risk irreversible action still stops for human input. Codex's available implementation is a soft gate using native Multi Agent V2, not a server-side same-request Advisor API.

## Design and implementation gates

- Brainstorm when a new behavior or architecture is being designed, or when uncertainty could materially change scope, cost, risk, or permissions. Skip it for clear mechanical edits and ordinary configuration changes.
- Use TDD for non-trivial logic, bugs/regressions, security or permission paths, data-loss risks, and when the user requires it. Otherwise choose the smallest verification that fits the change.
- Verification depth follows risk. Re-read changed config/code and exercise one representative path plus a relevant safety boundary for meaningful changes. Static inspection alone does not prove runtime behavior.
- In explicit Demo work, deliver the visible main path first. Optional research, Advisor review, agents, full stability work, and Formal gates must not block it unless they expose a hard boundary or the user asked for them.
