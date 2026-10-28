#!/usr/bin/env python3
"""Check a .docx or .pptx for the accessibility basics a script can read.

Usage:
    python3 -I check_doc_a11y.py <file.docx|file.pptx> [--lang he-IL]

Reads the file's XML directly (standard library only) and prints one line per
problem: FAIL lines are barriers, WARN lines need a person to look. It always
ends with what it could NOT check, because a clean run here is not a pass.

Exit status: 0 no FAIL, 1 at least one FAIL, 2 the file could not be read
(not a .docx/.pptx, a Strict Open XML file, or a part it references is missing).

Vendor facts this relies on (read 2026-10-25):
- Decorative images: Microsoft Learn, Decorative class: "When the object is
  serialized out as xml, it's qualified name is adec:decorative", with a val
  attribute, "available in Office 2019 and above". Namespace measured on 114
  marks PowerPoint wrote in local files: DECORATIVE below.
- PowerPoint table header: python-pptx docs, PowerPoint UI behavior: a new
  table has <a:tblPr firstRow="1" ...>; "After setting firstRow property off
  ... The firstRow attribute is removed".
- Word table header: Word's "No Header Row Specified" is fixed with "Repeat
  Header Rows", stored as w:tblHeader in the row's w:trPr (ECMA-376 tblHeader).
- Word style inheritance: a style's w:basedOn names the style it inherits from
  (Microsoft Learn, BasedOn class).
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
DC = "http://purl.org/dc/elements/1.1/"
TABLE_URI = "http://schemas.openxmlformats.org/drawingml/2006/table"
DECORATIVE = "{http://schemas.microsoft.com/office/drawing/2017/decorative}decorative"
STRICT_PREFIX = "{http://purl.oclc.org/ooxml/"
# Word parts that hold published text or images besides the body, found through
# the document's own relationships, never by file name. Reviewer comments are
# left out: they are not part of what a reader is given.
STORY_TYPES = ("/header", "/footer", "/footnotes", "/endnotes")

HEBREW = re.compile(r"[֐-׿]")
IMAGE_NAME = re.compile(r"\.(png|jpe?g|gif|bmp|tiff?|svg|emf|wmf|webp)$", re.I)
URL = re.compile(r"^(https?://|www\.)", re.I)
# Link texts that say nothing about where the link goes, in English and Hebrew.
VAGUE = {
    "click here", "here", "more", "read more", "link", "this link", "click",
    "לחץ כאן", "לחצו כאן", "כאן", "קישור", "עוד", "למידע נוסף", "קרא עוד",
}
# A short paragraph that is all bold, or at least this size, looks like a heading.
FAKE_HEADING_MAX_CHARS = 80
FAKE_HEADING_MIN_HALF_POINTS = 28  # 14 pt
# A document this long with no real heading has no structure to navigate by.
MIN_PARAGRAPHS_FOR_HEADINGS = 15

NOT_CHECKED = [
    "reading order (Word: text boxes and floating shapes; PowerPoint: the Reading Order pane)",
    "whether each alt text describes the PURPOSE of the image",
    "colour contrast (4.5:1 normal text, 3:1 large text) and meaning carried by colour alone",
    "images of text, and instructions that rely on shape, place or colour",
    "any PDF exported from this file: check the PDF on its own",
]


class Unreadable(ValueError):
    """The file cannot be judged: say so, never report a clean result."""


class Report:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, str]] = []

    def fail(self, rule: str, msg: str) -> None:
        self.lines.append(("FAIL", rule, msg))

    def warn(self, rule: str, msg: str) -> None:
        self.lines.append(("WARN", rule, msg))

    @property
    def failed(self) -> bool:
        return any(kind == "FAIL" for kind, _, _ in self.lines)


def q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def read_xml(z: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(z.read(name))
    except KeyError:
        return None


def need_xml(z: zipfile.ZipFile, name: str, why: str) -> ET.Element:
    root = read_xml(z, name)
    if root is None:
        raise Unreadable(f"{why} '{name}' is referenced but missing")
    return root


def refuse_strict(root: ET.Element) -> None:
    if root.tag.startswith(STRICT_PREFIX):
        raise Unreadable("Strict Open XML is not supported; save it as a normal .docx/.pptx")


def text_of(el: ET.Element, ns: str) -> str:
    return "".join(t.text or "" for t in el.iter(q(ns, "t")))


def is_on(value: str | None) -> bool:
    # An OOXML boolean: absent value on a present element means on.
    return value is None or value.lower() in ("1", "true", "on")


def is_decorative(container: ET.Element) -> bool:
    for el in container.iter(DECORATIVE):
        if el.get("val", "").lower() in ("1", "true"):
            return True
    return False


def rels_of(z: zipfile.ZipFile, part: str) -> list[tuple[str, str, str]]:
    """(id, type, resolved target) for each internal relationship of a part."""
    folder, name = posixpath.split(part)
    root = read_xml(z, posixpath.join(folder, "_rels", name + ".rels"))
    out = []
    if root is None:
        return out
    for r in root.iter(q(PKG_REL, "Relationship")):
        if r.get("TargetMode") == "External":
            continue
        t = r.get("Target", "")
        target = t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join(folder, t))
        out.append((r.get("Id", ""), r.get("Type", ""), target))
    return out


def check_title(z: zipfile.ZipFile, rep: Report) -> None:
    core = read_xml(z, "docProps/core.xml")
    title = core.find(q(DC, "title")) if core is not None else None
    if title is None or not (title.text or "").strip():
        rep.fail("title", "the file has no Title property (File > Info > Title)")


def check_alt(name: str, descr: str | None, decorative: bool, where: str, rep: Report) -> None:
    if decorative:
        return
    text = (descr or "").strip()
    if not text:
        rep.fail("alt-text", f"{where}: image '{name}' has no alt text and is not marked decorative")
    elif IMAGE_NAME.search(text):
        rep.fail("alt-text-filename", f"{where}: image '{name}' alt text is a file name ('{text}')")


def check_link(text: str, where: str, rep: Report) -> None:
    plain = re.sub(r"[\s.,:;!?()\"']+", " ", text).strip().lower()
    if not plain:
        rep.fail("link-text", f"{where}: a link has no text")
    elif plain in VAGUE:
        rep.fail("link-text", f"{where}: link text '{text.strip()}' does not say where it goes")
    elif URL.match(text.strip()):
        rep.warn("link-bare-url", f"{where}: link text is a bare address ('{text.strip()[:60]}')")


def check_default_lang(defaults: set[str], expected: str | None, rep: Report) -> None:
    if not defaults:
        rep.fail("language", "no document language is set")
    if expected and expected.lower() not in {v.lower() for v in defaults}:
        rep.fail("language", f"expected language {expected}, found {sorted(defaults) or 'none'}")


def is_he(value: str | None) -> bool:
    return bool(value) and value.lower().startswith("he")


# --- Word ------------------------------------------------------------------


class WordStyles:
    """Paragraph and run styles with their basedOn chain resolved."""

    def __init__(self, styles: ET.Element | None) -> None:
        self.by_id: dict[str, ET.Element] = {}
        self.defaults_lang: dict[str, str] = {}
        if styles is None:
            return
        for st in styles.iter(q(W, "style")):
            self.by_id[st.get(q(W, "styleId"), "")] = st
        for lang in styles.iterfind(f".//{q(W, 'docDefaults')}//{q(W, 'lang')}"):
            for attr in ("val", "bidi"):
                if lang.get(q(W, attr)):
                    self.defaults_lang[attr] = lang.get(q(W, attr))

    def chain(self, sid: str):
        seen = set()
        while sid and sid not in seen and sid in self.by_id:
            seen.add(sid)
            st = self.by_id[sid]
            yield st
            based = st.find(q(W, "basedOn"))
            sid = based.get(q(W, "val"), "") if based is not None else ""

    def heading_level(self, sid: str) -> int | None:
        for st in self.chain(sid):
            name_el = st.find(q(W, "name"))
            name = (name_el.get(q(W, "val"), "") if name_el is not None else "").lower()
            m = re.fullmatch(r"heading ([1-9])", name)
            if m:
                return int(m.group(1))
            lvl = st.find(f"{q(W, 'pPr')}/{q(W, 'outlineLvl')}")
            val = lvl.get(q(W, "val"), "") if lvl is not None else ""
            if val.isdigit():
                return int(val) + 1 if int(val) < 9 else None
        return None

    def style_lang(self, sid: str, attr: str) -> str | None:
        for st in self.chain(sid):
            lang = st.find(f"{q(W, 'rPr')}/{q(W, 'lang')}")
            if lang is not None and lang.get(q(W, attr)):
                return lang.get(q(W, attr))
        return None


def run_lang(r: ET.Element, para_style: str, styles: WordStyles, attr: str) -> str | None:
    """The language a run's text gets for one attribute (val or bidi): the run's
    own rPr, then its character style, then the paragraph style, then defaults."""
    rpr = r.find(q(W, "rPr"))
    if rpr is not None:
        lang = rpr.find(q(W, "lang"))
        if lang is not None and lang.get(q(W, attr)):
            return lang.get(q(W, attr))
        rs = rpr.find(q(W, "rStyle"))
        if rs is not None:
            v = styles.style_lang(rs.get(q(W, "val"), ""), attr)
            if v:
                return v
    if para_style:
        v = styles.style_lang(para_style, attr)
        if v:
            return v
    return styles.defaults_lang.get(attr)


def table_rows(tbl: ET.Element) -> list[ET.Element]:
    """The table's own rows, including rows wrapped in a content control or
    custom XML, but never the rows of a nested table."""
    rows: list[ET.Element] = []

    def walk(el: ET.Element) -> None:
        for child in el:
            if child.tag == q(W, "tr"):
                rows.append(child)
            elif child.tag in (q(W, "sdt"), q(W, "sdtContent"), q(W, "customXml")):
                walk(child)

    walk(tbl)
    return rows


def run_is_bold(r: ET.Element) -> bool:
    b = r.find(f"{q(W, 'rPr')}/{q(W, 'b')}")
    return b is not None and is_on(b.get(q(W, "val")))


def run_half_points(r: ET.Element) -> int:
    sz = r.find(f"{q(W, 'rPr')}/{q(W, 'sz')}")
    val = sz.get(q(W, "val"), "") if sz is not None else ""
    return int(val) if val.isdigit() else 0


def para_style(p: ET.Element) -> str:
    ps = p.find(f"{q(W, 'pPr')}/{q(W, 'pStyle')}")
    return ps.get(q(W, "val"), "") if ps is not None else ""


def check_docx(z: zipfile.ZipFile, expected_lang: str | None, rep: Report) -> None:
    doc = need_xml(z, "word/document.xml", "the main document")
    refuse_strict(doc)
    styles = WordStyles(read_xml(z, "word/styles.xml"))
    check_title(z, rep)
    check_default_lang(set(styles.defaults_lang.values()), expected_lang, rep)

    # Every story part the document links to: headers, footers, footnotes, endnotes.
    stories = [("word/document.xml", doc)]
    for _, rtype, target in rels_of(z, "word/document.xml"):
        if rtype.endswith(STORY_TYPES):
            stories.append((target, need_xml(z, target, "a header, footer or note part")))

    # Hebrew text must reach a Hebrew language through its own run, its styles
    # or the defaults; a Hebrew style nobody uses does not count.
    bare_hebrew = 0
    first_bare = ""
    for part, root in stories:
        for p in root.iter(q(W, "p")):
            ps = para_style(p)
            for r in p.iter(q(W, "r")):
                txt = text_of(r, W)
                if HEBREW.search(txt) and not (is_he(run_lang(r, ps, styles, "bidi"))
                                               or is_he(run_lang(r, ps, styles, "val"))):
                    bare_hebrew += 1
                    first_bare = first_bare or f"{part}: '{txt.strip()[:30]}'"
    if bare_hebrew:
        rep.fail("language-hebrew", f"{bare_hebrew} Hebrew text run(s) have no Hebrew language (he-IL), first {first_bare}")

    # Headings: real heading styles (through basedOn), in order, and lookalikes.
    body = doc.find(q(W, "body"))
    paras = list(body.iter(q(W, "p"))) if body is not None else []
    # Bold, short text in a table cell is a cell, not a heading.
    in_table = {id(p) for tbl in (body.iter(q(W, "tbl")) if body is not None else []) for p in tbl.iter(q(W, "p"))}
    with_text = 0
    seen: list[int] = []
    for i, p in enumerate(paras, 1):
        txt = text_of(p, W).strip()
        if not txt or id(p) in in_table:
            continue
        with_text += 1
        own = p.find(f"{q(W, 'pPr')}/{q(W, 'outlineLvl')}")
        own_val = own.get(q(W, "val"), "") if own is not None else ""
        if own_val.isdigit():
            lvl = int(own_val) + 1 if int(own_val) < 9 else None
        else:
            lvl = styles.heading_level(para_style(p))
        if lvl is not None:
            if seen and lvl > seen[-1] + 1:
                rep.fail("heading-skip", f"paragraph {i}: Heading {seen[-1]} is followed by Heading {lvl} ('{txt[:40]}')")
            seen.append(lvl)
            continue
        runs = [r for r in p.iter(q(W, "r")) if text_of(r, W).strip()]
        if runs and len(txt) <= FAKE_HEADING_MAX_CHARS:
            if all(run_is_bold(r) for r in runs) or min(run_half_points(r) for r in runs) >= FAKE_HEADING_MIN_HALF_POINTS:
                rep.warn("fake-heading", f"paragraph {i}: '{txt[:40]}' looks like a heading but uses no heading style")
    if with_text >= MIN_PARAGRAPHS_FOR_HEADINGS and not seen:
        rep.fail("headings-none", f"{with_text} paragraphs and no real heading (use Heading 1, 2, ...)")

    # Images, in every story part.
    for part, root in stories:
        for holder in list(root.iter(q(WP, "inline"))) + list(root.iter(q(WP, "anchor"))):
            pr = holder.find(q(WP, "docPr"))
            if pr is not None:
                check_alt(pr.get("name", "?"), pr.get("descr"), is_decorative(pr), part, rep)

    # Tables: the first row must be marked as a header row.
    for n, tbl in enumerate(doc.iter(q(W, "tbl")), 1):
        rows = table_rows(tbl)
        if len(rows) < 2:
            continue
        hdr = rows[0].find(f"{q(W, 'trPr')}/{q(W, 'tblHeader')}")
        if hdr is None or not is_on(hdr.get(q(W, "val"))):
            rep.fail("table-header", f"table {n}: first row is not a header row (Table Properties > Row > Repeat as header row)")

    for part, root in stories:
        for n, link in enumerate(root.iter(q(W, "hyperlink")), 1):
            check_link(text_of(link, W), f"{part} link {n}", rep)


# --- PowerPoint ------------------------------------------------------------


def slide_parts(z: zipfile.ZipFile, pres: ET.Element) -> list[str]:
    target = {rid: t for rid, _, t in rels_of(z, "ppt/presentation.xml")}
    out = []
    for sid in pres.iter(q(P, "sldId")):
        rid = sid.get(q(R, "id"), "")
        if rid not in target:
            raise Unreadable(f"slide relationship '{rid}' does not resolve")
        out.append(target[rid])
    return out


def link_groups(root: ET.Element):
    """Each logical PowerPoint link: neighbouring runs of one paragraph that
    share the same hlinkClick target, joined, so a split link is read whole."""
    for para in root.iter(q(A, "p")):
        rid, parts = None, []
        for r in para.iter(q(A, "r")):
            link = r.find(f"{q(A, 'rPr')}/{q(A, 'hlinkClick')}")
            this = link.get(q(R, "id"), "") if link is not None else None
            if this != rid and parts:
                yield "".join(parts)
                parts = []
            rid = this
            if this is not None:
                parts.append(text_of(r, A))
        if parts:
            yield "".join(parts)


def check_pptx(z: zipfile.ZipFile, expected_lang: str | None, rep: Report) -> None:
    pres = need_xml(z, "ppt/presentation.xml", "the presentation")
    refuse_strict(pres)
    check_title(z, rep)
    slides = slide_parts(z, pres)

    defaults: set[str] = set()
    for d in pres.iterfind(f".//{q(P, 'defaultTextStyle')}//{q(A, 'defRPr')}"):
        if d.get("lang"):
            defaults.add(d.get("lang"))
    check_default_lang(defaults, expected_lang, rep)
    default_he = any(is_he(v) for v in defaults)

    bare_hebrew = 0
    titles: dict[str, int] = {}
    for n, part in enumerate(slides, 1):
        root = need_xml(z, part, "slide")
        refuse_strict(root)
        where = f"slide {n}"
        for r in root.iter(q(A, "r")):
            rpr = r.find(q(A, "rPr"))
            own = (rpr.get("lang") or rpr.get("altLang")) if rpr is not None else None
            if HEBREW.search(text_of(r, A)) and not (is_he(own) or (own is None and default_he)):
                bare_hebrew += 1

        title = ""
        for sp in root.iter(q(P, "sp")):
            ph = sp.find(f"{q(P, 'nvSpPr')}/{q(P, 'nvPr')}/{q(P, 'ph')}")
            if ph is not None and ph.get("type") in ("title", "ctrTitle"):
                title = text_of(sp, A).strip()
                break
        if not title:
            rep.fail("slide-title", f"{where}: no slide title (use the layout's title placeholder)")
        else:
            if title in titles:
                rep.warn("slide-title-duplicate", f"{where}: same title as slide {titles[title]} ('{title[:40]}')")
            titles.setdefault(title, n)

        for pic in root.iter(q(P, "pic")):
            pr = pic.find(f"{q(P, 'nvPicPr')}/{q(P, 'cNvPr')}")
            if pr is not None:
                check_alt(pr.get("name", "?"), pr.get("descr"), is_decorative(pr), where, rep)
        for gf in root.iter(q(P, "graphicFrame")):
            data = gf.find(f"{q(A, 'graphic')}/{q(A, 'graphicData')}")
            pr = gf.find(f"{q(P, 'nvGraphicFramePr')}/{q(P, 'cNvPr')}")
            if data is not None and data.get("uri") == TABLE_URI:
                tbl_pr = data.find(f"{q(A, 'tbl')}/{q(A, 'tblPr')}")
                if tbl_pr is None or not tbl_pr.get("firstRow") or not is_on(tbl_pr.get("firstRow")):
                    rep.fail("table-header", f"{where}: table '{pr.get('name', '?') if pr is not None else '?'}' has no header row (Table Design > Header Row)")
            elif pr is not None:
                check_alt(pr.get("name", "?"), pr.get("descr"), is_decorative(pr), where, rep)

        for k, text in enumerate(link_groups(root), 1):
            check_link(text, f"{where} link {k}", rep)

    if bare_hebrew:
        rep.fail("language-hebrew", f"{bare_hebrew} Hebrew text run(s) have no Hebrew language (he-IL)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--lang", help="the language the document must declare, such as he-IL")
    args = ap.parse_args(argv)
    rep = Report()
    try:
        with zipfile.ZipFile(args.path) as z:
            names = set(z.namelist())
            if "word/document.xml" in names:
                kind = "docx"
                check_docx(z, args.lang, rep)
            elif "ppt/presentation.xml" in names:
                kind = "pptx"
                check_pptx(z, args.lang, rep)
            else:
                print(f"CANNOT READ {args.path}: not a .docx or .pptx (Excel and PDF are checked by hand)")
                return 2
    except (OSError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        print(f"CANNOT READ {args.path}: {type(exc).__name__}: {exc}")
        return 2

    for kind_, rule, msg in rep.lines:
        print(f"{kind_} {rule}: {msg}")
    fails = sum(1 for k, _, _ in rep.lines if k == "FAIL")
    warns = len(rep.lines) - fails
    print(f"RESULT {kind}: {fails} FAIL, {warns} WARN")
    print("NOT CHECKED BY THIS SCRIPT (a person must look):")
    for item in NOT_CHECKED:
        print(f"  - {item}")
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
