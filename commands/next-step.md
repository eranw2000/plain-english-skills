---
model: inherit
description: "Name what to do next on a project, in a few lines, with the command to start it. Pass a number for several options that differ in kind. Read-only; recommends, does not do."
argument-hint: "[count 1-5] [project name] and/or a constraint (e.g. '2', 'billing-api', '3 only 30 minutes')"
---

The user is asking what to work on next.

**Default: one recommendation.** That is the point of the command, and at a count of one the output is exactly what it has always been.

**On request, several.** A number in `$ARGUMENTS` asks for that many, up to 5, so `/next-step 2` returns two. Even then this is a shortlist with a stated pick, never a dump of the board, and the options must differ in KIND rather than being the next items down the same ranking. The rules for that are in Rank and Recommend below.

**Say it the way `/explain-simply` would.** Whatever you recommend, write it for someone who has been away for a week. Apply the list in `~/.claude/skills/explain-simply/SKILL.md`, section "The words to strip", which owns that vocabulary: no phase or PR numbers, no names of your own skills and agents, no harness jargon, no long paths where a sentence would do. That skill restates a message and never recommends; this command recommends. The plain-English requirement is the only thing the two share.

This command is **read-only**: inspect and report, never commit, push, deploy, or edit files. The only mutation is offered at the very end, and only if the user says yes.

`$ARGUMENTS` may carry a project name, a constraint on the session shape, or both. Constraints are real inputs, not decoration: "only 30 minutes" rules out anything with a review round in it, "nothing that deploys" rules out a release, "no code" points at decisions and docs. If the argument names no project, resolve from the current directory.

**A bare number 1 to 5, anywhere in the arguments, is the count of recommendations.** Strip it out and read whatever remains as project and constraint, exactly as before, so `/next-step 3 billing-api` and `/next-step billing-api 3` mean the same thing. No number means one. A digit inside a word is not a bare number and is not the count, so `s3sync` and `v2` are project text. A number above 5 is refused in one line rather than silently truncated, because past five this stops being a decision aid and becomes the board dump the command exists to avoid.

## Setup: resolve the project

In order, stop at the first hit. Never string-build a project path and assume it exists.

1. If `$ARGUMENTS` names a project, match it under `~/.claude/projects/` by name. The folder is sometimes prefixed and does not always equal the repo name, so match rather than construct: `find ~/.claude/projects -maxdepth 1 -type d -iname '*<arg>*'`.
2. Else if cwd is inside `~/.claude/projects/<X>/`: project = `<X>`.
3. Else if cwd is inside a git repo (`REPO_ROOT=$(git rev-parse --show-toplevel)`): take the repo basename and match it under `~/.claude/projects/` with the same `find`.
4. On zero or several matches, list `ls -lt ~/.claude/projects` (top 5) and ASK which project. Do not guess.

State the resolved project in one line and move on. Capture `REPO_ROOT` if a linked repo is found; the git and PR sweep needs it.

## Gather (keep it cheap)

This is a ranking pass, not a full session briefing. You need enough signal to rank. Read only:

1. The project `TODO.md`: the pin block (any `>>> NEXT SESSION <<<` header) and the **Active** bucket. Skip Queued and Parked unless Active turns out to be empty. While you are in there, note one kind of item that ranks differently from ordinary work: anything written as a decision rather than a task, which in these files reads as "Decide whether", "Decide what to do about", or "my call".
2. Git state in the linked repo: current branch, `git status --porcelain`, ahead/behind against `origin/main`.
3. Open PRs against main (`cd "$REPO_ROOT" && gh pr list --base main --state open`), including whether each carries a review verdict. **Run it from the repo, never from the project data dir**: if you version-control your `~/.claude` directory, a data dir sits inside that repo, so a bare `gh` resolves to your config repo and returns `[]` regardless of the project's real PRs. With no linked repo, skip this source and say so rather than reporting zero.
4. The project `CLAUDE.md`'s most recent shipped entry, for what just landed and what it says is still open.
5. **Any external tracker the user actually works between sessions**, if the project has one. The `TODO.md` on disk is only half the list when a board exists, and the half you can see is the older one. Fold what the board says into the ranking rather than listing it: an item the user moved into the current sprint is them telling you what they want next, and it outranks your own reading of the Active bucket. If there is no board, or it is unreachable, say so in one clause and rank on the file alone.

