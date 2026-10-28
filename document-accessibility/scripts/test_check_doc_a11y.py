"""Tests for check_doc_a11y.py.

Run with an interpreter that has python-docx and python-pptx (they only BUILD the
fixtures; the checker itself is run with the system python3 to prove it needs
nothing but the standard library):

    python3 -m unittest test_check_doc_a11y -v

Each test builds a clean file, breaks ONE thing, and asserts that exactly that
rule fails. CONTROL builds one file with every defect, and it must fail.
"""
from __future__ import annotations

import io
import os
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from lxml import etree
from pptx import Presentation
from pptx.util import Inches

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "check_doc_a11y.py"
SYSTEM_PY = "/usr/bin/python3"
DECOR_NS = "http://schemas.microsoft.com/office/drawing/2017/decorative"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def mark_decorative(cnvpr, ns: str = DECOR_NS) -> None:
    ext_lst = etree.SubElement(cnvpr, f"{{{A_NS}}}extLst")
    ext = etree.SubElement(ext_lst, f"{{{A_NS}}}ext", uri="{C183D7F6-B498-43B3-948B-1728B52AA6E4}")
    etree.SubElement(ext, f"{{{ns}}}decorative", val="1")


def add_link(paragraph, url: str, text: str) -> None:
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def build_docx(path: Path, breaks: set[str] = frozenset(), hebrew: bool = False) -> None:
    doc = Document()
    if "no_title" not in breaks:
        doc.core_properties.title = "Quarterly report"
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    rpr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    for old in rpr.findall(qn("w:lang")):
        rpr.remove(old)
    if "no_lang" not in breaks:
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "en-US")
        lang.set(qn("w:bidi"), "he-IL" if hebrew and "hebrew_no_he" not in breaks else "ar-SA")
        rpr.append(lang)

    doc.add_heading("Summary", level=1)
    doc.add_paragraph("שלום, זה דוח." if hebrew else "This is the report.")
    doc.add_heading("Details", level=3 if "heading_skip" in breaks else 2)
    for i in range(16):
        doc.add_paragraph(f"Line {i} of the details, long enough to be ordinary body text.")
    if "fake_heading" in breaks:
        doc.add_paragraph().add_run("Looks like a heading").bold = True

    doc.add_picture(io.BytesIO(png()))
    pr = doc.inline_shapes[-1]._inline.docPr
    if "alt_missing" in breaks:
        pass
    elif "alt_filename" in breaks:
        pr.set("descr", "chart.png")
    elif "decorative" in breaks:
        mark_decorative(pr)
    elif "decorative_wrong_ns" in breaks:
        mark_decorative(pr, "urn:example:custom")
    else:
        pr.set("descr", "Sales rose each quarter, from 10 to 40")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "Name", "Score"
    table.cell(1, 0).text, table.cell(1, 1).text = "Dana", "90"
    for cell in table.rows[0].cells:
        cell.paragraphs[0].runs[0].bold = True
    if "table_no_header" not in breaks:
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))

    text = "click here" if "link_vague" in breaks else "https://example.com/a" if "link_url" in breaks else "the course page"
    add_link(doc.add_paragraph("See "), "https://example.com/a", text)
    doc.save(path)


def build_pptx(path: Path, breaks: set[str] = frozenset(), hebrew: bool = False) -> None:
    prs = Presentation()
    if "no_title" not in breaks:
        prs.core_properties.title = "Course overview"
    root = prs.part._element
    for d in root.iter(f"{{{A_NS}}}defRPr"):
        if "no_lang" in breaks:
            d.attrib.pop("lang", None)
        else:
            d.set("lang", "en-US")

    def slide(title: str | None):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        if title is not None:
            s.shapes.title.text = title
        else:
            s.shapes.title.text = ""
        return s

    s1 = slide("Welcome")
    box = s1.shapes.add_textbox(Inches(1), Inches(2), Inches(6), Inches(1))
    run = box.text_frame.paragraphs[0].add_run()
    run.text = "שלום לכולם" if hebrew else "Hello everyone"
    if hebrew and "hebrew_no_he" not in breaks:
        run._r.get_or_add_rPr().set("lang", "he-IL")
    if "no_lang" in breaks:
        for el in s1.shapes._spTree.iter():
            el.attrib.pop("lang", None)

    s2 = slide(None if "no_slide_title" in breaks else "Welcome" if "dup_title" in breaks else "Results")
    pic = s2.shapes.add_picture(io.BytesIO(png()), Inches(1), Inches(2))
    pr = pic._element.nvPicPr.cNvPr
    if "alt_default" in breaks:
        pass  # whatever python-pptx wrote: the file name
    elif "alt_missing" in breaks:
        pr.attrib.pop("descr", None)
    elif "decorative" in breaks:
        pr.attrib.pop("descr", None)
        mark_decorative(pr)
    else:
        pr.set("descr", "Scores went up in every class")

    s3 = slide("Scores")
    table = s3.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
    table.cell(0, 0).text, table.cell(0, 1).text = "Class", "Score"
    if "table_no_header" in breaks:
        table.first_row = False
    box = s3.shapes.add_textbox(Inches(1), Inches(4), Inches(6), Inches(1))
    link = box.text_frame.paragraphs[0].add_run()
    link.text = "click here" if "link_vague" in breaks else "cl" if "link_split" in breaks else "the course page"
    link.hyperlink.address = "https://example.com/a"
    if "link_split" in breaks:
        rest = box.text_frame.paragraphs[0].add_run()
        rest.text = "ick here"
        rest.hyperlink.address = "https://example.com/a"
        # Both pieces point at the same relationship, as one link split by an edit.
        rid = link._r.rPr.find(f"{{{A_NS}}}hlinkClick").get(qn("r:id"))
        rest._r.rPr.find(f"{{{A_NS}}}hlinkClick").set(qn("r:id"), rid)
    prs.save(path)


