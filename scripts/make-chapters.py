#!/usr/bin/env python3
"""Number the chapters from the index.

The index (the guide) is the single source of the chapter order.  This
script reads the links to sheets in the guide, in order, and

  * numbers the sheets of the main sequence 1, 2, ..., N;
  * keeps the names of side-series sheets (A1, A2, ...), which are
    taken from the link labels under the "Side series" heading;
  * rewrites the number at the start of each link label in the guide,
    so that a new sheet can be listed without a number;
  * writes chapters.tex, which defines \\chapnumber{ID} for each sheet
    ID (the Denote timestamp at the start of its file name).

A sheet sets its number with

    \\newcounter{chap}
    \\input{chapters}\\chapnumber{20261125T001000}

Run from the repository root.  With --check, change nothing and exit 1
if the guide labels or chapters.tex are out of date.
"""
import os
import re
import sys

GUIDE = "20261125T012000--grh-workbook__guide.org"
OUT = "chapters.tex"

# An index entry is a list item that starts with a link to a sheet.
LINK = re.compile(
    r"(?<=^- )\[\[file:(?P<id>\d{8}T\d{6})--(?P<rest>[^\]]*?)__workbook\.html\]"
    r"\[(?P<label>[^\]]*)\]\]")
SIDE_NAME = re.compile(r"^(?P<name>[A-Z]+\d+)\.\s+(?P<title>.*)$")
MAIN_NUM = re.compile(r"^\d+\.\s+")


def die(msg):
    sys.exit(f"make-chapters: {msg}")


def main():
    check = "--check" in sys.argv[1:]
    with open(GUIDE, encoding="utf-8") as f:
        guide = f.read()

    order = []            # (id, number-or-name)
    seen = {}
    out_lines = []
    n = 0
    side = False
    for line in guide.split("\n"):
        if line.startswith("* "):
            side = "side series" in line.lower()

        def relabel(m):
            nonlocal n
            ident, label = m.group("id"), m.group("label")
            if ident in seen:
                die(f"sheet {ident} is listed twice in the index")
            if side:
                sm = SIDE_NAME.match(label)
                if not sm:
                    die(f"side-series entry {ident} needs a name such as "
                        f"'A3. Title' in its label, got {label!r}")
                num = sm.group("name")
            else:
                n += 1
                num = str(n)
                label = f"{num}. {MAIN_NUM.sub('', label, count=1)}"
            seen[ident] = num
            order.append((ident, num, m.group("rest")))
            return (f"[[file:{ident}--{m.group('rest')}__workbook.html]"
                    f"[{label}]]")

        item = re.match(r"^\s*- ", line)
        if item:
            line = line[:item.end()] + LINK.sub(
                relabel, "- " + line[item.end():], count=1)[2:]
        out_lines.append(line)
    new_guide = "\n".join(out_lines)

    for ident, _, rest in order:
        tex = f"{ident}--{rest}__workbook.tex"
        if not os.path.exists(tex):
            die(f"the index lists {tex}, which does not exist")

    table = "\n".join(
        f"\\chapters@set{{{ident}}}{{{num}}}% {rest}"
        for ident, num, rest in order)
    new_out = rf"""% Chapter numbers, generated from {GUIDE}
% by scripts/make-chapters.py.  Do not edit: change the order of the
% index and rerun the script (./preview-site.sh and CI do this).
%
% Usage in a sheet, after \newcounter{{chap}}:
%   \input{{chapters}}\chapnumber{{<sheet ID>}}
\makeatletter
\providecommand\chapters@set[2]{{\@namedef{{chapters@#1}}{{#2}}}}
{table}
\providecommand\chapnumber[1]{{%
  \@ifundefined{{chapters@#1}}%
    {{\PackageError{{chapters}}{{Sheet #1 is not listed in the index}}%
      {{List it in {GUIDE}\MessageBreak
       and run scripts/make-chapters.py.}}}}%
    {{\edef\thechap{{\@nameuse{{chapters@#1}}}}}}}}
\makeatother
"""
    old_out = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None

    stale = []
    if new_guide != guide:
        stale.append(GUIDE)
    if new_out != old_out:
        stale.append(OUT)
    if check:
        if stale:
            die("out of date: " + ", ".join(stale)
                + "; run scripts/make-chapters.py")
        return
    if new_guide != guide:
        with open(GUIDE, "w", encoding="utf-8") as f:
            f.write(new_guide)
    if new_out != old_out:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(new_out)
    for s in stale:
        print(f"make-chapters: updated {s}")


if __name__ == "__main__":
    main()