Skip a source silently if its tool or file is missing. This is a ranking pass, not an inventory; do not sweep the codebase for markers.

## Verify the pin before you trust it (only if there is one)

Most projects have no pin block, so treat it as the exception rather than the norm. If this one has none, skip straight to Rank and lean on the Active bucket. Nothing below is a reason to go looking for a pin that does not exist.

Where there is one, a `NEXT SESSION: start here` block is the strongest single signal, and it is also the one most likely to be stale, because it is written at the end of the session it describes and nothing re-checks it afterwards.

So before recommending whatever it names, **confirm that work is still open**. A branch it calls unmerged may have shipped (check with `git merge-base --is-ancestor <squash-sha> origin/main`, since a squash merge leaves the branch looking unmerged). A PR it calls open may be closed. A blocker it names may have been fixed.

If the pin is stale, say so plainly and correct for it. A stale pin that misdirects the next session is itself a candidate for the recommendation, because it is cheap to fix and every future session pays for leaving it.

This is the standing "validate the premise before any fix whose scope the premise decides" rule, applied to the one premise this command rests on.

## Rank

Apply these in order. The first rule that clearly separates two candidates decides between them.

1. **A decision that GATES ready work beats doing any work.** It is the same logic as the rule below it, one step earlier: the work behind it is already built and paid for, and what releases it is a sentence from the user rather than a session of effort. A goal or an approval that several built things are queued behind is the clearest case. **Qualifying is narrow and that is the point**: the decision must be blocking work that is otherwise ready to proceed. A decision that merely sits open, however long it has sat, does not qualify and stays in the waiting line. On a board with a dozen open questions, usually one or none passes this test.
2. **Finishing beats starting.** Work that is built, reviewed, and one command from shipping outranks anything not yet begun. An unreleased CLEAN PR is the highest-value item on almost any board, because its value is already paid for and sitting idle, and because a branch left open drifts behind main.
3. **A live correctness or safety problem beats everything except finishing and a gating decision.** Something wrong in production, a credential to rotate, a guard that does not fire. Weight it by whether it is reachable today, not by how bad it would be.
4. **Unblockers beat blocked work.** If one item is the gate on several others, it is worth more than its own line suggests. Say how many things it unblocks.
5. **Cost that is growing beats cost that is flat.** A file past its size threshold, an index near a byte cap, a queue filling up. These have a deadline without having a due date, and they get harder, not just later.
6. **Cheap and durable beats expensive and local.** A one-line fix that stops a class of mistake recurring outranks a large fix that closes one instance.
7. **Prefer work that fits the session the user actually has.** Honor any constraint in `$ARGUMENTS`. Absent one, prefer something that reaches a safe stopping point in a single sitting over something that will strand them mid-build.

### When more than one is asked for

The ranking above picks slot 1. The remaining slots are NOT the next items down that list. The item ranked second is usually the same kind of work as the first and slightly less urgent, and that is not a choice.

**Each option must differ from the others on a stated axis.** The axis is one of:

- **Size.** A full session against something that fits in twenty minutes.
- **Type.** Shipping something already built, against starting something new, against answering a decision, against maintenance whose cost is growing.
- **Risk.** Work that touches production against work that cannot break anything.

Name the axis in the option's own line, in plain words rather than these labels: "the twenty-minute one", "if you would rather not touch production today".

**A gating decision takes slot 1 and no other slot.** He asked for a choice of work, and two questions is not that. One real exception: if two separate decisions each gate ready work, say so and let them take two slots.

