# ExcelDashboard

Work done with Claude Code, and the tools for checking it.

| Folder | What's in it |
| --- | --- |
| `projects/` | One folder per project: what was asked, what was done, and its review. |
| `.claude/agents/content-reviewer.md` | The reviewer agent: supervisor, editor and proofreader for any generated content. |
| `docs/LEARNING-PLAN.md` | Step-by-step skills and practice projects. |

## Projects

- [Video edit #1 — "B-roll" clip](projects/2026-11-video-edit/README.md) (5 Nov 2026) — [review](projects/2026-11-video-edit/REVIEW.md)
- [Five-stage bookkeeping tool](projects/2026-11-bookkeeping/README.md) (12 Nov 2026): prompts, six books, reconciliation, profit report in ₦
- Logistics dashboard — not started

## Using the reviewer agent

In a Claude Code session opened on this repository, say:

> Use the content-reviewer agent to review `<file or link>` against my prompt:
> "<paste your original prompt word for word>"

It checks the output against the prompt, scores it, says whether problems came from the
prompt or the execution, rewrites the prompt, and gives you a fix list and something to
learn. Agents load when a session starts, so it's available from your next session.

Not stored here on purpose: private video footage, downloaded media, and locally
installed third-party tools (see `.gitignore`).
