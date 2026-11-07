# ExcelDashboard

Work done with Claude Code, and the tools for checking it.

| Folder | What's in it |
| --- | --- |
| `projects/` | One folder per project: what was asked, what was done, and its review. |
| `.claude/agents/content-reviewer.md` | The reviewer agent: supervisor, editor and proofreader for any generated content. |
| `.claude/agents/critical-thinker.md` | The challenger agent: questions every idea and output, adds new perspectives, proposes something better, coaches prompting and research. |
| `.claude/agent-memory/critical-thinker/` | What the challenger remembers between sessions (patterns, past challenges, open questions). |
| `CLAUDE.md` | Tells Claude to end every substantive reply with a challenge, a better idea, a prompt tip and a research lead. |
| `docs/LEARNING-PLAN.md` | Step-by-step skills and practice projects. |

## Projects

- [Video edit #1 — "B-roll" clip](projects/2026-11-video-edit/README.md) (5 Nov 2026) — [review](projects/2026-11-video-edit/REVIEW.md)
- Logistics dashboard — not started

## Using the reviewer agent

In a Claude Code session opened on this repository, say:

> Use the content-reviewer agent to review `<file or link>` against my prompt:
> "<paste your original prompt word for word>"

It checks the output against the prompt, scores it, says whether problems came from the
prompt or the execution, rewrites the prompt, and gives you a fix list and something to
learn. Agents load when a session starts, so it's available from your next session.

## Using the critical-thinker agent

> Use the critical-thinker agent to challenge this: "<your idea, plan or prompt>"

Or after Claude answers: *"Run the critical-thinker on your last answer."* It sharpens
the claim, attacks its assumptions, brings in perspectives you haven't considered,
proposes something better, and tells you how to prompt and research better next time.

Even without calling it, `CLAUDE.md` makes every substantive reply end with a short
Challenge / Better / Prompt tip / Dig deeper block.

Memory: the agent reads and updates `.claude/agent-memory/critical-thinker/MEMORY.md`.
Cloud sessions start fresh, so ask Claude to commit and push that file when it changes.
It cannot see your claude.ai chats; for that, use the version in
[docs/CRITICAL-THINKER-CLAUDE-AI.md](docs/CRITICAL-THINKER-CLAUDE-AI.md).

Not stored here on purpose: private video footage, downloaded media, and locally
installed third-party tools (see `.gitignore`).
