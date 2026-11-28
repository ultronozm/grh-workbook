# GRH via exercises

Short exercise sheets presenting Alpöge's proof of the generalized Riemann hypothesis for Dirichlet $L$-functions, following the rewritten Lean proof (<https://github.com/lsernau/grh-lean>, commit `72fead1`, on which the Lean community's repository is now based), in the style of Onishchik–Vinberg.  Parts I–V treat one ingredient per sheet in its simplest setting; Part VI states the ingredients in the generality of the proof and deduces the theorem.  Start with the index `20261125T012000--grh-workbook__guide.org`, which gives the reading order and the sources.

The earlier version of the workbook, which followed the Lean code as first released, is kept under the tag `original-route`.  The site as built from it on 25 November 2026 is kept, frozen, in the directory `original-route/` (static files, not processed by the build; served at `original-route/`).  Its withdrawn sheets are listed in `scripts/withdrawn.tsv`; the site answers their old URLs with a short page that links to the index (`scripts/make-withdrawn.py`).

Build a sheet with `latexmk -pdf FILE.tex`.  Cross-sheet references use `xr`, so build earlier sheets first.  Chapter numbers come from the order of the index, through `chapters.tex`, which `scripts/make-chapters.py` generates; see `CONTRIBUTING.md`.

## Publishing

The workbook is published as a child of the TeX notes site machinery at <https://github.com/ultronozm/tex-site>, configured locally as the `upstream` remote.  Content lives here; reusable publishing machinery lives upstream.  To merge machinery changes: `git fetch upstream && git merge upstream/main`.

- Content and site-specific files: the sheets, the guide, `chapters.tex`, `scripts/`, `config.json`, `index.org` (the landing page, which includes the guide), `tex2html-local.el` (HTML postprocessing for problem numbers, citations and references), and `preview-site.sh`.
- Upstream-owned machinery (with one local step in `build.yml` that runs `scripts/`): `.github/workflows/build.yml`, `.github/workflows/make-index.yml`, `compile.sh`, `convert.sh`, `make-index.sh`, `tex2html.el` and `tex.css`.

CI compiles the sheets in file-name order and then recompiles each sheet that imports, via `xr`, a sheet compiled after it, so every cross-sheet reference resolves.

`./preview-site.sh` builds what the deploy branch would contain (PDFs, HTML, aux files, `index.html`, `listing.json`) into `_site/`, from `HEAD` plus uncommitted changes to tracked files; serve it with `python3 -m http.server -d _site`.

## Licence

The sheets and the index are licensed under the Creative Commons Attribution 4.0 International licence (`LICENSE`).
