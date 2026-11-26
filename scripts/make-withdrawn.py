#!/usr/bin/env python3
"""Answer the old URLs of withdrawn sheets.

For each line STEM <TAB> TITLE of scripts/withdrawn.tsv, write
DIR/STEM.html, a short page saying that the sheet was withdrawn and
linking to the index, and remove DIR/STEM.pdf and DIR/STEM.aux, which a
build may have carried forward from an earlier deploy.

Usage, from the repository root:  scripts/make-withdrawn.py --site DIR
"""
import html
import os
import sys

LIST = "scripts/withdrawn.tsv"
REPO = "https://github.com/ultronozm/grh-workbook"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Withdrawn: {title}</title>
<link rel="stylesheet" href="tex.css">
</head>
<body>
<div class="my-links-container"><a href="index.html" class="my-link">home</a></div>
<h1 class="title">{title}</h1>
<p>This sheet was withdrawn on 26 November 2026, when the workbook was
rebuilt around the rewritten Lean proof.  The present sheets are listed in
the <a href="index.html">index</a>.</p>
<p>The earlier version of the workbook is kept in the repository under the tag
<a href="{repo}/tree/original-route"><code>original-route</code></a>.</p>
</body>
</html>
"""


def main():
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "--site":
        sys.exit(__doc__.strip().split("\n")[-1])
    site = args[1]
    n = 0
    with open(LIST, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            stem, title = line.rstrip("\n").split("\t")
            if os.path.exists(stem + ".tex"):
                sys.exit(f"make-withdrawn: {stem}.tex exists; it is not withdrawn")
            for ext in (".pdf", ".aux"):
                p = os.path.join(site, stem + ext)
                if os.path.exists(p):
                    os.remove(p)
            with open(os.path.join(site, stem + ".html"), "w", encoding="utf-8") as out:
                out.write(PAGE.format(title=html.escape(title), repo=REPO))
            n += 1
    print(f"make-withdrawn: wrote {n} pages")


if __name__ == "__main__":
    main()
