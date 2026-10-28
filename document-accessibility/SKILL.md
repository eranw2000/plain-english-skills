---
name: document-accessibility
description: "Make, check or fix a Word, PowerPoint, Excel or PDF document so people who use a screen reader, a keyboard or high contrast can use it, aligned with Israeli Standard SI 5568 Part 2 (ת״י 5568 חלק 2) and the WCAG AA rules that apply to documents. Runs a checker over the .docx or .pptx XML (title, language, Hebrew language, real headings, alt text, table header rows, link text, slide titles) that exits non-zero on a barrier, then walks the manual checks (reading order, contrast, the exported PDF). Use when the user says 'make this document accessible', 'check accessibility', 'נגישות', 'is this deck accessible', 'SI 5568', 'תקן 5568', 'accessible PDF', 'alt text', or before a document goes to a public body or a client that must comply. Not legal advice, and not for web pages."
model: opus
---

# Document accessibility

A document is accessible when its STRUCTURE is right, not when it looks right. A screen
reader does not see bold text or a big font: it sees headings, lists, tables, alt text,
a title and a language, or it sees nothing. So the work is to give the file that
structure, then prove it with a check that can fail.

The target is Israeli Standard SI 5568 Part 2 (digital documents) and the WCAG AA rules
that apply to a document. Before you state which edition, date or legal duty applies,
read the Standards Institution of Israel page and the current regulation in the same
turn: an edition or an exemption written from memory is a claim, and the reader will act
on it. Technical conformance and legal compliance are two different answers; this skill
covers technical conformance.

## 1. Know what you are holding

Name: the format (.docx, .pptx, .xlsx, .pdf), the languages (Hebrew, English, both), who
reads it and where it is published, whether it has charts, diagrams or complex tables,
and whether a PDF will be made from it. Do not stop to ask what the file itself answers.

## 2. Run the checker (Word and PowerPoint)

```
python3 -I ~/.claude/skills/document-accessibility/scripts/check_doc_a11y.py "<file>" [--lang he-IL]
```

It reads the XML directly (no Word needed), prints `FAIL` lines (barriers) and `WARN`
lines (a person must look), and ends with the list of checks a person makes. Exit 0
means no FAIL, 1 means at least one FAIL, 2 means it could not read the file. Pass
`--lang he-IL` when the document must declare Hebrew. Rules and how to fix each one:
read `~/.claude/skills/document-accessibility/reference/formats.md`.

A clean run is NOT a pass. It covers what a script can read; step 4 covers the rest.

For Excel and PDF, work by hand from `reference/formats.md`.

## 3. Build or fix in this order

Structure before looks, and never trade structure for looks:

1. Title property, and the document language (Hebrew: `he-IL`, set as the
   document default, not only on some runs).
2. Real headings in order (Heading 1, then 2; never a jump from 1 to 3), real lists,
   real tables with the first row marked as the header row.
3. Alt text on every meaningful image, chart and diagram, saying what it SHOWS or what
   it is FOR, never its file name; decorative images marked decorative.
4. Link text that says where it goes, never "click here" or "לחץ כאן".
5. Every slide with its own title in the layout's title placeholder, not a text box.
6. Reading order, then colour and contrast, then the exported PDF on its own.

When you generate the file with python-docx or python-pptx, set these in the builder,
not afterwards by hand. Two traps to avoid: python-pptx writes the image's FILE
NAME as its alt text when none is given, and a deck built from blank layouts with text
boxes has no slide titles at all.
For a Hebrew file, set right-to-left direction on every paragraph and table, and look at
the result in Word or PowerPoint itself, since other viewers draw mixed Hebrew and English differently.

## 4. The checks a person makes

The checker prints these at the end of every run. Walk each one and write down what
you saw:

- **Reading order.** Word: content in floating text boxes or shapes. PowerPoint: the
  Reading Order pane. Visual position is not evidence.
- **Alt text that means something.** Purpose, not appearance; "image of" only when the
  fact that it is an image matters. A chart or diagram that one line cannot carry gets a
  text explanation or a data table next to it.
- **Contrast**: 4.5:1 for normal text, 3:1 for large text. Compute it with the WCAG
  contrast formula; do not trust brand colours to pass.
- **Colour alone** never carries meaning: a status, an error or a category also has a word
  or a symbol.
- **Images of text** are replaced by live text; a scan needs real text, tags and order, and
  OCR alone does not make it accessible.
- **Instructions** do not rely on shape, place, size, sound or colour ("the red button").
- **The PDF**, when one is made, is checked separately: an accessible Word file does not
  prove the PDF is. It must be tagged, with title, language, headings, tables, links and
  alt text surviving the export.

If you could not make a check (no PowerPoint on this machine, no screen reader), write
"Not verified: <check>, needs <tool or person>". Never report a check you did not run.

## 5. Report

For a review, one finding per barrier: ID, where (page, slide, table), the rule, what is
wrong, how bad, the fix, and how the fix was verified. Severity:

- **Critical**: content or a function is unavailable to assistive technology.
- **High**: a major barrier, or the same structural failure repeated.
- **Medium**: a real defect with a workaround.
- **Low**: a local improvement.

For a client the findings go to a spreadsheet or as bullets, never a pipe table in a mail.

End with one outcome:

- **PASS**: every applicable check in steps 2 and 4 was made, the checker prints no FAIL,
  and no finding of any severity is left open.
- **PASS WITH FIXES**: usable, no Critical or High finding is left, and every Medium or Low
  one still open is written down with its fix and who accepted leaving it.
- **FAIL**: significant content is unreachable, the structure or reading order is broken,
  alt text is missing at scale, a required PDF is untagged, or a required check could not
  be made.

Say what was checked, never more: "passed the checks listed here", "reading order still
needs a manual check". Never "100% accessible", "legally compliant" or "certified".

## Not for

- Web pages and apps: they need a web review against WCAG 2.1 AA.
- Whether an organisation is legally obliged: that is the current regulation and a lawyer.
