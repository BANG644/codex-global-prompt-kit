---
name: html-effectiveness
description: "Use when Codex needs examples or patterns for delivering complex output as standalone HTML artifacts instead of long Markdown. Includes Thariq Shihipar's html-effectiveness gallery: exploration grids, code review, code understanding, design systems, component variants, prototypes, slide decks, status/incident reports, flowcharts, research explainers, implementation plans, PR writeups, triage boards, feature flags, and prompt tuning editors."
---

# HTML Effectiveness

This skill is a local copy of `ThariqS/html-effectiveness`: standalone HTML examples for making AI outputs easier to inspect, compare, and share.

## Use

When creating a complex HTML deliverable, read the closest example first and adapt its structure:

- `01-exploration-code-approaches.html` / `02-exploration-visual-designs.html`: side-by-side options and tradeoffs.
- `03-code-review-pr.html` / `17-pr-writeup.html`: PR review, diff explanation, severity-coded findings.
- `04-code-understanding.html`: annotated code walkthrough.
- `05-design-system.html` / `06-component-variants.html`: design systems and UI variants.
- `07-prototype-animation.html` / `08-prototype-interaction.html`: small interactive prototypes.
- `09-slide-deck.html`: browser-based slides.
- `11-status-report.html` / `12-incident-report.html`: reports and executive summaries.
- `13-flowchart-diagram.html`: process or system diagrams.
- `14-research-feature-explainer.html` / `15-research-concept-explainer.html`: research and learning artifacts.
- `16-implementation-plan.html`: implementation plan with phases and risks.
- `18-editor-triage-board.html` / `19-editor-feature-flags.html` / `20-editor-prompt-tuner.html`: one-off editing tools.

Open `index.html` for the categorized gallery. Files under `unknowns/` are extra examples; use them only when the main 20 do not fit.

## Rules

- Keep new deliverables self-contained unless external assets are explicitly useful.
- Reuse layout ideas, navigation, interaction patterns, and information hierarchy; do not copy fictional sample data.
- Pair this with `html-delivery` for where to save generated artifacts.
