#!/usr/bin/env python3
"""Fail if a sheet or the index types a workbook number by hand.

Chapter, section, problem and theorem numbers change when a chapter is
inserted, so prose must get them from \\ref (with xr prefixes for other
sheets), and the index gets them from scripts/make-chapters.py.  This
lint reports prose such as "Chapter 12", "Chapters~\\ref{a-chap} and~13",
"Problem 3.2.1", "Ch. 7", "\\S4.2", "§4.2", or a bare "3.2.1".

Not checked: the preamble, comments, optional arguments of \\cite (so
\\cite[Ch.~12]{Dav} is fine), the bibliography, URLs, \\ref and \\label
arguments, and the link labels of index entries.

Escapes, for numbers that refer to another work or are not references:
  * in a .tex file, a comment on the same line,
        % check-numbers: ok (Davenport): Ch.~12; Ch.~17
    allows the listed matches on that line (as printed by this lint);
    the parenthesised reason is optional, and "% check-numbers: ok"
    without a list allows every match on the line;
  * in an .org file, a comment line "# check-numbers: ok[: ...]" applies
    to the next line.

Usage: scripts/check-numbers.py [FILE ...]   (default: the sheets and
the index).  Exit status 1 if anything is reported.
"""
import glob
import re
import sys

GUIDE = "20261125T012000--grh-workbook__guide.org"

KEYWORD = (r"(?:Chapters?|Ch\.|Sheets?|Sections?|Sec\.|\\S\\S|\\S|§§|§"
           r"|Problems?|Pr\.|Theorems?|Thm\.|Hints?|Exercises?"
           r"|Lemmas?|Propositions?|Corollar(?:y|ies)|Remarks?)")
NUMBER = r"[A-Z]?\d+[A-Z]?(?:\.\d+)*"
REF = r"\\(?:ref|eqref)\{[^}]*\}"
SEP = r"(?:\s*(?:,|--|–|-)\s*|\s+(?:and|or|to)[~\s]+|\s*,\s*and\s+)~?"
# A keyword followed by a list of numbers and \refs.
LIST = re.compile(
    rf"(?<![A-Za-z]){KEYWORD}[~\s]*(?:(?:{REF}|{NUMBER})(?:{SEP}(?:{REF}|{NUMBER}))*)")
BARE_TRIPLE = re.compile(r"(?<![\w.])\d+\.\d+\.\d+(?![\w.])")
HAS_BARE = re.compile(rf"(?:^|[~\s,–-]|\\S|§){NUMBER}(?![\w}}])")
REASON = r"(?:\s*\([^)]*\))?"
ESCAPE_TEX = re.compile(rf"%\s*check-numbers:\s*ok{REASON}(?::\s*(.*))?$")
ESCAPE_ORG = re.compile(rf"^\s*#\s+check-numbers:\s*ok{REASON}(?::\s*(.*))?$")


def blank(text, pattern, flags=0):
    """Replace matches of PATTERN by spaces, keeping newlines."""
    return re.sub(pattern,
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                  text, flags=flags)


def strip_braced(text, command):
    """Blank optional [...] arguments of \\COMMAND, which may nest {}."""
    out = list(text)
    for m in re.finditer(r"\\" + command + r"\*?\s*\[", text):
        depth, i = 0, m.end()
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == "]" and depth == 0:
                break
            i += 1
        for j in range(m.end(), i):
            if out[j] != "\n":
                out[j] = " "
    return "".join(out)


def allowed(escape, match):
    if escape is None:
        return False
    if escape.group(1) is None:
        return True
    items = [s.strip() for s in escape.group(1).split(";")]
    norm = re.sub(r"\s+", " ", match)
    return norm in items


def scan(text, escapes, path):
    problems = []
    lists = list(LIST.finditer(text))
    spans = [(m.start(), m.end()) for m in lists]
    triples = [m for m in BARE_TRIPLE.finditer(text)
               if not any(a <= m.start() < b for a, b in spans)]
    for m in sorted(lists + triples, key=lambda m: m.start()):
        s = m.group(0)
        tail = re.sub(rf"^{KEYWORD}", "", s) if m.re is LIST else " " + s
        tail = re.sub(REF, "", tail)
        if not HAS_BARE.search(tail):
            continue
        line = text.count("\n", 0, m.start())
        shown = re.sub(r"\s+", " ", s)
        if allowed(escapes.get(line), shown):
            continue
        problems.append(f"{path}:{line + 1}: hard-coded number: {shown}")
    return problems


def check_tex(path):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    escapes = {}
    for i, l in enumerate(lines):
        e = ESCAPE_TEX.search(l)
        if e:
            escapes[i] = e
    begin = text.find("\\begin{document}")
    head = text[:begin] if begin >= 0 else ""
    body = re.sub(r"[^\n]", " ", head) + text[len(head):]
    body = blank(body, r"(?<!\\)%.*")
    body = blank(body, r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                 re.S)
    for cmd in ("cite", "citep", "citet", "item", "bibitem"):
        body = strip_braced(body, cmd)
    body = blank(body, r"\\(?:url|href|label|externaldocument"
                       r"|input|include|chapnumber)\{[^}]*\}")
    body = blank(body, r"\\(?:cite|citep|citet)\{[^}]*\}")
    return scan(body, escapes, path)


def check_org(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    escapes = {}
    out = []
    for i, l in enumerate(lines):
        e = ESCAPE_ORG.match(l)
        if e:
            escapes[i + 1] = e
        if l.lstrip().startswith("#"):
            l = ""
        # Index entries: the link label is generated, so skip it.
        l = re.sub(r"\[\[[^\]]*\]\[[^\]]*\]\]", lambda m: " " * len(m.group(0)), l)
        l = re.sub(r"\[\[[^\]]*\]\]", lambda m: " " * len(m.group(0)), l)
        out.append(l)
    return scan("\n".join(out), escapes, path)


def main():
    files = sys.argv[1:] or sorted(glob.glob("*__workbook.tex")) + [GUIDE]
    problems = []
    for f in files:
        problems += check_org(f) if f.endswith(".org") else check_tex(f)
    for p in problems:
        print(p)
    if problems:
        print(f"check-numbers: {len(problems)} hard-coded number(s); use "
              "\\ref (or an escape comment if the number refers to "
              "another work).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
