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
- Every citation is checked to exist, and every numerical claim is checked by computation.

**Acceptance.**
A sheet is added only after an independent solver, given just the sheet, its hints, its prerequisites, the earlier sheets and the cited books, has worked every problem.  Problems found false, unclear, missing a step or needing an unstated result are fixed first.

**Numbering.**
The index `20261125T012000--grh-workbook__guide.org` is the only record of the chapter order; chapters are numbered 1, 2, 3, … in that order.  Never type a chapter, section, problem or theorem number.
- To insert a chapter, add one line for it to the index at its place, e.g. `- [[file:ID--slug__workbook.html][Title]] \\`, and rebuild with `./preview-site.sh`.  The label's number is filled in, and later chapters are renumbered, by `scripts/make-chapters.py`, which also writes `chapters.tex`.  Commit both.  Side-series entries keep the names in their labels (`A3. Title`).
- A sheet takes its number from the table: after `\newcounter{chap}`, write `\input{chapters}\chapnumber{ID}`, with `ID` the timestamp at the start of its file name.
- Never rename or delete a `pr:` label in a posted sheet; readers' solutions are keyed to them.  If a problem must go, keep its label on the replacement or note the change in the commit message.
- In prose, refer to other sheets by `\ref{xx-chap}`, `\ref{xx-pr:label}` and so on, with `\externaldocument[xx-]{…}` in the preamble; in the index, link to the sheet by title.
- `scripts/check-numbers.py`, run by `./preview-site.sh` and CI, fails on typed numbers outside `\cite[…]` and the bibliography.  A number that refers to another work (e.g. a chapter of Davenport outside a `\cite`) is allowed by a comment on its line: `% check-numbers: ok (Davenport): Ch.~12; Ch.~17`.

Build a sheet with `latexmk -pdf FILE.tex`; cross-sheet references use `xr`, so build earlier sheets first.  `./preview-site.sh` builds the whole site locally.
