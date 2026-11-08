---
name: html-delivery
description: "Use when Codex should deliver complex, information-dense output as a self-contained HTML artifact instead of dumping long Markdown in chat: long reports, research summaries, comparison matrices, galleries, dashboards, timelines, dense tables, visual briefs, or any user request to output/save HTML. Also use to archive generated HTML under the current project."
---

# HTML Delivery

Use a self-contained `.html` file when the result is easier to browse, inspect, or reuse as an artifact than as chat Markdown.

## Decide

Use HTML when:

- The answer would otherwise be long, scroll-heavy Markdown.
- The deliverable needs sections, cards, dense tables, timelines, dashboards, galleries, charts, or navigation.
- The user wants a polished file, reusable artifact, or browser-readable package.

Do not use HTML for short answers, small code diffs, command output, plain lists, or when the user explicitly asks for Markdown or plain text.

## Location

- Follow a user-specified location first. In a project, save HTML reports to `<project-root>/docs/reports/`; save non-report HTML artifacts to `<project-root>/outputs/html_archive/`.
- If no project root is available, save HTML to `%USERPROFILE%\.codex\html_archive\`.
- Create the directory on demand.
- Name reports with a concise, descriptive Chinese title; add a date, version, or subject only when needed to distinguish similar reports. For other HTML artifacts, use a readable name suited to the project.

## Artifact

- Prefer one self-contained HTML file: inline CSS/JS and embedded data.
- Use external CDNs only when they materially reduce bulk and network access is acceptable.
- Include `<meta charset="utf-8">` and a responsive viewport.
- Add a visible title/date/source summary at the top when it helps the reader.
- Keep the chat reply short: link the file and state what it contains; do not paste the whole HTML into chat.
- If the HTML is visual/design-heavy, inspect it in a browser or run a quick static sanity check when practical.

## Reuse Design References

For complex HTML artifact patterns, use `html-effectiveness` first. If a brand/style reference is requested and `awesome-design-html` is installed, use it as an optional visual reference only.
