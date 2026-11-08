---
name: codex-agent-orchestration
description: Use when a Codex task may benefit from parallel subagents, delegated work packages, explicit write ownership, or coordinating agent waits. Also applies to Token Efficiency under a Sol lead, including batching repetitive work for Luna without an explicit user reminder.
---

# Codex Agent Orchestration

Delegate when it shortens the critical path or, under a Sol lead, reduces total costly-token use without lowering quality or missing the user's delivery constraints. The primary agent remains the owner of scope, permissions, the critical path, necessary direct work, integration, and final acceptance.

## Decide whether to delegate

- Delegate only work that is independent, low interaction, separately verifiable, and has a clear output and stop condition.
- Keep small, tightly coupled, overlapping-write, or coordination-heavy work with the primary agent. Do not create agents to satisfy a quota or because a task merely looks complex.
- In Demo work, a delegated result must feed the visible main path or change its next decision. Do not spend parallel capacity on duplicate reading, status-only work, or a review that cannot affect the next step.
- A role is a reusable capability description, not a live agent or a reason to spawn one. Create a live agent only for a ready work package. Use a general role when no specialist is needed; use legal, medical, financial, or other domain specialists only when requested or materially required by risk.

## Cost-aware model routing

- **Scope and default:** apply this cost-saving policy only when the runtime identifies the active primary as Sol (currently `gpt-6.1-sol`), whether or not the user says "Token Efficiency". Other leads retain ordinary delegation and Advisor rules; same-level parallelism does not imply a cost saving.
- **Local cost preference:** for this user's current setup, treat Sol tokens as scarce, including the lead's own work, Sol workers, and Sol Advisors; treat Luna as effectively unmetered for routing purposes. This is a user-provided cost preference, not a universal pricing or unlimited-capacity claim. Respect actual context, concurrency, service limits, and user budgets; do not impose new hard token caps without a user request.
- **Prefer Luna for suitable execution:** when the runtime confirms `gpt-6-luna`, actively look for coherent batches of mechanical or repetitive work, execution of an already detailed plan, bounded research collection or shallow analysis, and factual inventory or status reporting. Research with ambiguous evidence or difficult inference is not automatically low-complexity. Use independent workers in parallel where their outputs and write scopes are separable; do not create one worker per tiny item.
- **Check the total trade-off:** weigh useful work against briefing/context transfer, dispatch, waits, checking, rework, and integration. Keep small or tightly coupled tasks local. Dispatch only when the expected saving or speed gain is worthwhile, and request concise findings with source or artifact references rather than full logs. Review at the depth required by risk without routinely repeating the entire worker task.
- **Keep difficult judgment with Sol:** retain scope, requirements interpretation, architecture, security or permission decisions, data-loss decisions, ambiguous or deep analysis, cross-package conflicts, integration, and final acceptance. Use another Sol worker or Advisor only when its difficult reasoning or independent perspective justifies the extra cost. If a Luna package becomes uncertain or too difficult, have it return findings and stop for lead reassessment; do not force repeated low-quality retries or silently promote the whole batch to Sol.
- **Confirm routing and ownership:** give each package an owner, write boundary, acceptance criteria, stop condition, and fallback. Explicitly select the confirmed Luna model in the dispatch API; an unspecified worker may inherit the Sol parent. Respect the API's history-sharing constraints and provide only the context needed. If the route is unavailable, do not claim Luna was used or silently spawn Sol; reassess doing the necessary work locally. The lead still verifies and owns the final result.

## Define a work package

State the goal, input scope, write scope, expected output, acceptance criteria, and stop condition. Give the agent only those materials needed to deliver it. Prefer no history or a short selected excerpt; include more history only when correctness depends on it. When routing to a different executor, record the reason in the package: repetitive or bounded work for cost efficiency, or parallel work for throughput. Never grant broader authority than the primary task.

Use the host's native Multi Agent V2 capability when it is exposed. Respect model and reasoning constraints in `codex-reasoning-quality-gates`; do not guess model availability or silently route to another model. A task-level explicit choice takes precedence over role defaults, global `[agents]` defaults, and parent/platform defaults.

## Coordinate and integrate

- Let independent packages proceed in parallel. Wait only at a real dependency barrier; do not block the main path for polling, progress reports, or formal review without material risk.
- Collect results when they are complete, blocked, or no longer useful. Close or release agents that have finished or produced no usable output.
- The primary agent checks the result against its acceptance criteria, resolves cross-package conflicts, performs the integration work, and owns the final user-facing result.
- Trigger research, QA, cross-checking, or review when risk and expected value justify it. Full review is for a meaningful milestone, material high risk, external release/merge, or an explicit request. Routine tasks need only a proportionate check of affected behavior.
