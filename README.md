# GRH via exercises

Short exercise sheets, one ingredient of the argument per sheet, in its simplest setting, in the style of Onishchik–Vinberg.  Start with the index `20261125T012000--grh-workbook__guide.org`, which gives the reading order and the expositions the sheets draw on.

Side series A: sign-only proofs of RH for curves and of Deligne's bound.

Build a sheet with `latexmk -pdf FILE.tex`.  Cross-sheet references use `xr`, so build earlier sheets first.  Chapter numbers come from the order of the index, through `chapters.tex`, which `scripts/make-chapters.py` generates; see `CONTRIBUTING.md`.

## Publishing

The workbook is published as a child of the TeX notes site machinery at <https://github.com/ultronozm/tex-site>, configured locally as the `upstream` remote.  Content lives here; reusable publishing machinery lives upstream.  To merge machinery changes: `git fetch upstream && git merge upstream/main`.

- Content and site-specific files: the sheets, the guide, `chapters.tex`, `scripts/`, `config.json`, `index.org` (the landing page, which includes the guide), `tex2html-local.el` (HTML postprocessing for problem numbers, citations and references), and `preview-site.sh`.
- Upstream-owned machinery (with one local step in `build.yml` that runs `scripts/`): `.github/workflows/build.yml`, `.github/workflows/make-index.yml`, `compile.sh`, `convert.sh`, `make-index.sh`, `tex2html.el` and `tex.css`.

CI compiles the sheets in file-name order and then recompiles each sheet that imports, via `xr`, a sheet compiled after it, so every cross-sheet reference resolves.

`./preview-site.sh` builds what the deploy branch would contain (PDFs, HTML, aux files, `index.html`, `listing.json`) into `_site/`, from `HEAD` plus uncommitted changes to tracked files; serve it with `python3 -m http.server -d _site`.

## Licence

The sheets and the index are licensed under the Creative Commons Attribution 4.0 International licence (`LICENSE`).
