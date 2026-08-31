---
name: write-in-ste
description: Rewrite a named document into ASD-STE100 Simplified Technical English, then verify it with a checker that exits non-zero on violations. Use when the user says "write this in STE", "apply Simplified Technical English", "make this document STE", "rewrite the install guide in controlled English", or asks for controlled or aerospace-style technical English for a procedure, install guide, handover document, runbook or work instruction. Applies to one document the user names. Not for chat replies, and not for code.
model: opus
---

# Write in Simplified Technical English (ASD-STE100)

Rewrite a document the user names into controlled technical English, then prove the
result mechanically. This fires on a document, never on chat.

## The one thing to get right

**Never report a document as "STE compliant".** The core of ASD-STE100 is its
approved-word dictionary, about 900 words each locked to one meaning and one part
of speech, plus about 1200 not-approved words with substitutes. That dictionary is
copyright ASD and is not bundled here, and it is not what is installed.

**A local plain-English list is installed instead** (84 entries, built 2026-08-16
from plainlanguage.gov and a set of plain-writing rules, see
`dictionary/README.md`). It catches hard words with a simpler substitute. It is
not the ASD dictionary and does not approximate it.

The checker prints which list it loaded on every run. Copy that line into the
report rather than describing it. The honest claim is:

> Passes the structural rules. Word choice was checked against the local plain
> English list, not the ASD-STE100 approved dictionary, so this document is
> plainer, not certified.

Saying more than that is the declared-but-unverified trap. Only a run loading the
official ASD list may drop the second clause, and even then only for what the
checker can mechanically see.

## Steps

**1. Settle the target and the mode. Do not guess either.**

Ask which file, and whether each section is PROCEDURAL (steps the reader performs,
20-word sentence limit) or DESCRIPTIVE (explanation, 25-word limit). A document is
usually mixed; handle it section by section rather than picking one mode for the
whole file. If the document is a set of numbered steps, it is procedural.

**2. Read the whole document before changing a line.**

Note anything that must survive verbatim: identifiers, file paths, commands, UI
labels, quoted regulation text, product names. STE governs prose, not these.

**3. Rewrite, applying these rules.**

- One instruction per sentence. Procedural sentences stop at 20 words, descriptive at 25.
- Six sentences per paragraph, one topic per paragraph.
- Active voice. Name the actor. Passive is allowed only in descriptive text where the actor is genuinely unknown.
- Allowed verb forms only: infinitive, imperative, simple present, simple past, simple future, and the past participle used as an adjective.
- No perfect tenses. "The pump has been removed" becomes "You removed the pump".
- No "-ing" forms unless the word is a technical noun or a modifier inside a technical noun phrase.
- Noun clusters stop at three words. Break longer ones with "of" or "the".
- One word, one meaning. Pick "make sure" and never rotate through "verify", "check", "confirm", "ensure".
- Keep articles, subjects and verbs. Do not drop words for brevity.
- Say what to do, not what to avoid.
- Put a warning or caution BEFORE the step it protects, never after.
- Use a vertical list for anything with more than two conditions or parts.

**4. Verify. This step is not optional and its output goes in the report.**

```
python3 ~/.claude/skills/write-in-ste/ste_check.py <file> --mode procedural
python3 ~/.claude/skills/write-in-ste/ste_check.py <file> --mode descriptive
```

Exit 0 is clean, 1 means findings, 2 is a usage error. Add `--strict` to fail on
advisory findings too, `--json` for machine output.

Findings come in bands. **hard** is mechanical and near certain: sentence length,
paragraph length, perfect tenses, passive voice in procedures. **advisory** is a
heuristic that can over-fire: "-ing" forms, noun clusters, multiple instructions.
Read an advisory finding before obeying it. If it fires on correct text, that is a
bug in the rule, and the fix belongs in `ste_check.py` or in
`dictionary/ing_allow.txt`, not in the document.

**5. Report honestly.**

Give the exit code, the hard and advisory counts, and the sentence from the boxed
warning above. Name any advisory finding you deliberately left alone, and why.

## What this skill must not do

- **Do not touch code, commands, paths, or identifiers.** The checker already
  excludes fenced blocks, inline spans, headings, tables, link targets and YAML
  frontmatter. Your rewrite must respect the same boundary.
- **Do not rewrite quoted external text**, such as regulation wording, a vendor
  error message, or a customer's own words. Quote it and leave it.
- **Do not rename a technical term to a simpler one.** STE simplifies grammar and
  general vocabulary; it never invents a new name for a part, a field or a service.
  If a term is genuinely ambiguous, flag it, do not silently swap it.
- **Do not apply this to chat.** These rules govern a document. A conversational
  reply follows the same spirit without the sentence counter, and forcing the full
  rule set on chat makes the reply stilted rather than clear.

## Voice

Procedural STE is imperative ("Remove the pump"), so it has no first person and
does not collide with a first-person voice. Where a document goes out under one
person's name, descriptive sections stay in the first person singular: "I measured",
never "we measured".

## Files

- `ste_check.py` - the checker. `--selftest` runs a built-in two-way control.
- `test_ste_check.py` - 60 checks, contrast pair per rule.
- `dictionary/not_approved.txt` - the loaded word list. Its `# name:` line is what
  the checker prints, so a list that changes cannot silently keep the old label.
- `dictionary/README.md` - what is installed, and how to swap in the official list.
- `dictionary/ing_allow.txt` - technical "-ing" nouns that are legitimate. Extend it.

## Sources

**Structural rules:** ASD-STE100 Issue 9, January 2025, 53 writing rules. The
specification is a free copy from https://www.asd-ste100.org/ after a short form,
which is a human step nobody has taken, so the approved-word dictionary is not
here.

**The installed word list:** plainlanguage.gov (GSA), a US federal work released
under CC0 1.0, filtered against a corpus of real technical documents and combined
with a list of words that mark machine-written prose. Nothing in it is copied from
ASD-STE100. How the list was built, and how to rebuild it for your own writing, is
in `dictionary/README.md`.
