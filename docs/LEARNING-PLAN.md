# Learning plan

Goal: be able to brief Claude precisely, judge what comes back, and know when Claude is
wrong. Each level ends with a small project you do yourself. Ask Claude to review each
one with the `content-reviewer` agent.

## Level 1 — Briefing (prompts)

A prompt is a brief. Use this template every time:

```
Goal:          what the result must achieve, for whom
Audience:      who sees it, what they already know
Platform:      where it will be used (Reels, Excel, a report, a meeting…)
Must have:     non-negotiables
Must not:      things to avoid
Deliverable:   files, format, length
Done when:     how you will judge it; what Claude must check before finishing
```

**Project 1:** Rewrite your last three requests to Claude with this template. Send the
before/after to the reviewer agent and compare its answers.

## Level 2 — Reviewing

Never accept work you haven't looked at. For anything Claude makes, ask:
1. Did it do what I asked? (requirement by requirement)
2. Would it work for the audience?
3. What did it guess? (ask Claude: "list every assumption you made")
4. What couldn't it verify? (ask Claude: "what did you not check?")

**Project 2:** Watch the exported video from project #1, write down 5 problems with
timestamps, then compare your list with `projects/2026-11-video-edit/REVIEW.md`.

## Level 3 — Video basics

Learn the words: A-roll, B-roll, rough cut, jump cut, punch-in, captions, safe area,
aspect ratio (9:16 vertical, 16:9 horizontal), export.

**Project 3:** In the AI Producer editor, change one caption's wording, move one B-roll
image by a second, and re-export. Then film 3 B-roll shots of your own (5 seconds each,
vertical, steady) and ask Claude to swap them in for the stock photos.

## Level 4 — Rights and sources

- Stock media needs a licence that permits your use. Creative Commons licences:
  https://creativecommons.org/licenses/ — avoid NC (non-commercial) and ND (no
  derivatives) if you will monetise or edit.
- For research, a source counts only if you can open it and it says what is claimed.
  AI output is scaffolding until a human has checked it against the source.

**Project 4:** Find 3 images on https://openverse.org you could legally use in a
commercial video and write the attribution line for each.

## Level 5 — Git and GitHub

- **Repository:** the project folder, with its full history.
- **Commit:** a saved snapshot with a message.
- **Branch:** a separate line of work, so experiments don't touch the main version.
- **Pull request (PR):** a request to merge one branch into another; GitHub shows the
  changes, lets people comment, and you click Merge to accept.

**Project 5:** On github.com, edit this file on a new branch (fix a typo or add a
note), open a pull request, read the "Files changed" tab, and merge it.

## Level 6 — Capstone: logistics dashboard in Excel

Brief it with the Level 1 template before any work starts. Bring:
- a sample of the data (column names and 20 rows are enough),
- the 3 decisions the dashboard must help you make,
- who will read it and how often.

Then: Claude builds → you review with Level 2 questions → reviewer agent scores it →
Claude fixes → you sign off.