**If fewer than the requested number genuinely qualify, return fewer and say so in one clause.** Never pad to reach the number. An invented second option is worse than a short answer, because the user will spend real time weighing something you already know is filler.

**Two things are never the recommendation**, no matter how they rank:

- **Anything that needs the user physically.** A pass on a real phone, a drive, an action in somebody's web console. These are not next steps for a working session; they are things to hand over. Surface them in a separate one-line "waiting on you" note so they stay visible without competing. **A decision is NOT in this category**, which is the distinction rule 1 turns on: a physical action cannot be the answer because the user has to leave the desk to do it, while a decision that gates ready work is answerable in a sentence from where they are sitting. Only decisions that fail rule 1's blocking test belong on the waiting line.
- **Anything the user has parked.** Parked means do not propose unsolicited. Respect it.

## Recommend

**Hard budget at a count of one: 12 lines or fewer, and the answer plus its
first command are the first three lines.** Everything after that is a footer the user
is free to skip. This is the whole point of the command, so treat the budget as
the spec rather than as a style preference.

**The budget scales with the count, it does not stretch.** Each option gets at
most four lines of prose plus its fenced command, and the footer stays two lines
however many options there are. That puts two options near 20 lines and three
near 28. If an option cannot be said in four lines it is not ready to be
recommended, so cut it or replace it rather than borrowing room from another.

The shape, in this order and nothing else:

```
**<the concrete thing>.**

<one sentence of why>

<the command, in a fenced block>

Runner-up: <one thing>. Also open: <one thing>.
Waiting on you: <n> items (<three-word gist each>).
```

The last two lines are optional. Drop the runner-up line if nothing is close.
Drop the waiting line if nothing needs the user.

**When the count is more than one**, number the options and give each one the
same shape as the single answer, then close with your pick:

```
1. **<the concrete thing>** <one clause naming how it differs: the short one, the safe one>

<one sentence of why>

<the command, in a fenced block>

2. **<the second thing>** <its clause>

<one sentence of why>

<its command, in a fenced block>

I'd start with <n>, because <reason>.
Waiting on you: <n> items (<three-word gist each>).
```

**The pick line is not optional.** Handing over a numbered menu with no
recommendation moves the ranking work back to the user, which is the failure this
command already refuses to commit on a single answer. They can overrule it in one
word; that is the point.

Drop the runner-up line when the count is more than one, since the other options
already are the runners-up.

**When the answer is a decision (rule 1), the shape does not change, but the
fenced block holds the QUESTION rather than a command**, stated so it can be
answered yes or no, plus your recommended answer. A decision handed over as an
open question moves the work to the user instead of doing it; a decision handed
over with a recommendation costs them one word. Say in the why-sentence what is
blocked behind it, since that is the whole reason it outranked real work.

Then stop and offer to start it, or at a count above one, to start whichever the
user names. Ask first: this command recommends, it does not begin work on its own.

**What NOT to write.** Each of these is what makes a short answer read as a
report:

- **Never cite the ranking rules.** "Rule 2, finishing beats starting" is
  internal machinery. The user asked what to do, not how you decided. The rules
  are for you; the answer is for them.
- **No trade-off paragraph.** If the pick was close, that is what the
  runner-up line is for, or at a count above one, the clause on each option
  naming how it differs. One clause at most, either way.
- **No "what this could not see" paragraph.** Compress it to a clause on the
  runner-up line, and only when it would actually change the answer. The full
  version reads as hedging and pushes the answer off the screen.
- **No restating the gather.** He does not need to know the branch was clean or
  that a pin was verified unless it changed the answer.
- **No headings, no bold section labels.** At this length they are noise, and
  they are what makes a short answer look like a report.

If the pin turned out to be stale, that is worth one clause, because it means
the file is now lying to every future session. Do not spend a paragraph on it.

Follow the global writing rules: no em dashes, no box-drawing characters, no tables in prose output.
