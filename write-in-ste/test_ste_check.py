#!/usr/bin/env python3
"""Tests for ste_check.py.

Every rule gets a CONTRAST PAIR: text that must fire, and near-identical text
that must stay silent. A test that only proves a check can fire is half a test,
because a rule that fires on everything passes it.

Run with either interpreter:
  /usr/bin/python3 test_ste_check.py
  ~/miniconda3/bin/python3 test_ste_check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ste_check as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PASS = []
FAIL = []


def check(name, got, want):
    # coerce, because a printer that crashes on a non-string swallows every
    # verdict after the first bad row
    ok = got == want
    (PASS if ok else FAIL).append((name, str(got), str(want)))


def rules(text, mode="procedural", dictionary_dir=None):
    f, _, _ = S.check_text(text, mode, dictionary_dir)
    return sorted({x.rule for x in f})


def bands(text, mode="procedural"):
    f, _, _ = S.check_text(text, mode)
    return {(x.rule, x.band) for x in f}


# --- R1 sentence length, with a boundary and a mode contrast ---------------
w20 = " ".join(["word"] * 19) + " end."
w21 = " ".join(["word"] * 20) + " end."
check("R1 fires at 21 words procedural", "R1" in rules(w21), True)
check("R1 silent at 20 words procedural", "R1" in rules(w20), False)
check("R1 silent at 21 words descriptive", "R1" in rules(w21, "descriptive"), False)
check("R1 fires at 26 words descriptive",
      "R1" in rules(" ".join(["word"] * 25) + " end.", "descriptive"), True)

# --- R2 paragraph length, and the list-item exemption ----------------------
seven = "\n".join(["Do the thing number %d." % i for i in range(7)])
six = "\n".join(["Do the thing number %d." % i for i in range(6)])
seven_list = "\n".join(["- Do the thing number %d." % i for i in range(7)])
check("R2 fires on a 7-sentence paragraph", "R2" in rules(seven), True)
check("R2 silent on a 6-sentence paragraph", "R2" in rules(six), False)
check("R2 silent on a 7-item vertical list", "R2" in rules(seven_list), False)
# A single bullet holding 7 sentences is a paragraph wearing a dash. The list
# exemption used to swallow it; mutating the conjunct is what surfaced that.
check("R2 fires on ONE list item holding 7 sentences",
      "R2" in rules("- " + " ".join(["Do thing %d." % i for i in range(7)])), True)

# --- R3 perfect tenses -----------------------------------------------------
check("R3 fires on 'has been completed'",
      "R3" in rules("The task has been completed."), True)
check("R3 fires on irregular 'have done'",
      "R3" in rules("You have done the check."), True)
check("R3 silent on simple past", "R3" in rules("You completed the task."), False)

# --- R4 passive, and the band changes with mode ---------------------------
passive = "The pump was removed."
check("R4 fires on passive", "R4" in rules(passive), True)
check("R4 silent on active", "R4" in rules("Remove the pump."), False)
# The sharper control: an ACTIVE sentence that still contains a participle.
# "Remove the pump." has no participle at all, so it cannot tell a working
# be-form check from one that flags any word before a participle.
check("R4 silent on active text containing a participle",
      "R4" in rules("You removed the damaged pump."), False)
check("R4 is hard in procedural", ("R4", "hard") in bands(passive), True)
check("R4 is advisory in descriptive",
      ("R4", "advisory") in bands(passive, "descriptive"), True)

# --- R5 -ing forms and the allowlist --------------------------------------
check("R5 fires on a plain -ing form",
      "R5" in rules("Start installing the unit."), True)
check("R5 silent on allowlisted 'during'",
      "R5" in rules("Hold the switch during the test."), False)
check("R5 silent on allowlisted 'warning'",
      "R5" in rules("Read the warning first."), False)
# The length floor: a 4-letter -ing word that is NOT on the allowlist must stay
# silent. Without this, mutating the floor from 4 to 0 changes nothing and the
# guard is untested.
check("R5 silent on a 4-letter -ing word below the floor",
      "R5" in rules("Send a ping to the host."), False)

# --- R6 noun clusters ------------------------------------------------------
check("R6 fires on a 4-word noun run",
      "R6" in rules("Replace main landing gear actuator now."), True)
check("R6 silent when a function word breaks the run",
      "R6" in rules("Replace the actuator of the gear now."), False)

# --- R7 more than one instruction ------------------------------------------
check("R7 fires on 'and then'",
      "R7" in rules("Remove the bolt and then remove the cover."), True)
check("R7 silent on one instruction",
      "R7" in rules("Remove the bolt."), False)
check("R7 silent in descriptive mode",
      "R7" in rules("Remove the bolt and then remove the cover.", "descriptive"), False)

# --- non-prose stripping, each with its live contrast ----------------------
long_sentence = " ".join(["word"] * 30) + " end."
check("prose control: the long sentence does fire", "R1" in rules(long_sentence), True)
check("fenced code is excluded",
      "R1" in rules("```\n" + long_sentence + "\n```"), False)
check("inline code is excluded",
      "R1" in rules("`" + long_sentence + "`"), False)
check("headings are excluded", "R1" in rules("# " + long_sentence), False)
check("frontmatter is excluded",
      "R1" in rules("---\nname: x\ndesc: " + long_sentence + "\n---\n"), False)
check("table rows are excluded", "R1" in rules("| " + long_sentence + " |"), False)

# --- sentence splitting does not break on decimals or abbreviations -------
f, _, _ = S.check_text("Issue 9.1 is current. Use it.")
check("decimal does not split a sentence", len(S.split_sentences("Issue 9.1 is current.")), 1)
check("abbreviation does not split",
      len(S.split_sentences("Use the pump, e.g. the main one, first.")), 1)

# --- R8 dictionary: off by default, on when installed ---------------------
tmp = tempfile.mkdtemp()
with open(os.path.join(tmp, "not_approved.txt"), "w", encoding="utf-8") as fh:
    fh.write("# seed\nensure = make sure\nutilize = use\n")
check("R8 silent with no dictionary",
      "R8" in rules("Ensure the valve is open.", "procedural", tmp + "-missing"), False)
check("R8 fires with a dictionary installed",
      "R8" in rules("Ensure the valve is open.", "procedural", tmp), True)
check("R8 silent on approved wording with a dictionary installed",
      "R8" in rules("Make sure that the valve is open.", "procedural", tmp), False)

# --- R8 multi-word phrases ------------------------------------------------
# A loop over single words can never match "in order to". Ten entries of the
# first real list were dead this way and the output looked perfectly clean.
tmp2 = tempfile.mkdtemp()
with open(os.path.join(tmp2, "not_approved.txt"), "w", encoding="utf-8") as fh:
    fh.write("# name: test list\nin order to = to\nensure = make sure\n"
             "a number of = some\nutilize = use\n")


def r8_msgs(text, dictionary_dir):
    f, _, _ = S.check_text(text, "procedural", dictionary_dir)
    return [x.message for x in f if x.rule == "R8"]


check("R8 fires on a multi-word phrase",
      "R8" in rules("We did it in order to win.", "procedural", tmp2), True)
check("R8 silent when the phrase is absent",
      "R8" in rules("We did it to win.", "procedural", tmp2), False)
check("R8 silent on a partial phrase match",
      "R8" in rules("Put it in order, then win.", "procedural", tmp2), False)
check("R8 phrase matches across a line break",
      len(r8_msgs("We did it in order\nto win.", tmp2)), 1)
check("R8 phrase names itself as a phrase",
      "phrase" in (r8_msgs("We did it in order to win.", tmp2) or [""])[0], True)

# --- R8 reports every distinct offender, not just the first ---------------
check("R8 reports both offenders in one sentence",
      len(r8_msgs("Ensure we did it in order to win.", tmp2)), 2)
# Two bad WORDS, no phrase. Without this the earlier pair passes even if the
# word loop still stops at the first match, because the phrase loop supplies
# the second finding.
check("R8 reports two bad words in one sentence",
      len(r8_msgs("Ensure we utilize the valve.", tmp2)), 2)
# A trailing boundary, or the phrase matches inside a longer word: "a number
# of" would otherwise fire on "a number often".
check("R8 phrase does not match inside a longer word",
      len(r8_msgs("We need a number often.", tmp2)), 0)
check("R8 phrase still fires when properly bounded",
      len(r8_msgs("We need a number of items.", tmp2)), 1)
check("R8 does not repeat one word appearing twice",
      len(r8_msgs("Ensure the valve is open and ensure it stays open.", tmp2)), 1)
check("R8 count is zero on clean text",
      len(r8_msgs("Make sure we did it to win.", tmp2)), 0)

# --- a BARE entry, no substitute -----------------------------------------
# dictionary/README.md documents this format, and nothing exercised it. The
# message must still name the word and must NOT trail an empty "use ''".
tmp3 = tempfile.mkdtemp()
with open(os.path.join(tmp3, "not_approved.txt"), "w", encoding="utf-8") as fh:
    fh.write("# name: bare list\ncommence\nensure = make sure\n")
_bare = r8_msgs("Commence the procedure.", tmp3)
check("R8 fires on a bare entry", len(_bare), 1)
check("bare entry names the word", "commence" in (_bare or [""])[0], True)
check("bare entry suggests nothing", "use" in (_bare or [""])[0], False)
_sub = r8_msgs("Ensure the valve is open.", tmp3)
check("an entry WITH a substitute still suggests it",
      "use 'make sure'" in (_sub or [""])[0], True)

# --- the loaded list must name itself -------------------------------------
# Without this a locally-built list is indistinguishable from the official one
# in the output, which is the false-compliance trap moved rather than fixed.
check("dictionary name is read from the file",
      S.check_text("x", "procedural", tmp2)[2], "test list")
check("no dictionary means no name",
      S.check_text("x", "procedural", tmp2 + "-missing")[2], "")
check("an unnamed list still reports that it is loaded",
      S.check_text("x", "procedural", tmp)[2].startswith("unnamed list"), True)

# --- exit codes through the real CLI --------------------------------------
def run_cli(text, *args):
    p = os.path.join(tempfile.mkdtemp(), "d.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    r = subprocess.run([sys.executable, os.path.join(HERE, "ste_check.py"), p] + list(args),
                       capture_output=True, text=True)
    return r.returncode


check("CLI exit 0 on clean text", run_cli("Remove the pump.", "--quiet"), 0)
check("CLI exit 1 on a hard finding", run_cli(w21, "--quiet"), 1)
check("CLI exit 0 on advisory only",
      run_cli("Start installing the unit.", "--quiet"), 0)
check("CLI exit 1 on advisory with --strict",
      run_cli("Start installing the unit.", "--quiet", "--strict"), 1)
check("CLI exit 2 on a missing file",
      subprocess.run([sys.executable, os.path.join(HERE, "ste_check.py"),
                      "/nope/nope.md"], capture_output=True).returncode, 2)
check("CLI selftest exits 0",
      subprocess.run([sys.executable, os.path.join(HERE, "ste_check.py"), "--selftest"],
                     capture_output=True).returncode, 0)

# --------------------------------------------------------------------------
print("PASS %d   FAIL %d" % (len(PASS), len(FAIL)))
for n, g, w in FAIL:
    print("  FAIL %s: got %s want %s" % (n, g, w))
sys.exit(1 if FAIL else 0)
