# Status of the workbook

**Status, 26 November 2026.**  The collection is being extended to cover the complete proof and is updated continuously.  Parts I–V and the side series are stable apart from small corrections.  Parts VI–IX present the whole proof.  Part VI fixes the data and all the objects, and deduces the theorem from Theorems A, B and C.  Each of Parts VII–IX states its theorem in a chapter that deduces it from its inputs, and each input has a sheet.  A sheet proves a simplest instance or a model and the arithmetic of the constants; it then proves the general statement or states it from the Lean code, and ends with the list of what it took as given.  Proved here in general are the deductions: the theorem from A, B and C; Theorem B from three estimates, and the second moment from the estimates for the terms that survive and for the open cell; Theorem A from five inputs, and the divisibility of the composite lift, with its count of gains, collisions and losses, from the bounds for one lift; Theorem C from four inputs, the auxiliary forms from the forms with short lifts, the factorization of the determinant of a chain from three identities for norms of lifts, the cost of one lift from its inputs, and the comparison operator from the statements about the gluing map; the bound for the denominators of projections from a bound for one clearing operator; the bound for the sum of the local losses over all primes, and the existence of small twists from a polynomial input, itself deduced from four statements read from the Lean code; and a lemma on roots of unity.  Part VIII works out the normal form and the two-place derivative count at 5 for a product of theta functions of one CM curve.  The general theorem uses the one-curve expansion, the factorization of the theta product for a standard datum, and an integrality statement for jets in several variables.  What is stated from the Lean code and not proved is listed in the index under *What is not proved here*.

The site is <https://ultronozm.github.io/grh-workbook/>.  Each update appends an entry below, newest first.

## What changed

### 26 November 2026. One curve at a non-split prime (batch 10, first chapter)

*The normal form of theta derivatives at a non-split prime* follows *One lift at a small non-split prime*. It computes the normal form and the derivative count for a product from one CM curve at 5. The one-lift and formal-group chapters point to the general theorem stated there.

### 26 November 2026: batch 9, instances and references

- **Sixteen new problems.**  The first parts work out a Mellin transform with three poles, the selection of places in a prime sum, and two matrix examples for congruences and traces.  The later parts give instances of the prime window, the main inequality, isotropic vectors over a finite field, the determinant of a chain, local derivatives and norms, the exchange factor and a local Gauss sum, a cyclotomic frame, the cost of a projection, and the local and character calculations for twists.
- **References.**  The sheets give sources for primes in progressions, forms on unitary groups, Poincaré series and theta lifts.  *Which terms survive* explains the factor $z_0^{-k}$ in the bound for a pair of terms.  Sources in the index now includes R. Di’s reconstruction and explains the use of R. Zhang’s note.
- **What is not proved here.**  The index now lists the inputs taken as given by Part, immediately after *How the sheets fit together*.  The status paragraph lists the deductions.
- **Audit corrections.**  *The comparison operator* corrects the determinant modulus and spells out the character and hypotheses used at the bottom of the tower.  *Two lifts at a time* distinguishes the norm-five model from the last pair of the chain and corrects the character in the triple action and the coordinates in the two-period hint.

### 26 November 2026. Reading progress on the website

- Mark problems as done on the HTML sheets. Chapter counts and the controls for exporting, importing and clearing progress are on the index. Marks are saved in the reader's browser.

### 26 November 2026: batch 8, seven further sheets; the denominators split; Sources

- **Seven new sheets.**  In Part VIII: *A Hecke operator is nearly onto*.  In Part IX: *Turns and the auxiliary forms*, *The comparison operator*, *Congruences bounded by lengths*, *Auxiliary primes: even classes at no cost*, *Lengths as values of polynomials*, *Tied primes*.  Each takes over a statement that its chapter had read from the Lean code.  It either deduces that statement from narrower statements read from the code, or states it with a model and its accounting (*A Hecke operator is nearly onto*).  The status paragraph names what is still read from the code.
- **Statement chapters.**  *The cost of one lift* cites the comparison operator from its sheet.  *The determinant of a chain* and *Theorem C* cite the auxiliary forms from theirs.  *Divisibility of the composite lift* passes its theorem on elementary divisors to the new sheet.  *Twists with few congruences* takes Selmer data, Stickelberger systems and the polynomial input from *Lengths as values of polynomials*.  *Denominators of projections to lifts* says where its theorem is deduced.
- **Denominators of projections to lifts, split.**  Its first three sections are now the model sheet *Clearing a projection: two classes*.  The statement chapter defines its local terms and the Hecke polynomial operator, and gains a running instance in rank one.
- ***Two lifts at a time*** is rewritten around the last pair, worked out first in a lattice model.
- **Sources.**  A new group, expositions of the proof in its rewritten form, with M. Bolan's manuscript.
- **Checks:** each new sheet went through fidelity audits against the code and solver tests; the batch was read as a whole.

### 26 November 2026: second coherence pass over Parts VI–IX

- **Status paragraph.**  Rewritten after a reading of Parts VI–IX as a whole.  It now separates what is proved here (the deductions) from what is stated from the Lean code, Part by Part.  The index also corrects one sentence in "How the sheets fit together" and four synopses, and lists Part VIII in the order D1, D2, D3, D5, D6.
- **Wording.**  Sentences in the sheets that said more was proved than is proved were corrected.  The same phrase is now used throughout for a statement taken from the proof: "read from the proof; not proved here".
- **The chain of deductions.**  *The seesaw identity* names the seesaw constant.  *Divisibility of the composite lift* connects the theorem on elementary divisors to the estimate it is used for.  *Theorem A* proves the two inequalities on the data that it uses.  *Theorem C* states its input (b) with a problem.  *The determinant of a chain* now proves the small-ratios statement with two problems; it was stated from the Lean code before.  Several input numbers, signs and references were corrected.
- **Definitions in one place.**  The gauge, the final level and its character, and the Petersson product are now defined in *Spaces, forms and twists*; *Theorem B* gains admissible fillings as a numbered definition.  Duplicated problems and sums were removed.
- **Checks.**  Every chapter whose statements read from the Lean code changed was audited again against the code and the findings were applied.

### 26 November 2026: where the inputs of the main inequality come from

- ***The main inequality*** now says, for each input, where it comes from: (A1) and (A2) are parts (a) and (b) of Theorem A in the notation of the chapter, (B) is a consequence of Theorem B, and Theorem C is quoted in full.  A new sentence says that the three theorems are proved in Parts VIII, VII and IX and that the chapter uses only their statements.

### 26 November 2026: batch 7, the second moment (second half); the whole proof

- **Two new sheets in Part VII:** *The open cell: Siegel's formula and Poisson summation* and *Positive type and the bootstrap: the second moment*.
- ***Theorem B: enough forms*** now takes its second moment from the second of these; the theorem *the second moment* leaves the chapter.  *Which terms survive* and *Good forms and the count of the target* point to the new statement.
- **Status.**  Parts VI–IX now present the whole proof.  The paragraph above lists what is stated and not proved here.
- **Checks:** each new sheet passed a fidelity audit and a solver test; the batch was read as a whole, with an extra fidelity pass.

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
