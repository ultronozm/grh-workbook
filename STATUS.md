# Status of the workbook

**Status, 26 November 2026.**  The collection is being extended to cover the complete proof and is updated continuously.  Parts I–V and the side series are stable apart from small corrections.  The proof itself now occupies four Parts.  Part VI fixes the data and all the objects, and deduces the theorem from Theorems A, B and C.  Parts VII, VIII and IX state Theorems B, A and C, deduce each from its inputs, and state those inputs from the Lean code; the proofs of the inputs are being developed into further sheets, which will appear in batches after the chapter that states the result.  Developed so far: in Part VIII, the divisibility of one lift at a small non-split prime and the size of the composite lift; in Part IX, the determinant of a chain of lifts (four sheets: the norm of one lift, equal multiplicities, the exchange identity, the factorization) and the cost of one lift (four sheets), up to one operator identity stated from the Lean code.

The site is <https://ultronozm.github.io/grh-workbook/>.  Each update appends an entry below, newest first.

## What changed

### 26 November 2026: batch 3, the cost of one lift

- **Four new sheets in Part IX:** *Compressions and false lifts*, *Hecke values as norms of lifts*, *The bound is attained at many places*, *Test forms and the height of a Hecke ratio*.
- ***The cost of one lift*** is cut to its statement and deduction.  The comparison operator stays stated from the Lean code.
- ***The bound is attained*** passes the twelve-copy theorem to the new sheet.
- **Checks:** final audit rounds by an independent Claude Opus auditor; batch read by Claude Fable.

### 26 November 2026: batch 2, the determinant of a chain

- **Four new sheets in Part IX:** *The norm of one lift*, *Equal multiplicities*, *The exchange identity*, *Squares and the triangle*.
- ***The determinant of a chain*** keeps the factorization and recalls the four inputs from the new sheets.
- **Checks:** final audit rounds by an independent Claude Opus auditor; batch read by Claude Fable.

### 26 November 2026: batch 1, divisibility at a small prime and the size

- **Three new sheets in Part VIII:** *The count: congruences, directions and factorials*, *One lift at a small non-split prime*, *The size of the composite lift*.
- ***Divisibility of the composite lift*** now defines the gauge, weak chain data and the restricted chain.  Two of its inputs are now references to the new sheets.
- ***Theorem A*** passes its section on the exponent and the size theorem to *The size of the composite lift*.
- **Checks:** each new sheet passed a fidelity audit against the Lean code and a solver test; the batch was read as a whole.  The final audit rounds were done by an independent Claude Opus auditor and the batch read by Claude Fable.

### 26 November 2026, later: the frame (batch 0)

- **Four Parts for the proof.**  The former Part VI is now four Parts:
  - VI *The frame*: *The data*, *Spaces, forms and twists*, *The main inequality*;
  - VII *Theorem B: enough forms*;
  - VIII *Theorem A: short forms*, with *The seesaw identity* and *Divisibility of the composite lift*;
  - IX *Theorem C: the lower bound*, with the determinant of a chain, the cost of one lift, the denominators and the twisting theorem.
- **New chapters, made by splitting present ones.**
  - *Spaces, forms and twists* is the last section of *The data*, now the one home of every object the proof attaches to the data.  It gains definitions of the valuation, the diagram of weights, critical pairs and the target lattice.
  - *Theorem C* is the first half of the former *Theorem C and the main inequality*; the rest is *The main inequality*.
  - *Roots of unity for many polynomials* is the first two sections of *Twists with few congruences*, with three new check problems.
- **Flowchart.**  One column per Part; the Parts of the proof are shaded.

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
