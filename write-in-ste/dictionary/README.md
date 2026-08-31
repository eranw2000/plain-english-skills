# The word list

`ste_check.py` verifies the structural rules on its own. Word choice needs a list,
and which list is loaded decides what a clean run is allowed to claim.

**Installed today: a local plain-English list, NOT the ASD-STE100 dictionary.**

## Why not the real one

The ASD-STE100 approved-word dictionary is about 900 approved words, each locked
to one meaning and one part of speech, plus about 1200 not-approved words with
substitutes. It is copyright ASD, Brussels. A free copy of the specification is
available, but only by sending a request form to `stemg@asd-ste100.org`, and no
one has sent it. It is not downloadable and nothing here reproduces it.

## What is installed instead

`not_approved.txt`, 84 entries, built 2026-08-16 from two sources that carry no
copyright bar:

- **plainlanguage.gov**, the US federal plain-language guidance, fetched from the
  GSA's own repository. A US government work, and additionally released under
  CC0 1.0 by that repository's licence.
- **A list of words that mark machine-written prose**, the kind a reader notices
  before they notice the content: "delve", "showcase", "testament", "underscore"
  used as a verb, "seamlessly", "crucial".

The plainlanguage.gov rows were filtered against a corpus of real technical
documents, and a row was kept only if it appears in at least one of them. That
filter caught about twenty entries that would have fired on correct technical
writing, because the source list was written for federal office prose: it wants
"interface" changed to "meet" and "parameters" to "limits".

The machine-prose rows were kept regardless of frequency. They score near zero in
a corpus that a writing guard already stops at write time, and deleting a rule
because its guard works would be the wrong reading of a zero.

To rebuild the list for your own writing, run the two sources through the same
filter: keep a plainlanguage.gov row only when your own documents contain the word
it flags, and record why you dropped each one.

## The `# name:` line is load-bearing

The file carries a line like:

```
# name: Plain English (local), 84 entries, NOT ASD-STE100
```

The checker reads it and prints it on every run. Without it, a locally-built list
and the official one look identical in the output, which is the false-compliance
problem moved rather than fixed. **If you change the list, change that line.** A
list with no name reports as `unnamed list (N entries)`, which is ugly on purpose.

## Format

One entry per line. `bad = substitute`, or a bare word to flag with no suggestion.
Text after `#` is a comment. Multi-word phrases work and are matched against the
sentence, so `in order to = to` fires correctly.

```
ensure = make sure
in order to = to
commence
```

## Swapping in the official list

1. Request the free copy of ASD-STE100 Issue 9 from https://www.asd-ste100.org/.
2. **Read the copyright and reuse terms inside the document.** They are not on the
   public web pages.
3. If the terms allow it, replace `not_approved.txt` with the not-approved entries
   and set the `# name:` line to say which issue it is.
4. If the terms forbid putting the list in a repository, keep the file local and
   untracked. The checker reads it from disk and never needs it committed.

Do not build a PARTIAL copy of the official list. A document passing against 12 of
its words while the other 890 go unchecked reads as compliance and is not. That
objection does not apply to the local list installed today, because that list does
not claim to be ASD-STE100 and says so in its own name.

## ing_allow.txt

STE allows an "-ing" form when the word is a technical noun or a modifier inside a
technical noun phrase. `ing_allow.txt` is that list. The checker falls back to a
built-in default when the file is absent. Add your own domain's terms; an advisory
R5 finding on a legitimate technical noun is a gap in this file, not a defect in
the document.