def run_checker(path: Path, *args: str) -> tuple[int, str]:
    out = subprocess.run([SYSTEM_PY, "-I", str(CHECKER), str(path), *args], capture_output=True, text=True)
    return out.returncode, out.stdout + out.stderr


def failed_rules(output: str) -> set[str]:
    return {line.split()[1].rstrip(":") for line in output.splitlines() if line.startswith("FAIL ")}


def warned_rules(output: str) -> set[str]:
    return {line.split()[1].rstrip(":") for line in output.splitlines() if line.startswith("WARN ")}


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def docx(self, *breaks: str, hebrew: bool = False, lang: str | None = None) -> tuple[int, str]:
        p = self.dir / "t.docx"
        build_docx(p, set(breaks), hebrew)
        return run_checker(p, *(["--lang", lang] if lang else []))

    def pptx(self, *breaks: str, hebrew: bool = False, lang: str | None = None) -> tuple[int, str]:
        p = self.dir / "t.pptx"
        build_pptx(p, set(breaks), hebrew)
        return run_checker(p, *(["--lang", lang] if lang else []))

    def assertOnlyFails(self, result: tuple[int, str], rule: str) -> None:
        code, out = result
        self.assertEqual(code, 1, out)
        self.assertEqual(failed_rules(out), {rule}, out)


class WordTests(Base):
    def test_clean_file_passes(self):
        code, out = self.docx()
        self.assertEqual(code, 0, out)
        self.assertEqual(failed_rules(out), set(), out)
        self.assertIn("NOT CHECKED BY THIS SCRIPT", out)

    def test_clean_hebrew_file_passes_with_lang(self):
        code, out = self.docx(hebrew=True, lang="he-IL")
        self.assertEqual(code, 0, out)

    def test_no_title(self):
        self.assertOnlyFails(self.docx("no_title"), "title")

    def test_no_language(self):
        self.assertOnlyFails(self.docx("no_lang"), "language")

    def test_hebrew_text_without_hebrew_language(self):
        self.assertOnlyFails(self.docx("hebrew_no_he", hebrew=True), "language-hebrew")

    def test_wrong_expected_language(self):
        self.assertOnlyFails(self.docx(lang="he-IL"), "language")

    def test_heading_level_skipped(self):
        self.assertOnlyFails(self.docx("heading_skip"), "heading-skip")

    def test_image_without_alt_text(self):
        self.assertOnlyFails(self.docx("alt_missing"), "alt-text")

    def test_alt_text_that_is_a_file_name(self):
        self.assertOnlyFails(self.docx("alt_filename"), "alt-text-filename")

    def test_decorative_image_needs_no_alt_text(self):
        code, out = self.docx("decorative")
        self.assertEqual(code, 0, out)

    def test_table_without_header_row(self):
        self.assertOnlyFails(self.docx("table_no_header"), "table-header")

    def test_vague_link_text(self):
        self.assertOnlyFails(self.docx("link_vague"), "link-text")

    def test_bare_url_link_only_warns(self):
        code, out = self.docx("link_url")
        self.assertEqual(code, 0, out)
        self.assertIn("link-bare-url", warned_rules(out), out)

    def test_bold_line_warns_as_fake_heading_but_bold_table_cells_do_not(self):
        code, out = self.docx("fake_heading")
        self.assertEqual(code, 0, out)
        self.assertEqual([l for l in out.splitlines() if l.startswith("WARN fake-heading")].__len__(), 1, out)

    def test_long_document_with_no_headings(self):
        p = self.dir / "flat.docx"
        doc = Document()
        doc.core_properties.title = "Flat"
        for i in range(20):
            doc.add_paragraph(f"Paragraph {i} of ordinary body text with no structure at all.")
        doc.save(p)
        code, out = run_checker(p)
        self.assertIn("headings-none", failed_rules(out), out)


