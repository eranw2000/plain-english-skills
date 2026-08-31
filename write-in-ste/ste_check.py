#!/usr/bin/env python3
"""Mechanical checker for the ASD-STE100 rules that code can actually verify.

WHAT IT CANNOT SEE, stated up front because a green run reads as full compliance:
the ASD-STE100 approved-word dictionary. That is the core of the standard (about
900 approved words, each locked to one meaning and one part of speech, plus about
1200 not-approved words with substitutes), it is copyright ASD, and it is NOT what
this checker loads.

What it does load is whatever `dictionary/not_approved.txt` holds, and every run
PRINTS THE NAME of that list. Today that is a local plain-English list built from
public-domain sources, so a clean run means the document is plainer, never that it
is ASD-STE100 compliant. With no list at all, R8 is off and the run says so.

Prose only. Fenced code blocks, inline code spans, link targets and headings are
removed before analysis, because a command is not a sentence and STE does not
govern one.

Python 3.9 compatible on purpose: no PEP 604 unions, stdlib only.

  ste_check.py <file> [--mode procedural|descriptive] [--strict]
               [--dictionary DIR] [--json] [--quiet]
  ste_check.py --selftest

Exit 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MAX_WORDS = {"procedural": 20, "descriptive": 25}
MAX_SENTENCES_PER_PARA = 6
MAX_NOUN_CLUSTER = 3

BE_FORMS = {"is", "are", "was", "were", "be", "been", "being", "am"}
HAVE_FORMS = {"has", "have", "had"}

IRREGULAR_PARTICIPLES = {
    "been", "begun", "broken", "brought", "built", "bought", "chosen", "come",
    "done", "drawn", "driven", "eaten", "fallen", "felt", "found", "given",
    "gone", "got", "gotten", "held", "kept", "known", "left", "lost", "made",
    "meant", "met", "paid", "put", "read", "run", "said", "seen", "sent", "set",
    "shown", "sold", "spent", "taken", "taught", "told", "thought", "understood",
    "written", "won", "cut", "hit", "let", "shut", "split", "spread",
}

FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "as", "at", "by",
    "for", "from", "in", "into", "of", "off", "on", "onto", "out", "over", "to",
    "with", "without", "up", "down", "before", "after", "during", "not", "no",
    "this", "that", "these", "those", "it", "its", "you", "your", "we", "our",
    "he", "she", "they", "their", "his", "her", "them", "i", "my", "me", "us",
    "do", "does", "did", "can", "must", "will", "would", "should", "may",
    "when", "where", "which", "who", "what", "how", "why", "all", "any", "each",
    "more", "most", "other", "some", "such", "only", "own", "same", "so", "too",
    "very", "there", "here", "also", "because", "while", "until", "about",
}
FUNCTION_WORDS |= BE_FORMS | HAVE_FORMS


def load_wordlist(path, fallback):
    """A one-word-per-line file, '#' comments allowed. Missing file -> fallback."""
    if not os.path.exists(path):
        return set(fallback)
    out = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip().lower()
            if line:
                out.add(line)
    return out


ING_ALLOW_DEFAULT = {
    "during", "string", "thing", "nothing", "something", "anything", "everything",
    "ring", "spring", "bring", "king", "wing", "sing", "morning", "evening",
    "ceiling", "building", "warning", "engineering", "training", "meeting",
    "setting", "settings", "heading", "landing", "bearing", "casing", "housing",
    "coating", "wiring", "tubing", "packing", "bushing", "fitting", "mounting",
    "opening", "reading", "readings",
}


# --------------------------------------------------------------------------
# text extraction
# --------------------------------------------------------------------------

def strip_non_prose(text):
    """Remove what STE does not govern. Returns (clean_text, removed_counts)."""
    counts = {"frontmatter": 0, "fenced": 0, "inline": 0, "heading": 0, "link": 0}

    # YAML frontmatter is metadata, not prose. Left in, it parses as one long
    # nonsense sentence and reports a length violation that is not real.
    m = re.match(r"^---\n.*?\n---\n", text, flags=re.S)
    if m:
        counts["frontmatter"] = 1
        text = "\n" * m.group(0).count("\n") + text[m.end():]

    def _fence(m):
        counts["fenced"] += 1
        return "\n"

    text = re.sub(r"```.*?```", _fence, text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", _fence, text, flags=re.S)

    def _inline(m):
        counts["inline"] += 1
        return "CODE"

    text = re.sub(r"`[^`\n]+`", _inline, text)

    def _link(m):
        counts["link"] += 1
        return m.group(1)

    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", _link, text)
    text = re.sub(r"https?://\S+", "URL", text)

    kept = []
    for line in text.split("\n"):
        if re.match(r"^\s{0,3}#{1,6}\s", line):
            counts["heading"] += 1
            kept.append("")
            continue
        if re.match(r"^\s*(-{3,}|\*{3,}|={3,})\s*$", line):
            kept.append("")
            continue
        if re.match(r"^\s*\|", line):          # markdown table row
            kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept), counts


ABBREV = {"e.g", "i.e", "etc", "vs", "mr", "dr", "no", "fig", "ref", "approx"}


def split_sentences(block):
    """Split on terminal punctuation. Protects decimals, versions and abbreviations."""
    protected = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", block)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    out = []
    buf = ""
    for p in parts:
        cand = (buf + " " + p).strip() if buf else p.strip()
        last = re.sub(r"[^A-Za-z.]", "", cand.split()[-1]).rstrip(".").lower() if cand.split() else ""
        if last in ABBREV:
            buf = cand
            continue
        buf = ""
        if cand:
            out.append(cand.replace("<DOT>", "."))
    if buf:
        out.append(buf.replace("<DOT>", "."))
    return out


def split_units(text):
    """Yield (unit_kind, sentences, line_no).

    A list item is its own unit, so a vertical list does not read as one
    12-sentence paragraph. STE actively wants vertical lists; penalising them
    would be a bug in the rule.
    """
    units = []
    para = []
    para_line = 1
    line_no = 0
    for raw in text.split("\n"):
        line_no += 1
        line = raw.rstrip()
        is_item = bool(re.match(r"^\s*([-*+]|\d+[.)])\s+", line))
        if not line.strip():
            if para:
                units.append(("paragraph", "\n".join(para), para_line))
                para = []
            continue
        if is_item:
            if para:
                units.append(("paragraph", "\n".join(para), para_line))
                para = []
            body = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", line)
            units.append(("list-item", body, line_no))
            continue
        if not para:
            para_line = line_no
        para.append(line)
    if para:
        units.append(("paragraph", "\n".join(para), para_line))
    return units


def words_of(sentence):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)]


def is_participle(word):
    w = word.lower()
    return w in IRREGULAR_PARTICIPLES or (len(w) > 3 and w.endswith("ed"))


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

class Finding(object):
    def __init__(self, rule, band, line, message, excerpt):
        self.rule = rule
        self.band = band
        self.line = line
        self.message = message
        self.excerpt = excerpt

    def as_dict(self):
        return {
            "rule": self.rule, "band": self.band, "line": self.line,
            "message": self.message, "excerpt": self.excerpt,
        }


def excerpt(s, n=70):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


def check_text(text, mode="procedural", dictionary_dir=None):
    findings = []
    clean, counts = strip_non_prose(text)
    limit = MAX_WORDS[mode]

    ing_allow = load_wordlist(os.path.join(HERE, "dictionary", "ing_allow.txt"),
                              ING_ALLOW_DEFAULT)
    not_approved = {}
    # A loaded list must say what it IS. Without this a locally-assembled list
    # is indistinguishable from the official one in the output, which is the
    # false-compliance trap dictionary/README.md warns about, just moved.
    dict_name = ""
    if dictionary_dir:
        path = os.path.join(dictionary_dir, "not_approved.txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.lower().startswith("# name:"):
                        dict_name = stripped.split(":", 1)[1].strip()
                    line = line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    if "=" in line:
                        bad, good = line.split("=", 1)
                        not_approved[bad.strip().lower()] = good.strip()
                    else:
                        not_approved[line.lower()] = ""
    if not_approved and not dict_name:
        dict_name = "unnamed list (%d entries)" % len(not_approved)

    # Multi-word entries need their own matcher, built once per run.
    phrase_terms = sorted((t for t in not_approved if " " in t),
                          key=lambda t: (-len(t), t))
    PHRASE_RX = {}
    for t in phrase_terms:
        PHRASE_RX[t] = re.compile(
            r"(?<![\w-])" + r"\s+".join(re.escape(p) for p in t.split())
            + r"(?![\w-])")

    for kind, body, line_no in split_units(clean):
        sentences = split_sentences(body)
        sentences = [s for s in sentences if words_of(s)]

        # Applies to a list item too. Splitting into units already protects a
        # vertical list (seven one-sentence items are seven units of one), so
        # exempting list items only hid a single bullet holding seven sentences,
        # which is a paragraph wearing a dash. Found by mutating the conjunct.
        if len(sentences) > MAX_SENTENCES_PER_PARA:
            findings.append(Finding(
                "R2", "hard", line_no,
                "paragraph has %d sentences, limit is %d"
                % (len(sentences), MAX_SENTENCES_PER_PARA),
                excerpt(sentences[0])))

        for s in sentences:
            ws = words_of(s)
            low = [w.lower() for w in ws]

            if len(ws) > limit:
                findings.append(Finding(
                    "R1", "hard", line_no,
                    "sentence has %d words, %s limit is %d" % (len(ws), mode, limit),
                    excerpt(s)))

            for i in range(len(low) - 1):
                if low[i] in HAVE_FORMS and is_participle(low[i + 1]):
                    findings.append(Finding(
                        "R3", "hard", line_no,
                        "present/past perfect '%s %s', use the simple past"
                        % (low[i], low[i + 1]),
                        excerpt(s)))
                    break

            for i in range(len(low) - 1):
                if low[i] in BE_FORMS and is_participle(low[i + 1]):
                    band = "hard" if mode == "procedural" else "advisory"
                    findings.append(Finding(
                        "R4", band, line_no,
                        "passive voice '%s %s', name the actor and use the active voice"
                        % (low[i], low[i + 1]),
                        excerpt(s)))
                    break

            for w in low:
                if w.endswith("ing") and len(w) > 4 and w not in ing_allow:
                    findings.append(Finding(
                        "R5", "advisory", line_no,
                        "'-ing' form '%s'; allowed only as a technical noun or "
                        "modifier (extend dictionary/ing_allow.txt if it is one)" % w,
                        excerpt(s)))
                    break

            run = 0
            for w in low:
                run = 0 if w in FUNCTION_WORDS else run + 1
                if run > MAX_NOUN_CLUSTER:
                    findings.append(Finding(
                        "R6", "advisory", line_no,
                        "noun cluster longer than %d words" % MAX_NOUN_CLUSTER,
                        excerpt(s)))
                    break

            if mode == "procedural":
                joins = len(re.findall(r"\b(and then|, then|; )", s.lower()))
                if joins:
                    findings.append(Finding(
                        "R7", "advisory", line_no,
                        "looks like more than one instruction; split into one "
                        "instruction per sentence",
                        excerpt(s)))

            if not_approved:
                # Report every DISTINCT offender in the sentence, not just the
                # first. A word list exists to be acted on, and stopping at the
                # first match means one re-run per bad word. Deduping by term
                # still stops a repeated word from flooding the report.
                #
                # Phrases are matched against the sentence text, because a loop
                # over single words can never see "in order to". Ten of the
                # first list's entries were dead until this was added, and
                # nothing in the output said so.
                seen_terms = set()
                for w in low:
                    if w in not_approved and w not in seen_terms:
                        seen_terms.add(w)
                        sub = not_approved[w]
                        findings.append(Finding(
                            "R8", "hard", line_no,
                            "'%s' is not an approved word%s" % (
                                w, (", use '%s'" % sub) if sub else ""),
                            excerpt(s)))
                slow = s.lower()
                # No already-seen check here: seen_terms holds single words,
                # which never contain a space, and every phrase does, so the
                # two sets cannot intersect. A guard was written here and
                # proved unreachable by instrumenting it across the suite and
                # 40 real documents, with a forced-true control confirming the
                # instrument fired. Deleted rather than tested.
                for term in phrase_terms:
                    if PHRASE_RX[term].search(slow):
                        sub = not_approved[term]
                        findings.append(Finding(
                            "R8", "hard", line_no,
                            "'%s' is not an approved phrase%s" % (
                                term, (", use '%s'" % sub) if sub else ""),
                            excerpt(s)))

    return findings, counts, dict_name


# --------------------------------------------------------------------------
# selftest: the two-way control
# --------------------------------------------------------------------------

DIRTY = """
The replacement of the hydraulic pump has been completed by the technician and then
the system was tested thoroughly before the aircraft main landing gear actuator
assembly housing was subsequently reinstalled into its correct position by the crew.
"""

CLEAN = """
Remove the pump.

