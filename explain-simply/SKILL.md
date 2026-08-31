---
model: opus
name: explain-simply
description: Re-say the last summary, report, or finding in plain English that a colleague who has not been reading along can follow, and list what is still open. Use when the user says "explain that simply", "in simple English", "in plain English", "I don't understand", "say that again simply", "simpler", "what does that mean", "recap that", "say that in English", or asks for the short version of something already said. Translates what was already said; it never does new work, never re-runs a check, and never softens a caveat to make it fit, and never recommends what to do next, which is /next-step's job.
argument-hint: "[optional focus, e.g. 'just the decision', 'shorter', 'skip the background']"
---

# Explain simply

The user did not understand the last thing you said, or wants it in a form they can act on. Say it again in plain words.

**This skill restates. It does not recommend.** Working out what to do next belongs to `/next-step`, and the split is deliberate: this one makes a message understandable, that one turns a decision or a status into an action with a command attached. Leading with what the user is actually choosing belongs to `/next-step`, not here.

## The one hard constraint

**This is a translation, not new work.** No tool calls, no re-reading files, no re-running a check, no fresh investigation. Everything you need is already in the conversation. If you find yourself wanting to verify something before you can say it plainly, that is a sign the original claim was shaky, and the honest move is to say so in the recap rather than to go and settle it now.

`$ARGUMENTS` may narrow the ask ("just the decision", "shorter", "skip the background"). Honor it.

If there is nothing to recap yet, say that in one line and ask what they want explained. Do not manufacture a summary of the session so far.

## Do not let the plain version become the rosier version

Compression is exactly where a hedge gets dropped and "probably works" quietly becomes "works". Every caveat, limit, and unknown in the technical version has to survive into the plain one. Being readable is not permission to be more confident.

Two specific carries:

- **If it is finished but not in front of the reader, that sentence goes FIRST**, on its own line, before any account of what happened. Not committed, not pushed, not deployed, not merged, behind a flag, local only. A tidy recap reads as "it works", so a caveat placed after it does not land.
- **If a check passed but could not see part of the claim, say what it could not see.** "The tests pass, and they do not cover the Hebrew rendering" is one line and it is the honest one.

## The shape

In this order. Skip any part that is genuinely empty rather than padding it.

```
<the blocking fact, one line, only if something is finished but not live/shared>

**What happened.** Two to four short lines.

**What is still open.** Numbered, one line each. Write "Nothing" if nothing is.
```

That is the whole shape. There is no "what I suggest" block and no recommendation of any kind.

**One boundary, because the two rules can collide.** If the thing you are restating ALREADY contained a recommendation, carry it across. Dropping it would be an unfaithful translation, and nothing may be lost in the compression. What you must not do is invent one that was not there, or turn a list of open items into a ranked plan. If the user wants to know what to do next, say in one line that `/next-step` answers that, and stop.

## The words to strip, and this is most of the job

The failing version of a recap is almost never wrong. It is written in the vocabulary of the session, to a reader who has been in it. Rewrite for a colleague who walked in five minutes ago.

Strip all of these:

- **Internal machinery**: phase numbers, stage numbers, clause numbers, rule numbers, PR numbers, issue numbers, commit hashes, run ids.
- **Names of your own tools**: skills, agents, commands, hooks. The reader does not need to know which reviewer found it or which skill ran.
- **Harness jargon**: gate, routed, parked, escalation, reap, verdict, terminal state, vacuous, mutation, tracer bullet, ramp, blast radius, non-vacuous, fail closed.
- **File paths where a sentence would do.** "The settings file" beats a 60-character path. Keep a path only when the reader has to open it, and then give the path alone on its line.
- **Units and identifiers the reader does not think in.** "1.8 GB" not "1800 MiB". "The bigger box" not the instance id. "The client's copy of the repo" not the remote name.

Two rules that decide the close calls:

- **Prefer deleting a jargon word to defining it.** A glossary is the fallback, not the fix. If a term genuinely has to stay because it names the thing, define it in the same sentence, once.
- **Name the subject instead of hiding it.** "The deploy check reads the wrong commit" is clear. "It was routed" is not.

## The rule is not "be brief"

Measured: the recap that failed was SHORTER than the one that worked. It failed because it was written in insider vocabulary, not because it was long. Explaining the mechanism is welcome. Making the reader decode it is not.

So: aim for something the reader gets through in under a minute, and spend words freely on the one thing that is hard to follow. If a mechanism needs three sentences to make sense, give it three sentences. Cutting it to one clause of jargon is the failure this skill exists to prevent.

## Check the draft before sending

Read it back once as though you had not seen the session, and answer these:

1. Does the first line say the thing the reader most needs to know, including any "this is not live yet"?
2. Can a reader who joined five minutes ago follow every sentence? Scan for the banned list above, word by word, not by feel.
3. Did any caveat, limit, or unknown from the original get lost?
4. Did anything get INVENTED? A recommendation, a ranking, or a next step that was not in the original is the failure this skill is most likely to commit.
5. If the reader only reads the first three lines, are they correctly informed?

If a scan is worth automating on a long recap, write the draft to a scratch file and grep it for the jargon list. For an ordinary recap, reading it back against the list is enough.

## Writing rules

These apply because a recap is chat prose the reader often forwards to somebody else:

- No em dashes. No box-drawing characters. No markdown tables (the terminal renders them into box characters and CLIPS the cells, silently dropping data).
- No AI-typical vocabulary, no rule-of-three, no significance inflation.
- Between you and the user, "we" is correct. If the recap is going to someone else, rewrite it in the first person singular, in the user's own voice.
- Bullets and short numbered lists, not paragraphs of prose.
