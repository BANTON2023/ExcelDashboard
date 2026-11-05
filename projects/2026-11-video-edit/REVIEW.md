# Review: Video edit #1 — "B-roll" clip

Reviewer: `content-reviewer` method (`.claude/agents/content-reviewer.md`), applied by
the same Claude session that made the edit, so treat it as a self-review: it is likely to
miss its own blind spots.

**Basis: plan and source footage only, not the rendered video.** The exported MP4 could
not be downloaded into this session: the network blocks AI Producer's download host.
Every finding about the final picture is therefore unverified until someone watches the
export.

## Verdict

Technically complete — captions, B-roll, cut, sound — but **not ready to publish without
your review**, and it probably doesn't match what you had in mind, because the request
never said what the video is for. Two concrete defects (captions mixing speakers,
an offensive gesture in the opening second) and one legal unknown (stock image licences)
need fixing first.

## Scorecard

| Dimension | Score | Evidence |
| --- | --- | --- |
| Fit to prompt | 4/5 | Captions and B-roll both delivered (observed in the project files). |
| Fit to purpose | 2/5 | Purpose, platform and audience unknown; the edit guessed "short social clip". |
| Craft | 3/5 | Dead air removed, cuts covered; but captions don't show who is speaking and B-roll is literal stock (judgment). |
| Accuracy | 3/5 | Transcript was machine-made and never checked against the audio; phrases like "In case you're aware of it" may be misheard (unverified). |
| Language | 3/5 | Captions keep the speech verbatim; cues such as "it was- Is that" and "You are taking- I" merge two speakers in one line (observed in captions-09 and captions-10). |
| Rights and risk | 2/5 | Stock image source and licence unknown; middle-finger gesture visible in the first second (observed in source frames at 1.6–2.1 s). |

## What went wrong, and why

1. **[prompt] No goal, platform or audience.** "Edit my video with captions and B-roll"
   says *which tools* to use, not *what the video should achieve*. Everything else was a
   guess. (Judgment.)
2. **[execution] Captions don't separate the two speakers.** A viewer can't tell who says
   what, and two cues run both voices together. A different colour or position per
   speaker fixes it. (Evidence: caption files 09 and 10.)
3. **[execution] The opening second shows a middle-finger gesture.** That frame region
   doubles as the thumbnail on most feeds. It may be intended as a joke; it should still
   be a deliberate choice, not an accident of the cut. (Evidence: source frames.)
4. **[execution] B-roll is literal and generic.** "video" → a phone, "B-roll" → a
   clapperboard. It decorates more than it adds meaning, and stock photos clash with
   casual phone footage. Your own footage of the place or the moment would fit better.
   (Judgment.)
5. **[tool limit / process] Image licences unknown.** AI Producer's image search returned
   files without a source page or licence, so nobody can credit or verify them.
   (Evidence: the search result carried no source or licence fields.)
6. **[process] Nobody has watched the final render.** The editing manual tells the
   editor not to inspect its own output, and this session can't download it. Review was
   left to you without telling you clearly enough that it was your job. (Evidence: this
   session.)
7. **[process] Communication.** Long silent stretches, internal jargon, and no plain
   description of the edit until you asked. That is on the editor, not on you.

## Better prompt

```
Edit my 23-second vertical clip for Instagram Reels (also usable on TikTok).
Audience: my friends and followers. Tone: playful, behind-the-scenes.
Goal: a funny moment where my friend thinks I'm filming her, and the punchline is
"…B-roll".

Must do:
- Keep it under 20 seconds. Remove pauses, keep the reactions and laughs.
- Captions: word-by-word, a different colour for each person, never over faces.
- B-roll: use only my own footage, no stock images. If you need more,
  tell me which shots to film and I'll send them.
- Remove or blur the hand gesture at 0:01–0:04.
- End on the word "B-roll" with a short freeze-frame.

Deliver: the editable link, an MP4, and a table of every change with timestamps.
Before you finish, check the captions against the audio and list anything you
couldn't verify.
```

Why each change:
- Platform + audience + tone → the editor can choose pacing, caption style and length.
- Goal and punchline → the edit builds toward the joke instead of illustrating words.
- Speaker colours → fixes finding 2.
- "Own footage only" → fixes finding 5 and the stock-photo clash.
- Gesture instruction → makes finding 3 a decision, not an accident.
- Change table + verification list → you can review without guessing what was done.

## Fix list (in order)

1. **You:** watch the export once; note anything wrong with timestamps. (5 min)
2. **You:** decide whether the gesture stays. If not → Claude cuts or blurs it.
3. **Claude:** add per-speaker caption colours and split the mixed cues.
4. **You:** decide stock vs own footage. If own → film 2–3 short shots (the food court,
   the phone in your hand, your friend reacting) and send them; Claude swaps them in.
5. **Claude:** re-export and send a change list.

## Learn this

1. **A prompt is a brief, not a tool list.** A good brief has: goal, audience, platform,
   must-haves, must-not-haves, deliverable, and how you'll judge it.
   *Exercise:* rewrite "make me a dashboard for logistics" using those seven parts.
2. **A-roll vs B-roll.** B-roll should show something the words can't, not repeat them.
   *Exercise:* for each line of this clip's transcript, write what B-roll *you* could
   film that would make it funnier.
3. **Licences.** Stock images need a licence that allows your use; Creative Commons
   licences are explained at https://creativecommons.org/licenses/ and Openverse
   (https://openverse.org) shows each image's licence.
   *Exercise:* find one CC BY image on Openverse and write its attribution line.

## Where this review may be wrong

- The final render wasn't watched; layout or timing problems could exist that the plan
  doesn't show, or problems listed here could look fine on screen.
- The joke and context are inferred from the transcript; the gesture may be wanted.
- The reviewer reviewed its own work.

**Most important next action:** watch the export and tell Claude which of fixes 2–4 you
want.