Install the new pump.

Do a test of the system.
"""


def selftest():
    ok = True
    dirty, _, _ = check_text(DIRTY, mode="procedural")
    rules_hit = sorted({f.rule for f in dirty})
    want = ["R1", "R3", "R4"]
    missing = [r for r in want if r not in rules_hit]
    if missing:
        ok = False
        print("SELFTEST FAIL: dirty passage did not trigger %s (got %s)"
              % (missing, rules_hit))
    else:
        print("selftest: dirty passage triggered %s" % rules_hit)

    clean, _, _ = check_text(CLEAN, mode="procedural")
    hard = [f for f in clean if f.band == "hard"]
    if hard:
        ok = False
        print("SELFTEST FAIL: clean passage produced hard findings: %s"
              % [(f.rule, f.message) for f in hard])
    else:
        print("selftest: clean passage produced no hard findings")

    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", nargs="?", help="markdown or text file to check")
    ap.add_argument("--mode", choices=sorted(MAX_WORDS), default="procedural")
    ap.add_argument("--strict", action="store_true",
                    help="advisory findings also fail the run")
    ap.add_argument("--dictionary", help="dir holding not_approved.txt")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.file:
        ap.print_usage()
        print("error: a file is required (or --selftest)")
        return 2
    if not os.path.exists(a.file):
        print("error: no such file: %s" % a.file)
        return 2

    with open(a.file, encoding="utf-8") as fh:
        text = fh.read()

    dict_dir = a.dictionary or os.path.join(HERE, "dictionary")
    findings, counts, dict_name = check_text(text, a.mode, dict_dir)
    dict_on = bool(dict_name)

    hard = [f for f in findings if f.band == "hard"]
    adv = [f for f in findings if f.band == "advisory"]

    if a.json:
        print(json.dumps({
            "file": a.file, "mode": a.mode,
            "dictionary_installed": dict_on,
            "dictionary_name": dict_name,
            "hard": [f.as_dict() for f in hard],
            "advisory": [f.as_dict() for f in adv],
            "excluded": counts,
        }, indent=2))
    elif not a.quiet:
        print("%s  mode=%s" % (a.file, a.mode))
        print("excluded from analysis: %d frontmatter, %d fenced blocks, "
              "%d inline spans, %d headings, %d links"
              % (counts["frontmatter"], counts["fenced"], counts["inline"],
                 counts["heading"], counts["link"]))
        for f in hard + adv:
            print("  [%s] %s line %s: %s" % (f.band.upper(), f.rule, f.line, f.message))
            print("        %s" % f.excerpt)
        print("hard: %d   advisory: %d" % (len(hard), len(adv)))
        if not dict_on:
            print("NOT CHECKED: no word list is installed, so word choice (R8) is "
                  "unverified. See dictionary/README.md.")
        else:
            print("word list: %s" % dict_name)

    failed = bool(hard) or (a.strict and bool(adv))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
