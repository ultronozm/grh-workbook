# Standards for the sheets

Each sheet treats one ingredient of the argument, in its simplest setting, in the style of Onishchik–Vinberg's *Lie Groups and Algebraic Groups*: light prose, and quick problems that carry the argument.

**Form.**
- One sheet is one chapter: about 4–6 pages and 15–25 problems.  Split a longer topic rather than compress it.
- A short *Prerequisites* paragraph says what is assumed: earlier chapters by number, and standard textbooks by chapter.  Nothing is used before it is given.
- A problem is one statement, with at most two or three short parts.  A theorem that several problems prove is stated in the text after them.
- A problem states its conclusion; a computation gives the answer or a check value.  No bare "Determine" or "Compute".
- Prove the natural statement when it is no harder, then specialize it in the next problem.
- An earlier result is recalled by its statement, with `\ref`, not by a name alone.  A formula that is given rather than derived gets a problem deriving it or a sentence saying where it comes from.
- Background results are stated in the text with hypotheses and a reference, not set as problems.
- All hints are in one *Hints* section at the end of the file.  A hint names the starting point or the tool; it does not carry out the argument.
- There are no solutions.

**Notation.**
- Conventions (side of actions, matrix entries, normalizations) are fixed once for the whole workbook in the index; a sheet that departs from one says so in its Prerequisites.
- No letter has two meanings, and standard letters keep their standard meanings.  Drop subscripts that are constant throughout a sheet, and say so once.

**Sources.**
- Prefer published sources.  The expositions listed in the index's *Sources* section may also be cited.
- `STATUS.md` holds the dated status paragraph shown at the top of the index and a list of what changed in each update, newest first.  Each update that changes what the site shows appends an entry, and updates the status paragraph in both places when the coverage changes.
- Every citation is checked to exist, and every numerical claim is checked by computation.
- Alpöge is credited once, on the first page of the index.  In the running text of a sheet and in the body of the index, the proof is "the proof" or "the argument" (not "the rewritten Lean proof", "the rewriting", "Alpöge's proof" or "Alpöge's argument").  Each sheet has one remark "In the Lean formalization" that names the declarations and cites the repository as `[GL]`; only there may the text say "the Lean proof".  A contrast with the Lean code as first released or with an older exposition is kept only with a citation of a public source, and then says "the Lean code as first released".
- The rewritten Lean proof is cited as `[GL]`, with the same `\bibitem` text in every sheet (repository, commit `72fead1`, readable edition `grh/`); a statement read from it goes in a remark "In the Lean formalization" that names the declaration.

**Acceptance.**
A sheet is added only after an independent solver, given just the sheet, its hints, its prerequisites, the earlier sheets and the cited books, has worked every problem.  Problems found false, unclear, missing a step or needing an unstated result are fixed first.

**Numbering.**
The index `20261125T012000--grh-workbook__guide.org` is the only record of the chapter order; chapters are numbered 1, 2, 3, … in that order.  Never type a chapter, section, problem or theorem number.
- To insert a chapter, add one line for it to the index at its place, e.g. `- [[file:ID--slug__workbook.html][Title]] \\`, and rebuild with `./preview-site.sh`.  The label's number is filled in, and later chapters are renumbered, by `scripts/make-chapters.py`, which also writes `chapters.tex`.  Commit both.  Side-series entries keep the names in their labels (`S3. Title`).
- A sheet takes its number from the table: after `\newcounter{chap}`, write `\input{chapters}\chapnumber{ID}`, with `ID` the timestamp at the start of its file name.
- Never rename or delete a `pr:` label in a posted sheet; readers' solutions are keyed to them.  If a problem must go, keep its label on the replacement or note the change in the commit message.
- In prose, refer to other sheets by `\ref{xx-chap}`, `\ref{xx-pr:label}` and so on, with `\externaldocument[xx-]{…}` in the preamble; in the index, link to the sheet by title.
- `scripts/check-numbers.py`, run by `./preview-site.sh` and CI, fails on typed numbers outside `\cite[…]` and the bibliography.  A number that refers to another work (e.g. a chapter of Davenport outside a `\cite`) is allowed by a comment on its line: `% check-numbers: ok (Davenport): Ch.~12; Ch.~17`.

Build a sheet with `latexmk -pdf FILE.tex`; cross-sheet references use `xr`, so build earlier sheets first.  `./preview-site.sh` builds the whole site locally.

**Tags.**
Numbers change when chapters or problems are inserted; tags do not.  As in the Stacks project, every chapter, `\section` and labelled `problem`, `theorem`, `proposition`, `lemma` and `definition` of the settled parts (for now Parts I–V and the side series S1–S2; the list is `STABLE_PARTS` and `STABLE_SIDE` in `scripts/make-tags.py`; Part VI stays untagged until its chapters stop changing) has a four-character tag such as `2B7K`, recorded in `tags.tsv` as tag, sheet ID and label (empty for the chapter).  The HTML shows it in grey beside the item; `tag/2B7K.html` leads to the item wherever it is, and `tags.html` lists all tags.  The PDF does not show tags.
- After adding an item to a settled part, run `scripts/make-tags.py`, which appends tags for the untagged items, and commit `tags.tsv` with the sheet.  Never edit, reorder or delete a line of `tags.tsv`, and never reuse a tag.
- A tagged label must stay.  If its item must go, or changes beyond recognition, mark its line retired by adding a fourth column: `retired`, or `retired -> 2C3D` if the item `2C3D` replaces it, optionally followed by `; reason`.  A retired label may then be reused for a new item, which gets a new tag.
- When Part VI settles, add it to the stable list and run `scripts/make-tags.py`.
- A tag retired by mistake may be made live again only for a whole sheet listed, with its reason, in `UNRETIRED` in `scripts/make-tags.py`; `--check --since` then accepts it.  This was used once, for the three sheets withdrawn and restored on 26 November 2026 (Stepanov without multiplicity, S1, S2).
- A withdrawn sheet: retire all its tags, add a line for it to `scripts/withdrawn.tsv` (the site keeps a short page at its old URL), and remove it from the index.
- `scripts/make-tags.py --check`, run by `./preview-site.sh` and CI, fails if a tagged label has disappeared without being retired, if a tag or an item is listed twice, or if a committed line was changed or deleted; it warns about untagged items.  A line not yet committed may still be dropped.
