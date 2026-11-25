---
model: opus
name: question-page
description: Build the HTML explainer page that goes with a question to the user, so they can decide from the page instead of from chat text. Writes a self-contained page into the project folder with a header band (project, what it is, date and time read from the clock), what went wrong in plain words, the real text or data quoted, before/after, numbered steps, and the options as cards with the recommendation marked; opens it in the browser, screenshots it at 1280px, and looks before asking. Use before any question to the user that is not on this skill's skip list, or when the user says "explain this question", "make a page for the question", "I don't understand what you're asking". Not for a session recap and not for re-saying an answer in plain words (explain-simply).
disable-model-invocation: false
---

# Question page: one HTML page per question

A user who works on several projects at once reads a question with no context. The chat shows option labels; the page shows what the choice is about. **Read this whole file before building a page.**

## When to build a page

Check the "always a page" cases FIRST: if any one holds, build the page even when a skip case also fits.

**Always a page:** a choice that changes what a client, a user or published text sees; one that needs quoted text, data, a non-Latin script, or a before and after; a review finding or anything with a "what went wrong"; a plan or design decision; anything that deletes data or rewrites history.

**No page (ask in chat and build nothing) when any one of these holds and no "always" case does:**

- a time-tracking or other bookkeeping question (separate entry, merge or skip; which project);
- a step of another skill's own fixed flow, with options the skill defines (which reviewers, a task bucket);
- a go-ahead on what the same message just reported (merge now, push, continue or stop);
- a setting or a value (a date, a time, a name, a path, a flag);
- a re-ask of a question the user already saw.

The test behind the list: the page would only repeat the question and its option labels. Edit both lists to fit how you work.

## Steps

1. **Read the clock.** `date '+%d %b %Y, %H:%M %Z'` for local time and `date -u '+%H:%M'` for UTC. Never type a time you did not read.
2. **Copy the template** `reference/page-template.html` (beside this file) into the project's folder as `<topic>_explained.html`, never into a temporary folder that is deleted later. Fill every `{{...}}` slot and delete the sections that do not apply. No slot may stay in the file: `test -s <file> && ! grep -q '{{' <file> && echo FILLED || echo "NOT FILLED"`, and go on only on `FILLED`.
3. **Fill it with what the chat cannot carry** (the parts list below).
4. **Look at it.** Screenshot at 1280px and Read the image:

   ```sh
   <chrome> --headless=new --disable-gpu --window-size=1280,1100 --screenshot=<scratch>/<topic>.png "file://<absolute path>"
   ```

   `<chrome>` is the Chrome or Chromium program (on macOS `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`, on Windows `"C:\Program Files\Google\Chrome\Application\chrome.exe"`). Fix what looks wrong (cut-off text, an empty card, a heading that no longer matches its list) and look again.
5. **Open it** for the user (`open` on macOS, `start ""` on Windows, `xdg-open` on Linux).
6. **Ask.** The chat message says in plain words what went wrong, gives each option on its own line with the recommendation, and gives the page's absolute path. Then ask with `AskUserQuestion`, so the user answers in one keystroke.

## The parts of a page

In this order. **Always on the page:** the header band, the question as a title, and the options as cards with the pick marked. **Required whenever the question has one:** the real text or data it is about (quoted, never paraphrased), a before and after when an option changes text or output, and numbered steps when it is about a process. The rest when they help.

- **Header band (always):** `Project: <name>`, a few words on what the project is, and the time read in step 1 as `<date>, HH:MM <zone> (HH:MM UTC)`. A user running several projects must see at a glance which one the question comes from.
- **The question as a title**, then one plain sentence on why it is being asked now.
- **What went wrong**, said as it happens to the real document or person, with no function or variable names.
- **The real thing, quoted:** the text, data row or message the decision is about. Right-to-left text (Hebrew, Arabic) goes in an RTL box (`<div dir="rtl" lang="he">`), and inside an English line in `<bdi dir="rtl">`. Never paraphrase what can be quoted.
- **Before and after** with `<del>` and `<ins>`, when an option changes text or output.
- **Numbered steps**, when the question is about a process or an order of work.
- **An invented example**, labelled "Invented example" on the page itself, when real data cannot be shown.
- **Checked:** what was run to back the claims on the page, in one line.
- **The options as cards**, at most 4: `Option N: <what you do, in plain words>`, then what changes for the people who use it and what they lose. Mark the recommended card ("MY PICK") and give its reason.

## Rules for the page

- A local file in the project folder.
- Self-contained: inline CSS, no web fonts, no scripts, no links to files the user cannot open.
- Light and dark both readable (the template's `prefers-color-scheme` block); text contrast at least 4.5:1.
- Plain words: short sentences, no internal names where a sentence would do.