class PowerPointTests(Base):
    def test_clean_file_passes(self):
        code, out = self.pptx()
        self.assertEqual(code, 0, out)
        self.assertEqual(failed_rules(out), set(), out)

    def test_clean_hebrew_file_passes(self):
        code, out = self.pptx(hebrew=True)
        self.assertEqual(code, 0, out)

    def test_no_title(self):
        self.assertOnlyFails(self.pptx("no_title"), "title")

    def test_no_language(self):
        self.assertOnlyFails(self.pptx("no_lang"), "language")

    def test_hebrew_text_without_hebrew_language(self):
        self.assertOnlyFails(self.pptx("hebrew_no_he", hebrew=True), "language-hebrew")

    def test_slide_without_title(self):
        self.assertOnlyFails(self.pptx("no_slide_title"), "slide-title")

    def test_duplicate_slide_title_only_warns(self):
        code, out = self.pptx("dup_title")
        self.assertEqual(code, 0, out)
        self.assertIn("slide-title-duplicate", warned_rules(out), out)

    def test_picture_without_alt_text(self):
        self.assertOnlyFails(self.pptx("alt_missing"), "alt-text")

    def test_python_pptx_default_alt_text_is_caught(self):
        # python-pptx writes the image's file name as alt text when none is given.
        self.assertOnlyFails(self.pptx("alt_default"), "alt-text-filename")

    def test_decorative_picture_needs_no_alt_text(self):
        code, out = self.pptx("decorative")
        self.assertEqual(code, 0, out)

    def test_table_without_header_row(self):
        self.assertOnlyFails(self.pptx("table_no_header"), "table-header")

    def test_vague_link_text(self):
        self.assertOnlyFails(self.pptx("link_vague"), "link-text")


