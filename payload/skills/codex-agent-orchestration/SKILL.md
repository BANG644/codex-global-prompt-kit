---
name: codex-agent-orchestration
description: Use when a Codex task may benefit from parallel subagents, delegated work packages, explicit write ownership, or coordinating agent waits. Covers when not to delegate, task boundaries, context sharing, routing, and integration.
---

# Codex Agent Orchestration

Use delegation only when it shortens the critical path. The primary agent remains the owner of scope, permissions, the critical path, necessary direct work, integration, and final acceptance.

## Decide whether to delegate

- Delegate only work that is independent, low interaction, separately verifiable, and has a clear output and stop condition.
- Keep small, tightly coupled, overlapping-write, or coordination-heavy work with the primary agent. Do not create agents to satisfy a quota or because a task merely looks complex.
- In Demo work, a delegated result must feed the visible main path or change its next decision. Do not spend parallel capacity on duplicate reading, status-only work, or a review that cannot affect the next step.
- A role is a reusable capability description, not a live agent or a reason to spawn one. Create a live agent only for a ready work package. Use a general role when no specialist is needed; use legal, medical, financial, or other domain specialists only when requested or materially required by risk.

## Cost-aware model routing

- Model collaboration is separate from Advisor review. Keep the lead model responsible for scope, judgment, integration, and final acceptance. When the runtime confirms a suitable lower-cost executor such as `gpt-6-luna`, a high-cost lead such as `gpt-6.1-sol` may delegate independent, repetitive, low-complexity work to it without lowering the final acceptance standard.
- This routing is available to any executor with the required capability. With same-level or similarly priced models, the main benefit is throughput or latency; with a higher-cost lead and lower-cost executor, it may also reduce execution cost.
- Good candidates include mechanical inventory, bounded extraction or conversion, independent static checks, repetitive comparisons, and parallel research collection with a fixed source and output contract. Keep requirements interpretation, architecture, security or permissions, data-loss decisions, ambiguous judgment, conflict resolution, integration, and final synthesis with the lead unless the task explicitly defines a separate review package.
- Before dispatch, estimate the work size, context-transfer cost, dispatch and wait overhead, review or integration cost, and expected savings or critical-path improvement. Keep tiny tasks local; delegate only when independence, batching, or parallelism makes the total tradeoff worthwhile.
- Give every delegated package an owner, write boundary, acceptance criteria, stop condition, and fallback. Treat worker output as evidence or a draft until the lead verifies it at a risk-appropriate depth. If the runtime does not confirm the selected model or route, do not invent or silently substitute one; use the active executor.

## Define a work package

State the goal, input scope, write scope, expected output, acceptance criteria, and stop condition. Give the agent only those materials needed to deliver it. Prefer no history or a short selected excerpt; include more history only when correctness depends on it. When routing to a different executor, record the reason in the package: repetitive or bounded work for cost efficiency, or parallel work for throughput. Never grant broader authority than the primary task.

Use the host's native Multi Agent V2 capability when it is exposed. Respect model and reasoning constraints in `codex-reasoning-quality-gates`; do not guess model availability or silently route to another model. A task-level explicit choice takes precedence over role defaults, global `[agents]` defaults, and parent/platform defaults.

## Coordinate and integrate

- Let independent packages proceed in parallel. Wait only at a real dependency barrier; do not block the main path for polling, progress reports, or formal review without material risk.
- Collect results when they are complete, blocked, or no longer useful. Close or release agents that have finished or produced no usable output.
- The primary agent checks the result against its acceptance criteria, resolves cross-package conflicts, performs the integration work, and owns the final user-facing result.
- Trigger research, QA, cross-checking, or review when risk and expected value justify it. Full review is for a meaningful milestone, material high risk, external release/merge, or an explicit request. Routine tasks need only a proportionate check of affected behavior.
