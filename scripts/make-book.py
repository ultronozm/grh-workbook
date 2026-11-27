#!/usr/bin/env python3
"""Assemble the whole collection into one PDF, in the order of the index.

Usage:  python3 scripts/make-book.py --site DIR

Run after the sheets are built: DIR holds the per-sheet PDFs (in CI and
in preview-site.sh it is the build directory itself).  The script

  - reads the index (the guide) for the title, the opening paragraph and
    the order of the Overview, the Parts and their sheets;
  - writes a master LaTeX file that has a title page (title, the opening
    paragraph, date, commit), a table of contents by Part, and then
    every listed sheet's PDF, included page by page with pdfpages; each
    sheet gets a table-of-contents line and a PDF bookmark under its
    Part where applicable, and the pages are numbered continuously (the numbers of the
    contents and the PDF page labels);
  - compiles it with pdflatex and puts it at DIR/grh-via-exercises.pdf;
  - writes DIR/book-link.org, the index macros for the source commit date and
    the link to the PDF (with its page count when the build succeeds).

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

from workbook_index import GUIDE, overview_sheet

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
    opening = ""
    parts = []       # [(part title, [(id stem, label, title)])]
    for line in lines:
        m = re.match(r"#\+TITLE:\s*(.*)", line)
        if m:
            title = m.group(1).strip()
    # The opening paragraph is the first paragraph after the keywords.
    body = [l for l in lines if not l.startswith("#")]
    text = "\n".join(body)
    head = text.split("\n* ", 1)[0]
    paras = [p.strip() for p in re.split(r"\n\s*\n", head) if p.strip()]
    if paras:
        opening = paras[0]
    if overview := overview_sheet(text):
        ident, slug = overview
        parts.append(("", [(f"{ident}--{slug}__workbook", "", "Overview")]))
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
    return title, opening, parts


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


def master_tex(title, opening, parts, site, date, commit):
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
    out.append(org_to_latex(opening) + "\n\n")
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
        first = bool(part)
        for stem, num, name in sheets:
            pdf = os.path.join(site, stem + ".pdf")
            if not os.path.exists(pdf):
                raise FileNotFoundError(pdf)
            n += 1
            entries = []
            if first:
                entries.append("1,part,-1,{%s},part%d" % (escape_title(part), n))
                first = False
            heading = escape_title(name)
            if num:
                heading = r"\protect\numberline{%s}%s" % (escape_title(num), heading)
            entries.append("1,chapter,0,{%s},sheet%d" % (heading, n))
            out.append("\\includepdf[pages=-,addtotoc={%s}]{%s}\n"
                       % (",".join(entries), pdf))
    out.append("\\end{document}\n")
    return "".join(out), n


def write_link(site, pages):
    revision = os.environ.get("GITHUB_SHA") or "HEAD"
    stamp = subprocess.check_output(
        ["git", "show", "-s", "--format=%cs", revision], cwd=ROOT, text=True).strip()
    date = datetime.date.fromisoformat(stamp)
    with open(os.path.join(site, LINK), "w", encoding="utf-8") as f:
        f.write("# Written by scripts/make-book.py for the index.\n")
        f.write(f"#+MACRO: updated {date.day} {date:%B %Y}\n")
        if pages:
            f.write(f"#+MACRO: book-link @@html: · @@[[file:{BOOK}]"
                    f"[the whole collection as one PDF]] ({pages} pages)\n")
        else:
            f.write("#+MACRO: book-link @@html:@@\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=".")
    args = ap.parse_args()
    site = os.path.abspath(args.site)
    guide = os.path.join(site, GUIDE)
    if not os.path.exists(guide):
        guide = os.path.join(ROOT, GUIDE)
    title, opening, parts = read_guide(guide)
    date = datetime.datetime.now(datetime.timezone.utc)
    date = "%d %s" % (date.day, date.strftime("%B %Y"))
    tmp = tempfile.mkdtemp(prefix="make-book-")
    try:
        tex, n = master_tex(title, opening, parts, site, date, commit_id())
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
