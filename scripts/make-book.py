#!/usr/bin/env python3
"""Assemble the whole collection into one PDF, in the order of the index.

Usage:  python3 scripts/make-book.py --site DIR

Run after the sheets are built: DIR holds the per-sheet PDFs (in CI and
in preview-site.sh it is the build directory itself).  The script

  - reads the index (the guide) for the title, the opening and status
    paragraphs and the order of the Parts and of their sheets;
  - writes a master LaTeX file that has a title page (title, the two
    paragraphs, date, commit), a table of contents by Part, and then
    every listed sheet's PDF, included page by page with pdfpages; each
    sheet gets a table-of-contents line and a PDF bookmark under its
    Part, and the pages are numbered continuously (the numbers of the
    contents and the PDF page labels);
  - compiles it with pdflatex and puts it at DIR/grh-via-exercises.pdf;
  - writes DIR/book-link.org, the sentence of the index that links the
    file and gives its number of pages (empty if the build failed).

Only the sheets listed in the index are included: not the snapshot
under original-route/, not the pages of withdrawn sheets, not the
sources.  The sheets' own text is kept as it is; links inside the
sheets are not kept by pdfpages (they are in the per-sheet PDFs).
Exit status 1 if the PDF could not be made.
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

GUIDE = "20261125T012000--grh-workbook__guide.org"
BOOK = "grh-via-exercises.pdf"
LINK = "book-link.org"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def org_to_latex(text):
    """Convert one Org paragraph to LaTeX with pandoc."""
    out = subprocess.run(
        ["pandoc", "-f", "org", "-t", "latex", "--wrap=none"],
        input=text, capture_output=True, text=True, check=True).stdout
    return out.strip()


def escape_title(title):
    """Escape a plain title for LaTeX, leaving $...$ math alone."""
    parts = re.split(r"(\$[^$]*\$)", title)
    out = []
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p) > 1:
            out.append(p)
        else:
            p = re.sub(r"(?<!\\)([&%#_])", r"\\\1", p)
            p = re.sub(r"/([^/\s][^/]*[^/\s]|[^/\s])/", r"\\emph{\1}", p)
            out.append(p)
    return "".join(out)


def read_guide(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    title = "GRH via exercises"
    paragraphs = []  # the opening and the status paragraphs
    parts = []       # [(part title, [(id stem, label, title)])]
    i = 0
    for line in lines:
        m = re.match(r"#\+TITLE:\s*(.*)", line)
        if m:
            title = m.group(1).strip()
    # The opening paragraph is the first paragraph after the keywords;
    # the status paragraph begins with *Status.
    body = [l for l in lines if not l.startswith("#")]
    text = "\n".join(body)
    head = text.split("\n* ", 1)[0]
    paras = [p.strip() for p in re.split(r"\n\s*\n", head) if p.strip()]
    if paras:
        paragraphs.append(paras[0])
    for p in paras:
        if p.startswith("*Status"):
            paragraphs.append(p)
    current = None
    for line in lines:
        h = re.match(r"\* (.*)", line)
        if h:
            name = h.group(1).strip()
            if name == "Sources":
                current = None
            else:
                current = (name, [])
                parts.append(current)
            continue
        e = re.match(r"- \[\[file:([^\]]+)\.html\]\[([^\]]+)\]\]", line)
        if e and current is not None:
            stem, label = e.group(1), e.group(2)
            num, _, name = label.partition(". ")
            current[1].append((stem, num, name))
    parts = [p for p in parts if p[1]]
    return title, paragraphs, parts


def commit_id():
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:7]
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def master_tex(title, paragraphs, parts, site, date, commit):
    out = [r"""\documentclass[11pt]{report}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{pdfpages}
\usepackage[hidelinks,bookmarksopen,bookmarksopenlevel=0,
  pdftitle={%(title)s},pdfauthor={Paul D. Nelson}]{hyperref}