def rewrite_zip(path: Path, edit) -> None:
    """Rewrite an Office file: `edit(files)` changes the {name: bytes} dict."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    edit(files)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class ReviewFindings(Base):
    """
    One test per earlier review finding: each built
    the way the finding described, each a pass the checker must refuse."""

    def test_f1_an_unused_hebrew_style_does_not_hide_bare_hebrew(self):
        p = self.dir / "f1.docx"
        build_docx(p, {"hebrew_no_he"}, hebrew=True)
        doc = Document(p)
        style = OxmlElement("w:style")
        style.set(qn("w:type"), "paragraph")
        style.set(qn("w:styleId"), "UnusedHebrew")
        name = OxmlElement("w:name")
        name.set(qn("w:val"), "Unused Hebrew")
        rpr = OxmlElement("w:rPr")
        lang = OxmlElement("w:lang")
        lang.set(qn("w:bidi"), "he-IL")
        rpr.append(lang)
        style.extend([name, rpr])
        doc.styles.element.append(style)
        doc.save(p)
        self.assertOnlyFails(run_checker(p), "language-hebrew")

    def test_f1_a_hebrew_run_tagged_english_still_fails(self):
        # The run carries its own language, and it is not Hebrew.
        p = self.dir / "f1c.docx"
        build_docx(p, {"hebrew_no_he"}, hebrew=True)
        doc = Document(p)
        for para in doc.paragraphs:
            for run in para.runs:
                if any("\u0590" <= ch <= "\u05ff" for ch in run.text):
                    lang = OxmlElement("w:lang")
                    lang.set(qn("w:val"), "en-US")
                    run._r.get_or_add_rPr().append(lang)
        doc.save(p)
        self.assertOnlyFails(run_checker(p), "language-hebrew")

    def test_f1_hebrew_in_a_used_hebrew_style_passes(self):
        p = self.dir / "f1b.docx"
        build_docx(p, {"hebrew_no_he"}, hebrew=True)
        doc = Document(p)
        style = doc.styles.add_style("HebrewBody", 1)
        style.element.get_or_add_rPr()
        lang = OxmlElement("w:lang")
        lang.set(qn("w:bidi"), "he-IL")
        style.element.rPr.append(lang)
        for para in doc.paragraphs:
            if any("֐" <= ch <= "׿" for ch in para.text):
                para.style = style
        doc.save(p)
        code, out = run_checker(p)
        self.assertEqual(code, 0, out)

    def test_f2_a_style_based_on_heading_3_is_a_heading_3(self):
        p = self.dir / "f2.docx"
        build_docx(p)
        doc = Document(p)
        style = doc.styles.add_style("Section detail", 1)
        style.base_style = doc.styles["Heading 3"]
        # The file already has Heading 1 then Heading 2; put the derived style
        # straight after the first Heading 1 so it jumps 1 -> 3.
        first_h1 = next(x for x in doc.paragraphs if x.style.name == "Heading 1")
        new = first_h1.insert_paragraph_before("Summary")
        new.style = doc.styles["Heading 1"]
        first_h1.text = "Inherited level"
        first_h1.style = style
        doc.save(p)
        self.assertOnlyFails(run_checker(p), "heading-skip")

    def test_f3_rows_inside_a_content_control_are_still_checked(self):
        p = self.dir / "f3.docx"
        build_docx(p, {"table_no_header"})

        def wrap_rows(files):
            from lxml import etree as LX
            root = LX.fromstring(files["word/document.xml"])
            tbl = root.find(f".//{{{W_NS}}}tbl")
            rows = tbl.findall(f"{{{W_NS}}}tr")
            sdt = LX.SubElement(tbl, f"{{{W_NS}}}sdt")
            content = LX.SubElement(sdt, f"{{{W_NS}}}sdtContent")
            for r in rows:
                content.append(r)
            files["word/document.xml"] = LX.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        rewrite_zip(p, wrap_rows)
        self.assertOnlyFails(run_checker(p), "table-header")

    def test_f4_an_image_in_a_custom_named_header_is_checked(self):
        p = self.dir / "f4.docx"
        build_docx(p)
        doc = Document(p)
        doc.sections[0].header.paragraphs[0].add_run().add_picture(io.BytesIO(png()))
        doc.save(p)

        def rename_header(files):
            old = next(n for n in files if n.startswith("word/header") and n.endswith(".xml"))
            files["word/customHeader.xml"] = files.pop(old)
            rels_old = old.replace("word/", "word/_rels/") + ".rels"
            if rels_old in files:
                files["word/_rels/customHeader.xml.rels"] = files.pop(rels_old)
            short = old.split("/")[-1]
            files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
                f'Target="{short}"'.encode(), b'Target="/word/customHeader.xml"')
            files["[Content_Types].xml"] = files["[Content_Types].xml"].replace(
                f"/word/{short}".encode(), b"/word/customHeader.xml")
        rewrite_zip(p, rename_header)
        code, out = run_checker(p)
        self.assertEqual(code, 1, out)
        self.assertIn("alt-text", failed_rules(out), out)
        self.assertIn("word/customHeader.xml", out)

    def test_f5_a_vague_link_split_across_runs_is_read_whole(self):
        p = self.dir / "f5.pptx"
        build_pptx(p, {"link_split"})
        self.assertOnlyFails(run_checker(p), "link-text")

    def test_f6_a_missing_slide_part_cannot_be_read(self):
        p = self.dir / "f6.pptx"
        build_pptx(p)
        rewrite_zip(p, lambda files: files.pop("ppt/slides/slide2.xml"))
        code, out = run_checker(p)
        self.assertEqual(code, 2, out)
        self.assertIn("CANNOT READ", out)

    def test_f7_a_decorative_tag_in_another_namespace_is_not_decorative(self):
        self.assertOnlyFails(self.docx("decorative_wrong_ns"), "alt-text")

    def test_f8_a_strict_open_xml_file_cannot_be_read(self):
        import zipfile
        p = self.dir / "strict.docx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("word/document.xml",
                       '<w:document xmlns:w="http://purl.oclc.org/ooxml/wordprocessingml/main"><w:body/></w:document>')
        code, out = run_checker(p)
        self.assertEqual(code, 2, out)
        self.assertIn("Strict", out)


class ControlAndErrors(Base):
    def test_control_file_with_every_defect_fails(self):
        p = self.dir / "control.docx"
        build_docx(p, {"no_title", "no_lang", "heading_skip", "alt_missing", "table_no_header", "link_vague"})
        code, out = run_checker(p)
        self.assertEqual(code, 1, out)
        self.assertEqual(failed_rules(out), {"title", "language", "heading-skip", "alt-text", "table-header", "link-text"}, out)
        q = self.dir / "control.pptx"
        build_pptx(q, {"no_title", "no_lang", "no_slide_title", "alt_missing", "table_no_header", "link_vague"})
        code, out = run_checker(q)
        self.assertEqual(code, 1, out)
        self.assertEqual(failed_rules(out), {"title", "language", "slide-title", "alt-text", "table-header", "link-text"}, out)

    def test_not_a_zip_cannot_be_read(self):
        p = self.dir / "x.docx"
        p.write_text("not a document")
        code, out = run_checker(p)
        self.assertEqual(code, 2, out)
        self.assertIn("CANNOT READ", out)

    def test_other_office_file_cannot_be_read(self):
        import zipfile
        p = self.dir / "book.xlsx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
        code, out = run_checker(p)
        self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
