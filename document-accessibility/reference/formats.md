# Rules and fixes, per format

## The checker's rules

Each line the checker prints starts with FAIL or WARN and a rule name.

- **title** (FAIL): the file's Title property is empty. Word and PowerPoint: File > Info >
  Title. python-docx / python-pptx: `core_properties.title = "..."`. A PDF viewer shows
  this title, so it must name the topic, not the file.
- **language** (FAIL): no document default language. Word keeps it in
  `w:docDefaults/w:rPrDefault/w:rPr/w:lang` in `styles.xml` (`w:val` for Latin text,
  `w:bidi` for Hebrew and Arabic); PowerPoint in `a:defRPr lang` under the presentation's
  `defaultTextStyle`. With `--lang he-IL` it also fails when that value is missing.
- **language-hebrew** (FAIL): the text has Hebrew letters and no `he-IL` anywhere. Google
  Docs exports often say only `en`. Set `w:bidi="he-IL"` in the defaults (Word) or
  `lang="he-IL"` on the Hebrew runs and the default (PowerPoint).
- **headings-none** (FAIL): 15 or more paragraphs and not one real heading style.
- **heading-skip** (FAIL): a level jumps (Heading 1 then Heading 3).
- **fake-heading** (WARN): a short paragraph that is all bold or 14 pt and up, with no
  heading style. Usually a heading in disguise; make it one. Bold text inside a table
  cell is not reported.
- **alt-text** (FAIL): an image, chart or diagram with no alt text that is not marked
  decorative. Word: `wp:docPr descr`; PowerPoint: `p:cNvPr descr`.
- **alt-text-filename** (FAIL): the alt text is a file name (`chart.png`). python-pptx
  writes the file name when you give none, so always set it.
- **table-header** (FAIL): Word: the first row lacks "Repeat as header row" (`w:tblHeader`
  in the row's `w:trPr`); PowerPoint: Header Row is off (`a:tblPr firstRow`).
- **link-text** (FAIL): link text says nothing ("click here", "כאן", "לחץ כאן", "more") or
  is empty. **link-bare-url** (WARN): the text is the raw address; name the page instead.
- **slide-title** (FAIL): a slide with no text in a title placeholder. A text box styled to
  look like a title does not count. **slide-title-duplicate** (WARN): two slides share a
  title; make each one say what is different.

A decorative image is marked with `adec:decorative val="1"` inside the image's
`cNvPr`/`docPr` (Office 2019 and later); the checker accepts that in place of alt text.

## Word

- Built-in heading styles, list styles and real tables; no layout tables.
- No essential text in floating text boxes; a screen reader may skip or misplace it.
- Spacing by paragraph spacing, not blank lines; no manual line breaks to fake layout.
- Headers and footers hold nothing a reader needs that is not also in the body.
- Before export to PDF, run Word's Accessibility Checker; Microsoft says Word uses what it
  found to tag the PDF. Windows: Save As > PDF > Options > "Document structure tags for
  accessibility". Mac (Office 2016 and later): Save As > PDF > "Best for electronic
  distribution and accessibility", which Microsoft says "sends the document over to a
  secure Microsoft service over the internet for conversion": for a client's confidential
  file, ask before using it. Print to PDF does not keep the tags. (Microsoft Support,
  "Create accessible PDFs", read 2026-10-25.)

## PowerPoint

- Build from layouts that have a title placeholder; one unique title per slide.
- Check the Reading Order pane on every slide with more than one text shape.
- Charts and diagrams: alt text plus the numbers or the steps in the slide text or notes,
  when the notes are part of what is handed out.
- Do not put essential content only in speaker notes.

## Excel

- Name every sheet for what it holds; no "Sheet1".
- Data starts at A1 or the first cell is a title row that says what follows.
- One header row per table, no merged header cells, no blank rows or columns used for
  spacing inside a table.
- Charts get alt text; colour-coded status also gets a word.
- Explain any formula a reader must understand in a note next to it.

## PDF

There is no PDF checker here yet. Until one is chosen from its own documentation, check
by hand in the viewer: tagged, Title shown in the window bar, language set, headings and
tables tagged, links work, alt text survived, text selectable, reading order sane. A PDF
printed from HTML: confirm it is tagged before calling it accessible, never assume it.

## Complex content

For a chart, diagram, dashboard or a table of many levels:

1. Say in one line what it shows (the message, not the shape).
2. Put that line in the alt text.
3. When one line cannot carry it, add a text explanation or a simple data table next to it.
4. Split a complex table into several simple ones rather than merging cells.
