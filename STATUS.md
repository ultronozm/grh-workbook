# Status of the workbook

**Status, 26 November 2026.**  The collection is being extended to cover the complete proof and is updated continuously.  Parts I–V and the side series are stable apart from small corrections.  The proof itself now occupies four Parts.  Part VI fixes the data and all the objects, and deduces the theorem from Theorems A, B and C.  Part VIII now proves Theorem A from its inputs, each developed in a sheet, except two bounds (the projection to good forms; the dimension of the ramified forms) and the theorem on elementary divisors used at exceptional primes, which are stated from the Lean code.  Part IX develops the determinant of a chain and the cost of one lift, up to the auxiliary forms and one operator identity stated from the Lean code; its last two inputs, the denominators of projections and the twisting theorem, are stated with all their definitions and not proved here, apart from the local loss and a lemma on roots of unity.  In Part VII the first half of the second moment is developed (three sheets: unfolding, the terms that survive, good forms and the count); the main term is being developed.

The site is <https://ultronozm.github.io/grh-workbook/>.  Each update appends an entry below, newest first.

## What changed

### 26 November 2026: batch 6, the second moment (first half); the whole collection as one PDF

- **Three new sheets in Part VII:** *Unfolding twice: Gram operators as sums over rational points*, *Which terms survive: characters, minors and the gain at the level*, *Good forms and the count of the target*.
- ***Theorem B: enough forms*** now defines the Poincaré maps, the scaled Poincaré map and the Bessel representation, and says what an admissible filling is.  It keeps the second moment as one statement and takes the near isometry of the good forms and the count of the target from the new sheets.  *The seesaw identity* now uses its Poincaré maps.
- **One file.**  The whole collection is also available as one PDF, in the order of the index, with a contents page and bookmarks.  The link is on the index, below this paragraph.  The file is rebuilt with every update.
- **Checks:** each new sheet passed a fidelity audit and a solver test; the batch was read as a whole, with an extra fidelity pass.

### 26 November 2026: batch 5, Theorem A closed; the statement-level steps; the flowchart

- **Three new sheets.**  In Part VIII: *The level prime and the ramified forms* and *Exceptional primes: a full mark*.  In Part IX: *The local loss and the sparse places*.
- **Part VIII.**  *Theorem A* now deduces its statement from inputs that are references to sheets, except two bounds stated from the Lean code.  *Divisibility of the composite lift* takes over the theorem on elementary divisors from *Hecke nondegeneracy on the tree*.  *Divisibility along the chain* passes its general theorem to the new sheet on exceptional primes.
- **Part IX, statement-level chapters.**  *Denominators of projections to lifts* and *Twists with few congruences* now state every definition their theorems use.  The odd-class integer is written X_odd throughout.
- **Flowchart.**  The proof (Parts VI–IX) is again a separate section above Parts I–V: one tree per Part, all feeding *The main inequality*.
- **Checks:** each new sheet passed a fidelity audit and a solver test; the batch was read as a whole.  The two repaired chapters were audited again after the repair.

### 26 November 2026: batch 4, the seesaw

- **Four new sheets in Part VIII:** *Transferring a Bessel period through a theta lift*, *Two lifts at a time*, *Lattices, cuts and the ramified forms*, *The seesaw tensor: translated vacua, gluing and the unit*.
- ***The seesaw identity*** now defines the lower chain, the definite chain, chain data and the composite lift, and deduces the identity from the four sheets.
- **Checks:** final audit rounds by an independent Claude Opus auditor; batch read by Claude Fable.

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