\setcounter{tocdepth}{0}
\pdfstringdefDisableCommands{\def\numberline#1{#1. }}
\setcounter{secnumdepth}{-2}
\makeatletter
\renewcommand*\l@chapter{\@dottedtocline{0}{0em}{2.3em}}
\makeatother
\begin{document}
\pagenumbering{roman}
\begin{titlepage}
\centering
{\Huge %(title)s\par}
\vspace{1.5em}
{\large The whole collection in one file\par}
\vspace{2em}
\begin{minipage}{0.86\textwidth}
\setlength{\parskip}{0.8em}\small
""" % {"title": title}]
    for p in paragraphs:
        out.append(org_to_latex(p) + "\n\n")
    out.append(r"""\end{minipage}
\vfill
{\small Built %(date)s from commit \texttt{%(commit)s} of \url{https://github.com/ultronozm/grh-workbook}.\\
The sheets, one file each, and this file: \url{https://ultronozm.github.io/grh-workbook/}\par}
\end{titlepage}
\setcounter{page}{2}
\pdfbookmark[-1]{Contents}{contents}
\tableofcontents
\cleardoublepage
\pagenumbering{arabic}
""" % {"date": date, "commit": commit})
    n = 0
    for part, sheets in parts:
        first = True
        for stem, num, name in sheets:
            pdf = os.path.join(site, stem + ".pdf")
            if not os.path.exists(pdf):
                raise FileNotFoundError(pdf)
            n += 1
            entries = []
            if first:
                entries.append("1,part,-1,{%s},part%d" % (escape_title(part), n))
                first = False
            entries.append("1,chapter,0,{\\protect\\numberline{%s}%s},sheet%d"
                           % (escape_title(num), escape_title(name), n))
            out.append("\\includepdf[pages=-,addtotoc={%s}]{%s}\n"
                       % (",".join(entries), pdf))
    out.append("\\end{document}\n")
    return "".join(out), n


def write_link(site, pages):
    with open(os.path.join(site, LINK), "w", encoding="utf-8") as f:
        f.write("# Written by scripts/make-book.py: the link to the whole "
                "collection as one PDF.\n")
        if pages:
            f.write("The whole collection as one PDF: [[file:%s][download]] "
                    "(%d pages).\n" % (BOOK, pages))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=".")
    args = ap.parse_args()
    site = os.path.abspath(args.site)
    guide = os.path.join(site, GUIDE)
    if not os.path.exists(guide):
        guide = os.path.join(ROOT, GUIDE)
    title, paragraphs, parts = read_guide(guide)
    date = datetime.datetime.now(datetime.timezone.utc)
    date = "%d %s" % (date.day, date.strftime("%B %Y"))
    tmp = tempfile.mkdtemp(prefix="make-book-")
    try:
        tex, n = master_tex(title, paragraphs, parts, site, date, commit_id())
        with open(os.path.join(tmp, "book.tex"), "w", encoding="utf-8") as f:
            f.write(tex)
        for _ in range(3):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", "book.tex"],
                               cwd=tmp, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            if r.returncode != 0:
                sys.stderr.write(r.stdout[-3000:])
                raise RuntimeError("pdflatex failed")
        log = open(os.path.join(tmp, "book.log"), encoding="latin-1").read()
        m = re.search(r"Output written on book\.pdf \((\d+) pages?", log)
        pages = int(m.group(1))
        shutil.copy(os.path.join(tmp, "book.pdf"), os.path.join(site, BOOK))
        write_link(site, pages)
        size = os.path.getsize(os.path.join(site, BOOK))
        print("make-book: %d sheets, %d pages, %.1f MB; wrote %s and %s"
              % (n, pages, size / 1e6, BOOK, LINK))
        return 0
    except Exception as e:
        print("make-book: FAILED: %s" % e, file=sys.stderr)
        write_link(site, None)
        try:
            os.remove(os.path.join(site, BOOK))
        except FileNotFoundError:
            pass
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
