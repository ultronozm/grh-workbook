# Status of the workbook

**Status, 26 November 2026.**  The collection is being extended to cover the complete proof and is updated continuously.  Parts I–V and the side series are stable apart from small corrections.  Part VI states every step of the proof, deduces Theorems A, B and C from their inputs and the main inequality from them; the proofs of the deeper inputs (the second moment, the seesaw identity, the divisibility of the composite lift, the determinant of a chain, the cost of one lift, the congruences) are stated from the Lean code and are being developed into further sheets.

The site is <https://ultronozm.github.io/grh-workbook/>.  Each update appends an entry below, newest first.

## What changed

### 26 November 2026

- **Redesign around the rewritten Lean proof.**  The sheets now follow the proof in the form of L. Sernau's rewritten Lean proof (`github.com/lsernau/grh-lean`, commit `72fead1`).
  - 28 sheets that served only the route of the Lean code as first released were withdrawn: windows, slopes, covolumes and the old later parts.  Their URLs show a short notice with a link to the index.
  - Eleven chapters are new: *A twist for each prime*, *The bound is attained*, and Part VI, *The proof* (ten chapters, from *The data* to *Theorem C and the main inequality*).
  - Parts I–V were adapted to the new proof.  Chapter numbers follow the index; tags of removed items are retired.
- **Coherence pass.**  There is now one notation standard for all chapters.  The spaces, forms and twists of Part VI are defined once, in *The data*.  References to a theorem point to the chapter that owns it.  Every chapter went through two further rounds of comparison with the Lean code.
- **Wording.**  Alpöge is credited on the first page.  Elsewhere the sheets say "the proof".  Each chapter has one remark, "In the Lean formalization", that names the Lean declarations.
- **Restored motivation chapters.**
  - *Stepanov without multiplicity* is back in Part II, before *The chain and the square root*.
  - The side series is back: *The sign-only proof of the Riemann hypothesis for curves* and *Deligne's bound by the sign-only method*, a model in the function-field setting that the proof does not use.
- **Snapshot.**  The collection and its flowchart as they stood on 25 November 2026 are kept, frozen and not maintained, at <https://ultronozm.github.io/grh-workbook/original-route/>.  The sources are under the tag `original-route`.
- **Index.**  Added this status paragraph, a link to the flowchart at the start of "How the sheets fit together", and an opening sentence for Notation.
- **Stable tags.**  Tags were assigned to the new items of Parts I–V, *Stepanov without multiplicity* and the side series.  Part VI stays untagged until its chapters stop changing.
