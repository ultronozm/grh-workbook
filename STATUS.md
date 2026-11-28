# Status of the workbook

**Status, 27 November 2026.**  The collection is being extended to cover the complete proof and is updated continuously.  Parts I–V and the side series are stable apart from small corrections.  Parts VI–IX present the whole proof.  Part VI fixes the data and all the objects, and deduces the theorem from Theorems A, B and C.  Each of Parts VII–IX states its theorem in a chapter that deduces it from its inputs, and each input has a sheet.  A sheet proves a simplest instance or a model and the arithmetic of the constants; it then proves the general statement or states it from the Lean code, and ends with the list of what it took as given.

The site is <https://ultronozm.github.io/grh-workbook/>.  Each update appends an entry below, newest first.

## What is proved where

Proved here in general are the deductions: the theorem from A, B and C; Theorem B from three estimates, and the second moment from the estimates for the terms that survive and for the open cell, the link and cut bounds for the data from estimates for size, gain, count and tail, the sieve recurrence and its frequency sum from local bounds, and the normalization of the real Bessel functions from a lower bound for a period and Schur orthogonality; Theorem A from five inputs, including the spanning by short forms from lattice transference and the basis of products of minors, the good projection from translation compatibility and a class count, and the dimension bound for ramified forms from freeness at the enlarged levels, and the divisibility of the composite lift, with its count of gains, collisions and losses, from the bounds for one lift; Theorem C from four inputs, the auxiliary forms from the forms with short lifts, the factorization of the determinant of a chain from three identities for norms of lifts, the cost of one lift from its inputs, and the comparison operator from the statements about the gluing map; the bound for the denominators of projections from a bound for one clearing operator; the bound for the sum of the local losses over all primes, the existence of small twists from the polynomial input and the lemma on roots of unity; and the twisting theorem from small twists, Selmer data on lattices and the systems for Hecke ratios.  Part VIII works out the normal form and the two-place derivative count at 5 for a product of theta functions of one CM curve.  The general normal form for jet series at a non-split prime follows from the one-curve expansion and the theta-product factorization of a standard datum.  The same factorization gives jet integrality away from the primes dividing the cyclotomic conductor.   Three chapters of Part V state the Galois cohomology, crystalline lattice results and local comparison for attached representations used in Part IX.  The count of cocycles behind the tied primes follows from the Greenberg–Wiles formula.  Part VIII proves the root lemma for binary forms in one letter and in the two-letter field model.  What is stated from the Lean code and not proved is listed under [What is taken on trust](https://ultronozm.github.io/grh-workbook/20261127T100000--overview__workbook.html#sec:trust) in the Overview.

## What changed

### 28 November 2026. Terminology, definitions and Rubinstein's outline

Terms are now defined before use: *adelic frame*, *framed space* and *standard lattice* in *Spaces, forms and twists*, and the spaces $Y_j$ in *The data*.  Several overloaded words were replaced: the Bessel sense of "frame" is now *Bessel tuple* and *Bessel pairings*; "cut" in Part VII is *Bessel truncation*; "gain" in Part VII is *congruence saving*; "cell" in *Turns and the auxiliary forms* is *grid square*; "unit of loss" is *local loss allowance*; "defect" in Part VIII is *exponent defect*.  Part VI is now titled *Data, spaces and the main inequality*.  No labels, tags or file names changed.

Additions suggested by M. O. Rubinstein's outline of the shortened proof: in the Overview, the role of the second cutoff, the factor of two for squared lengths, why class 1 is used, the completion to a basis before the product formula, and a paragraph on how the Parts group; a problem on Frobenius and the partner place in *The places, the weights and the remainder*; a two-row diagram in *The seesaw identity*; a counterexample after the Cauchy–Schwarz problem in *Size against divisibility*; and two remarks in *The data* on where the window for $\log N$ and the bound $p \ge 13$ are used.

Later the same day: the Overview gains a table of the identities between lifts, the passage from the half-plane to the critical line, the two uses of twists and a first-pass reading path; *The main inequality* compares how the readable edition, the compact edition and the code as first released treat the second cutoff; *From zeros to a one-sided bound* has an optional problem on the Taylor-series argument behind Landau's theorem.

On the site, the button for feedback on a whole sheet is now at the end of the sheet, and the sync panel can show the sync code again.

### 27 November 2026. The main inequality in mean form

Two new problems: the remainder as a tail integral (Chapter 1) and the mean form of the main inequality, which shows the saving $1/m$ and the origin of the sixth logarithm (Chapter 3).  The existence theorem of *The data* now states only the three bounds used later, and its scale problem gives the number of decimal digits of $x$.  *The main inequality* compares the inequality with the one in the Lean code as first released, citing H. Nashida's note, and no longer repeats a deduction of Chapter 3.  Chapters 69 and 71 each gain a short explanation suggested by K. Jin's translation.  The Overview states Theorem C for all conjugates and explains the role of the term $H$.

### 27 November 2026. Overview

The optional Overview precedes Part I on the site and in the collected PDF.  It gives a short account of the proof, a table of the Parts, the statements taken on trust, and the notation shared by the sheets.

### 27 November 2026. The real places (batch 15)

*Black box: discrete series and the comparison of traces* collects the real discrete-series facts and states the trace comparison used in *Equal multiplicities*. *A Bessel function at a real place* derives the transformation law, normalization and correlation from a period bound and Schur orthogonality. *Theorem B* points to the real-place character in the rescaled frame, and *Good forms and the count of the target* cites the formal-degree formula.

### 27 November 2026. The twisting theorem (batch 13)

*A measure for Hecke values* computes models over \(\mathbb{Q}(i)\) and states the general systems for the Hecke ratios. *From a representation to a Selmer datum* bounds the terms of the datum and combines it with the small-twists theorem and the systems for the ratios. *Twists with few congruences* now cites this deduction.

### 27 November 2026. The root lemma in small cases (batch 16)

*Least terms and Pieri's inequalities* proves the root lemma for binary forms in one letter and in the two-letter field model. *A Hecke operator is nearly onto* points to these calculations and to the rank computation for deep forms. The general root lemma and the average remain statements read from the proof.

### 27 November 2026. Galois cohomology, crystalline lattices and local comparison (batch 12)

Three black-box chapters in Part V collect results used in Part IX. The Galois cohomology chapter derives the relation count in *Tied primes* from the Greenberg–Wiles formula. The chapters on crystalline lattices and Galois representations give references for the local inputs to the denominator bound.

### 27 November 2026. Frames and couplings (batch 10)

*Frames and couplings: the normal form at all places* deduces the normal form for standard data and proves jet integrality away from primes dividing the cyclotomic conductor. The one-lift and formal-group chapters now cite these deductions. *The bound is attained at many places* gives isotropic products at 3 and 5.

### 26 November 2026. The remaining terms and the sieve (batch 14)

*Size, gain and count: the remaining terms* deduces the bounds for links and the cut for the data. *The sieve over the entries* derives the recurrence, works one step modulo 25 and bounds the sum over frequencies. The corresponding chapters of Part VII and Theorem B now cite these deductions.

### 26 November 2026. Theorem A’s direct inputs (batch 11)

*Free levels and short bases* proves the short-spanning theorem and the standard-level class count. *The good part and the ramified forms* proves the good-projection bounds and the lower bound for the ramified dimension. Theorems A and B now cite these deductions. *Spaces, forms and twists* points to the free-level pairing and trivial stabilizers, and *The size of the composite lift* cites the standard-level count.

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
