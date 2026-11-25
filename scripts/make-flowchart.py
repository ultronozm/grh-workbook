#!/usr/bin/env python3
"""Draw how the chapters depend on each other, and render the seminar plans.

Everything is read from the sources, so the chart follows the index:

  * the index (the guide) gives the chapters, their order, numbers,
    titles, IDs and Parts;
  * each sheet's \\externaldocument lines name the sheets it cites, and
    the references in its Prerequisites paragraph say which of them it
    builds on (references to later chapters are pointers, not
    prerequisites, and are dropped);
  * the Parts after Part V (the later parts) state the ingredients in
    general; the last of them holds only the assembly, the last chapter
    of the main sequence.  In the other later parts, a chapter with a
    Deliverable paragraph is a module: its Prerequisites and its
    "Simplest incarnation" remarks name the earlier chapters it
    generalizes, and the inputs (A1)-(A7), (V1)-(V3), (W1)-(W4) of the
    assembly that it supplies are read from its Deliverable paragraph and
    from the assembly's map of the inputs (the description list in its
    section sec:map), keeping the labels on which both agree.  The other
    chapters of those parts develop inputs of the modules and supply
    nothing to the assembly directly;
  * the sentence opening a later part names the Part among I-V that
    treats it in its simplest setting ("... what Part III treats ...").

The chart has two grids.  Below, one column per Part I-V, the chapters
of a Part stacked with the earliest at the bottom.  Above, one column per
later part, placed over the column of its counterpart among Parts I-V,
with its modules on top and its other chapters below in index order; the
assembly is on top of everything.  Edges into the upper grid enter boxes
from the side.  Edges implied by a path are dropped (transitive
reduction).  The layout and the orthogonal edge routing are done here,
so Graphviz is not needed; a DOT file is written as well, for reference.

Outputs (in the current directory, or --outdir):
  flowchart.org   the page: the chart inline, a legend, the seminar plans
  flowchart.svg   the chart alone
  flowchart.dot   the same graph for Graphviz

The seminar plans are kept in scripts/seminar-plans.json, keyed by sheet
ID, and rendered with the current chapter numbers and links.  Section
and theorem numbers in the plans are checked against the sheets' .aux
files where these exist (a warning, not an error).

Run from the repository root.  ./preview-site.sh and CI run it on every
build and export flowchart.org to flowchart.html.
"""
import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict

GUIDE = "20261125T012000--grh-workbook__guide.org"
PLANS = "scripts/seminar-plans.json"

LINK = re.compile(
    r"^\s*- \[\[file:(?P<id>\d{8}T\d{6})--(?P<slug>[^\]]*?)__workbook\.html\]"
    r"\[(?P<label>[^\]]*)\]\]")
LABEL = re.compile(r"^(?P<num>[A-Z]*\d+)\.\s+(?P<title>.*)$")
EXTDOC = re.compile(
    r"^[ \t]*\\externaldocument\[(?P<pre>[^\]]*)\]\{(?P<id>\d{8}T\d{6})--", re.M)
REF = re.compile(r"\\(?:eq|auto|c|C)?ref\{(?P<pre>[A-Za-z]+-)")
INPUT = re.compile(r"\((?P<l>[AVWK])(?P<a>\d)\)(?:\s*--+\s*\((?P=l)(?P<b>\d)\))?")

# The conditions (K1)-(K8) of a chain record [Adr, Def. 18.9] and the
# inputs (A1)-(A7) of the assembly that they give [Adr, Prop. 18.14],
# as the Deliverable paragraphs of the modules use them: (K4) and (K6)
# go into the height bound (A4), the first inequalities of (K7) and (K8)
# into (A6) and (A7).
K_TO_A = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 4, 7: 6, 8: 7}


def die(msg):
    sys.exit(f"make-flowchart: {msg}")


def warn(msg):
    print(f"make-flowchart: warning: {msg}", file=sys.stderr)


# ---------------------------------------------------------------- reading

class Sheet:
    def __init__(self, ident, slug, num, title, part, part_name, side):
        self.id, self.slug, self.num, self.title = ident, slug, num, title
        self.part, self.part_name, self.side = part, part_name, side
        self.tex = f"{ident}--{slug}__workbook.tex"
        self.html = f"{ident}--{slug}__workbook.html"

    def __repr__(self):
        return f"<{self.num}>"


def read_index():
    """Return the sheets in index order and the Parts as (key, name, ids)."""
    with open(GUIDE, encoding="utf-8") as f:
        guide = f.read()
    sheets, parts = [], []
    heading = None
    for line in guide.split("\n"):
        if line.startswith("* "):
            heading = line[2:].strip()
            continue
        m = LINK.match(line)
        if not m or heading is None:
            continue
        lm = LABEL.match(m.group("label"))
        if not lm:
            die(f"index entry {m.group('id')} has no number in its label; "
                "run scripts/make-chapters.py first")
        side = "side series" in heading.lower()
        pm = re.match(r"^(Part [IVXLC]+)\.\s*(.*)$", heading)
        key, name = (pm.group(1), pm.group(2)) if pm else (heading, "")
        s = Sheet(m.group("id"), m.group("slug"), lm.group("num"),
                  lm.group("title").strip(), key, name, side)
        sheets.append(s)
        if not parts or parts[-1][0] != key:
            parts.append((key, name, []))
        parts[-1][2].append(s.id)
    return sheets, parts


def read_counterparts():
    """Map each Part whose opening sentence names another Part ("what
    Part III treats") to that Part."""
    with open(GUIDE, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out = {}
    for k, line in enumerate(lines[:-1]):
        pm = re.match(r"^\* (Part [IVXLC]+)\.", line)
        if not pm or lines[k + 1].startswith(("-", "*")):
            continue
        cm = re.search(r"what (Part [IVXLC]+) treats", lines[k + 1])
        if cm:
            out[pm.group(1)] = cm.group(1)
    return out


def paragraph(src, name):
    """The text of \\paragraph{NAME.} up to the next blank line or section."""
    m = re.search(r"\\paragraph\{" + name + r"\.?\}(?:\\label\{[^}]*\})?(.*?)"
                  r"(?:\n[ \t]*\n|\\section|\\begin\{thebibliography\})",
                  src, re.S)
    return m.group(1) if m else ""


def prefixes(text):
    return {m.group("pre") for m in REF.finditer(text)}


def strip_tex(text):
    """Drop citations, math and comments, so that sentences split cleanly."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(r"\\cite(?:\[[^\]]*\])?\{[^}]*\}", "CITE", text)
    text = re.sub(r"\\\((.*?)\\\)", "MATH", text, flags=re.S)
    text = re.sub(r"\$[^$]*\$", "MATH", text)
    return text


def labels(text):
    out = []
    for m in INPUT.finditer(text):
        a = int(m.group("a"))
        b = int(m.group("b") or a)
        out += [f"{m.group('l')}{i}" for i in range(a, b + 1)]
    return out


def delivered(text):
    """The inputs a module's Deliverable paragraph says it supplies.

    A sentence counts if it says that something supplies or gives; a
    sentence that says the chapter proves none of them, or only names
    what enters them, or lists other inputs alongside, does not."""
    out = []
    for sent in re.split(r"(?<=[.])\s+(?=[A-Z\\])", strip_tex(text)):
        if not re.search(r"\b(suppl(?:y|ies)|gives?)\b", sent):
            continue
        if re.search(r"\b(none|enter|Alongside)\b", sent):
            continue
        for lab in labels(sent):
            if lab[0] == "K":
                lab = f"A{K_TO_A[int(lab[1:])]}"
            if lab not in out:
                out.append(lab)
    return out


def read_sheets(sheets):
    """Return (deps, deliveries, inputs, assembly, modules, src, devs, parent)."""
    by_id = {s.id: s for s in sheets}
    pos = {s.id: k for k, s in enumerate(sheets)}
    main = [s for s in sheets if not s.side]
    assembly = main[-1]
    src = {}
    pre = {}
    for s in sheets:
        with open(s.tex, encoding="utf-8") as f:
            src[s.id] = f.read()
        pre[s.id] = {m.group("pre"): m.group("id")
                     for m in EXTDOC.finditer(src[s.id])}

    def resolve(s, pres, where):
        out = set()
        for p in pres:
            t = pre[s.id].get(p)
            if t is None:
                warn(f"{s.tex}: {where} cites prefix {p} without "
                     "\\externaldocument")
            elif t not in by_id:
                warn(f"{s.tex}: {where} cites {t}, which is not in the index")
            elif pos[t] < pos[s.id]:
                out.add(t)
        return out

    deps = {}
    for s in sheets:
        para = paragraph(src[s.id], "Prerequisites")
        if not para:
            warn(f"{s.tex} has no Prerequisites paragraph")
        deps[s.id] = resolve(s, prefixes(para), "Prerequisites")

    # The later parts: from the first Part with a Deliverable paragraph
    # to the Part of the assembly.  Their chapters other than the
    # assembly are modules (with a Deliverable paragraph) or developments.
    order = list(dict.fromkeys(s.part for s in main))
    has_del = [s.part for s in main if s is not assembly
               and paragraph(src[s.id], "Deliverable")]
    first = order.index(has_del[0]) if has_del else order.index(assembly.part)
    later = set(order[first:])
    upper = [s for s in main if s.part in later and s is not assembly]
    modules = [s for s in upper if paragraph(src[s.id], "Deliverable")]
    devs = [s for s in upper if s not in modules]

    for s in sheets:
        if s in modules:
            for m in re.finditer(r"Simplest incarnation\}?:?(.*?)(?:Status|\n[ \t]*\n)",
                                 src[s.id], re.S):
                deps[s.id] |= resolve(s, prefixes(m.group(1)),
                                      "Simplest incarnation")

    deliveries = {}
    for s in modules:
        # A module without a Deliverable paragraph (the first chapter of
        # the Part, which fixes the objects) supplies nothing directly.
        deliveries[s.id] = delivered(paragraph(src[s.id], "Deliverable"))

    # The assembly's map of the inputs: each item names the inputs and
    # the chapters of the last Part whose deliverables supply them.  An
    # item that names a range of chapters has no single supplier.
    a_src = src[assembly.id]
    m = re.search(r"\\label\{sec:map\}(.*?)\\begin\{description\}(.*?)"
                  r"\\end\{description\}", a_src, re.S)
    mod_ids = {s.id for s in modules}
    from_map = defaultdict(list)
    inputs = []
    if not m:
        warn(f"{assembly.tex}: no description list in section sec:map")
    else:
        deps[assembly.id] |= resolve(assembly, prefixes(m.group(1)), "sec:map")
        for item in re.split(r"\\item\[", m.group(2))[1:]:
            head, _, body = item.partition("]")
            head = re.sub(r"\\eqref\{([A-Z]\d)\}", r"(\1)", head)
            labs = labels(head)
            inputs += [l for l in labs if l not in inputs]
            if re.search(r"\\ref\{[^}]*\}\s*--+\s*\\ref", body):
                continue
            for t in resolve(assembly, prefixes(body), "sec:map") & mod_ids:
                from_map[t] += [l for l in labs if l not in from_map[t]]
    # A module supplies an input if both the map and its Deliverable
    # paragraph say so; if only one of them names inputs, that one.
    for t in mod_ids:
        a, b = from_map.get(t, []), deliveries.get(t, [])
        both = [l for l in a if l in b]
        deliveries[t] = sorted(both or a or b,
                               key=lambda l: ("AVWK".index(l[0]), int(l[1:])))
    return deps, deliveries, inputs, assembly, modules, src, devs


# ---------------------------------------------------------------- graph

def build_graph(sheets, parts):
    (deps, deliveries, inputs, assembly, modules, src,
     devs) = read_sheets(sheets)
    mod_ids = {s.id for s in modules}
    upper = mod_ids | {s.id for s in devs} | {assembly.id}
    edges = {}          # (u, v) -> kind: dep, inc, del

    def kind(u, v):
        """Light (inc) for an earlier part's chapter into a module or the
        assembly, dark (dep) otherwise."""
        return ("inc" if (v in mod_ids or v == assembly.id)
                and u not in upper else "dep")

    for v, us in deps.items():
        for u in us:
            edges[(u, v)] = kind(u, v)
    supplier = defaultdict(list)
    for mid, labs in deliveries.items():
        for lab in labs:
            supplier[lab].append(mid)
        if labs:
            edges[(mid, assembly.id)] = "del"

    succ = defaultdict(set)
    for (u, v) in edges:
        succ[u].add(v)

    def reaches(a, b, skip=None):
        stack, seen = [x for x in succ[a] if (a, x) != skip], set()
        while stack:
            x = stack.pop()
            if x == b:
                return True
            if x not in seen:
                seen.add(x)
                stack.extend(succ[x])
        return False

    reduced = {e: k for e, k in edges.items()
               if k == "del" or not reaches(e[0], e[1], skip=e)}
    unsupplied = [l for l in inputs if l not in supplier]
    return dict(edges=reduced, deliveries=deliveries, assembly=assembly,
                modules=modules, unsupplied=unsupplied, src=src,
                devs=devs, counterpart=read_counterparts())


# ---------------------------------------------------------------- layout

FS = 11.5            # node font size
LH = 13.5            # line height
CHAR = 0.53 * FS     # average character width (sans-serif), a bit generous
WIDTH = 1200
MARGIN = 6
LANE = 6             # spacing of parallel edges
PAD = 7              # cluster padding


def wrap(text, width_px, max_lines=4):
    per = max(8, int(width_px / CHAR))
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > per:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(",;:") + "…"
    return lines


def assign_lanes(intervals):
    """Greedy interval colouring.  intervals: {key: (lo, hi)}."""
    lanes, ends = {}, []
    for key, (lo, hi) in sorted(intervals.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        for i, end in enumerate(ends):
            if end < lo - 2:
                lanes[key] = i
                ends[i] = hi
                break
        else:
            lanes[key] = len(ends)
            ends.append(hi)
    return lanes, len(ends)


def layout(sheets, parts, g):
    """Two grids.  Below, one column per Part I-V, the chapters of a Part
    stacked with the earliest at the bottom.  Above, one column per later
    part, over the column of its counterpart, its modules on top and its
    other chapters below in index order; the assembly on top of all.  Edges inside the lower grid run in
    its gutters and in the gaps below the rows; edges into the last Part
    cross the transfer gap below it and enter boxes from the side through
    the gutters of the upper grid."""
    by_id = {s.id: s for s in sheets}
    assembly, modules = g["assembly"], g["modules"]
    mod_ids = [s.id for s in modules]
    dev_ids = [s.id for s in g["devs"]]
    six = set(mod_ids) | set(dev_ids)
    up_parts = [p for p in parts if any(i in six for i in p[2])]
    up_keys = {p[0] for p in up_parts} | {assembly.part}
    col_parts = [p for p in parts if p[0] not in up_keys
                 and not by_id[p[2][0]].side]
    side_parts = [p for p in parts if by_id[p[2][0]].side]
    C = len(col_parts)
    col_of, row_of = {}, {}
    for c, (_, _, ids) in enumerate(col_parts):
        for r, i in enumerate(reversed(ids)):
            col_of[i], row_of[i] = c, r
    rows = max(len(p[2]) for p in col_parts)
    clusters = [(f"{k}. {n}" if n else k, ids) for k, n, ids in col_parts]
    for key, name, ids in side_parts:
        used = [sum(1 for i in col_of if col_of[i] == c) for c in range(C)]
        c = min(range(C), key=lambda c: (used[c], -c))
        start = used[c] + 1
        for r, i in enumerate(reversed(ids)):
            col_of[i], row_of[i] = c, start + r
        rows = max(rows, start + len(ids))
        clusters.append((f"{key}. {name}" if name else key, ids))

    # The upper grid: a column per later part, over its counterpart's
    # column if the counterparts are distinct Parts I-V; modules first.
    low_col = {k: c for c, (k, _, _) in enumerate(col_parts)}
    cp = [low_col.get(g["counterpart"].get(k)) for k, _, _ in up_parts]
    if (len(up_parts) == len(col_parts) and None not in cp
            and len(set(cp)) == len(cp)):
        up_col = cp
    else:
        up_col = list(range(len(up_parts)))
    K = max(up_col) + 1 if up_col else 1
    col6, lvl = {}, {}
    for (_, _, ids), c in zip(up_parts, up_col):
        ids = ([i for i in ids if i in mod_ids]
               + [i for i in ids if i not in mod_ids])
        for L, i in enumerate(ids):
            col6[i], lvl[i] = c, L
    levels = 1 + max(lvl.values(), default=0)

    edges = g["edges"]
    plan = {}
    for (u, v), k in edges.items():
        if k == "del":
            continue
        if v in six and u in six:
            if col6[u] == col6[v] and lvl[v] == lvl[u] + 1:
                plan[(u, v)] = ("down",)
            elif col6[u] == col6[v] and lvl[u] == lvl[v] + 1:
                plan[(u, v)] = ("rise",)
            else:
                plan[(u, v)] = ("six",)
        elif v in six:
            plan[(u, v)] = ("up",)
        else:
            cu, ru, cv, rv = col_of[u], row_of[u], col_of[v], row_of[v]
            if cu == cv and ru == rv + 1:
                plan[(u, v)] = ("straight",)
            else:
                gut, side = (cu + 1, "R") if cv > cu else (cu, "L")
                plan[(u, v)] = ("routed", gut, side, rv)

    # Sides and gutters in the upper grid.  Gutter k lies left of column k.
    # Estimated x (in column units) of a lower-grid gutter, to pick sides.
    def lower_gut_frac(gut):
        return gut / C
    def six_frac(v):
        return (col6[v] + 0.5) / K
    six_side = {}      # (edge, end) -> ("L"|"R", gutter index)
    for e, p in plan.items():
        u, v = e
        if p[0] == "up":
            cu = col_of[u]
            vx = six_frac(v)
            gut, side = (cu + 1, "R") if vx > (cu + 0.5) / C else (cu, "L")
            plan[e] = ("up", gut, side)
            if lower_gut_frac(gut) <= vx:
                six_side[(e, "v")] = ("L", col6[v])
            else:
                six_side[(e, "v")] = ("R", col6[v] + 1)
        elif p[0] == "six":
            if col6[u] == col6[v]:
                six_side[(e, "u")] = ("L", col6[u])
                six_side[(e, "v")] = ("L", col6[v])
            elif col6[v] > col6[u]:
                six_side[(e, "u")] = ("R", col6[u] + 1)
                six_side[(e, "v")] = ("L", col6[v])
            else:
                six_side[(e, "u")] = ("L", col6[u])
                six_side[(e, "v")] = ("R", col6[v] + 1)

    # Lanes in the upper gutters, from intervals in level units: the box
    # at level L is at L, the gap below it at L + 0.5, the transfer gap
    # below the whole grid at `levels`.
    six_iv = defaultdict(dict)
    hop_iv = defaultdict(dict)       # gap level -> {edge: (gut_u, gut_v)}
    for e, p in plan.items():
        u, v = e
        if p[0] == "up":
            gut = six_side[(e, "v")][1]
            six_iv[gut][e] = (lvl[v], levels)
        elif p[0] == "six":
            gu, gv = six_side[(e, "u")][1], six_side[(e, "v")][1]
            if gu == gv:
                six_iv[gu][e] = (min(lvl[u], lvl[v]), max(lvl[u], lvl[v]))
            else:
                h = max(lvl[u], lvl[v]) + 0.5
                six_iv[gu][(e, "u")] = (lvl[u], h)
                six_iv[gv][(e, "v")] = (lvl[v], h)
                hop_iv[h][e] = (min(gu, gv), max(gu, gv))
    lanes6, n6 = {}, {}
    for gut, iv in six_iv.items():
        ln, n = assign_lanes({k: (a * 10, b * 10) for k, (a, b) in iv.items()})
        lanes6.update(ln)
        n6[gut] = n
    GW6 = max(28, 2 * PAD + 6 + max(n6.values(), default=1) * LANE)
    BW6 = (WIDTH - 2 * MARGIN - (K + 1) * GW6) / K

    def col6_x(c):
        return MARGIN + GW6 + c * (BW6 + GW6)

    def gut6_x(gut, key):
        left = MARGIN + gut * (BW6 + GW6)
        n = n6.get(gut, 1)
        return left + GW6 / 2 + (lanes6[key] - (n - 1) / 2) * LANE

    # The lower grid: gutter lanes, with the "up" edges rising to gap -1.
    gutter_lanes = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            _, gut, side, gap = p
            ru = row_of[e[0]]
            gutter_lanes[gut][e] = (min(ru, gap + 0.5), max(ru, gap + 0.5))
        elif p[0] == "up":
            gutter_lanes[p[1]][e] = (-0.5, row_of[e[0]])
    lanes_g, nlanes_g = {}, {}
    for gut, iv in gutter_lanes.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        lanes_g.update(ln)
        nlanes_g[gut] = n
    maxl = max(nlanes_g.values(), default=1)
    GW = max(36, 2 * PAD + 10 + maxl * LANE)
    if K == C:
        # One column grid for both, so that a later part sits exactly
        # over its counterpart.
        GW = GW6 = max(GW, GW6)
    BW = (WIDTH - 2 * MARGIN - (C + 1) * GW) / C
    BW6 = (WIDTH - 2 * MARGIN - (K + 1) * GW6) / K

    def col_x(c):
        return MARGIN + GW + c * (BW + GW)

    def gutter_x(gut, lane, n):
        left = MARGIN + gut * (BW + GW)
        mid = left + GW / 2
        return mid + (lane - (n - 1) / 2) * LANE

    a_w = min(2 * BW + GW, WIDTH - 2 * MARGIN)
    a_x = WIDTH / 2 - a_w / 2

    lines = {}
    for s in sheets:
        if s.id in six:
            lines[s.id] = wrap(f"{s.num}  {s.title}", BW6 - 12, 5)
        else:
            lines[s.id] = wrap(f"{s.num}  {s.title}", BW - 12)
    BH = max(len(lines[s.id]) for s in sheets if s.id in col_of) * LH + 10
    lvl_h = [max(len(lines[v]) for v in six if lvl[v] == L) * LH + 10
             for L in range(levels)]

    # Horizontal lanes: hops between upper gutters, in the gaps between
    # levels; and the transfer gap (gap -1), from lower to upper gutters.
    hop_lanes, hop_n = {}, {}
    for h, iv in hop_iv.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        hop_lanes.update(ln)
        hop_n[h] = n
    # Entry points from below in the lower grid.
    entries = defaultdict(list)
    for e, p in plan.items():
        u, v = e
        if p[0] == "straight":
            entries[v].append((col_x(col_of[v]) + BW / 2, e))
        elif p[0] == "routed":
            entries[v].append((gutter_x(p[1], lanes_g[e], nlanes_g[p[1]]), e))
    entry_x = {}
    for v, lst in entries.items():
        lst.sort(key=lambda t: t[0])
        x0, w = col_x(col_of[v]), BW
        for k, (_, e) in enumerate(lst):
            entry_x[e] = x0 + w * 0.15 + w * 0.7 * (k + 1) / (len(lst) + 1)
    gap_iv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            gx = gutter_x(p[1], lanes_g[e], nlanes_g[p[1]])
            gap_iv[p[3]][e] = (min(gx, entry_x[e]), max(gx, entry_x[e]))
        elif p[0] == "up":
            gx = gutter_x(p[1], lanes_g[e], nlanes_g[p[1]])
            sx = gut6_x(six_side[(e, "v")][1], e)
            gap_iv[-1][e] = (min(gx, sx), max(gx, sx))
    lanes_h, nlanes_h = {}, {}
    for gap, iv in gap_iv.items():
        ln, n = assign_lanes(iv)
        lanes_h.update(ln)
        nlanes_h[gap] = n

    # Vertical positions.
    TITLE_H = 2 * 12 + 8
    A_H = 2 * LH + 14
    DEL_H = 96
    y = MARGIN + PAD + 22
    a_y = y
    TITLE6_H = 3 * 12.5 + 8
    y += A_H + DEL_H + TITLE6_H
    lvl_y, hop_top = [], {}
    for L in range(levels):
        lvl_y.append(y)
        y += lvl_h[L]
        hop_top[L + 0.5] = y
        y += 8 + hop_n.get(L + 0.5, 0) * LANE
    six_bottom = y
    y += PAD

    def gap_h(gap):
        return 10 + nlanes_h.get(gap, 0) * LANE

    gap_top = {-1: y}
    y += gap_h(-1) + TITLE_H
    row_y = {}
    for r in range(rows):
        row_y[r] = y
        y += BH
        gap_top[r] = y
        extra = TITLE_H if any(row_of[i] == r + 1 and i == ids[-1]
                               for _, ids in clusters[len(col_parts):]
                               for i in ids) else 0
        y += gap_h(r) + extra
    height = y + MARGIN

    def lane_y(gap, e):
        n = nlanes_h[gap]
        return gap_top[gap] + 5 + (lanes_h[e] + 0.5) * LANE if n else gap_top[gap] + 5

    def hop_y(h, e):
        return hop_top[h] + 4 + (hop_lanes[e] + 0.5) * LANE

    box = {}
    for i in col_of:
        box[i] = (col_x(col_of[i]), row_y[row_of[i]], BW, BH)
    for v in six:
        box[v] = (col6_x(col6[v]), lvl_y[lvl[v]], BW6, lvl_h[lvl[v]])
    box[assembly.id] = (a_x, a_y, a_w, A_H)
    lines[assembly.id] = wrap(f"{assembly.num}  {assembly.title}", a_w - 12, 2)

    # Attachment points on the sides of the upper boxes, ordered by the
    # height of the other end, and on the sides of the lower sources.
    att = defaultdict(list)       # (v, side) -> [(sortkey, key)]
    for (e, end), (side, gut) in six_side.items():
        other = e[1] if end == "u" else e[0]
        oy = box[other][1] if other in box else 0
        att[(e[0] if end == "u" else e[1], side)].append((oy, (e, end)))
    att_y = {}
    for (v, side), lst in att.items():
        lst.sort(key=lambda t: t[0])
        x, y0, w, h = box[v]
        for k, (_, key) in enumerate(lst):
            att_y[key] = y0 + h * (k + 1) / (len(lst) + 1)
    exits = defaultdict(list)
    for e, p in plan.items():
        if p[0] in ("routed", "up"):
            exits[(e[0], p[2])].append(e)
    exit_y = {}
    for (u, side), lst in exits.items():
        lst.sort(key=lambda e: lane_y(plan[e][3] if plan[e][0] == "routed" else -1, e))
        x, y0, w, h = box[u]
        for k, e in enumerate(lst):
            exit_y[e] = y0 + h * (k + 1) / (len(lst) + 1)

    def side_x(v, side):
        x, y0, w, h = box[v]
        return x if side == "L" else x + w

    paths = {}
    for e, p in plan.items():
        u, v = e
        ux, uy, uw, uh = box[u]
        vx, vy, vw, vh = box[v]
        if p[0] == "straight":
            ex = entry_x[e]
            paths[e] = [(ex, uy), (ex, vy + vh)]
        elif p[0] == "routed":
            _, gut, side, gap = p
            gx = gutter_x(gut, lanes_g[e], nlanes_g[gut])
            sx = ux + uw if side == "R" else ux
            hy = lane_y(gap, e)
            ex = entry_x[e]
            paths[e] = [(sx, exit_y[e]), (gx, exit_y[e]), (gx, hy),
                        (ex, hy), (ex, vy + vh)]
        elif p[0] == "up":
            _, gut, side = p
            gx = gutter_x(gut, lanes_g[e], nlanes_g[gut])
            sx = ux + uw if side == "R" else ux
            hy = lane_y(-1, e)
            vside, vg = six_side[(e, "v")]
            x6 = gut6_x(vg, e)
            ay = att_y[(e, "v")]
            paths[e] = [(sx, exit_y[e]), (gx, exit_y[e]), (gx, hy),
                        (x6, hy), (x6, ay), (side_x(v, vside), ay)]
        elif p[0] == "down":
            x = ux + uw / 2
            paths[e] = [(x, uy + uh), (x, vy)]
        elif p[0] == "rise":
            x = ux + uw / 2
            paths[e] = [(x, uy), (x, vy + vh)]
        else:
            us, gu = six_side[(e, "u")]
            vs, gv = six_side[(e, "v")]
            uy0, vy0 = att_y[(e, "u")], att_y[(e, "v")]
            if gu == gv:
                x6 = gut6_x(gu, e)
                paths[e] = [(side_x(u, us), uy0), (x6, uy0), (x6, vy0),
                            (side_x(v, vs), vy0)]
            else:
                h = max(lvl[u], lvl[v]) + 0.5
                xu, xv = gut6_x(gu, (e, "u")), gut6_x(gv, (e, "v"))
                hy = hop_y(h, e)
                paths[e] = [(side_x(u, us), uy0), (xu, uy0), (xu, hy),
                            (xv, hy), (xv, vy0), (side_x(v, vs), vy0)]

    # Delivery arrows: module tops to the bottom of the assembly.
    ax, ay, aw, ah = box[assembly.id]
    dels = [m for m in mod_ids if (m, assembly.id) in edges]
    dels.sort(key=lambda m: box[m][0])
    for k, m in enumerate(dels):
        mx, my, mw, mh = box[m]
        tx = ax + aw * (k + 1) / (len(dels) + 1)
        paths[(m, assembly.id)] = [(mx + mw / 2, my), (tx, ay + ah)]

    cl_boxes = []
    for name, ids in clusters:
        xs = [box[i][0] for i in ids]
        ys = [box[i][1] for i in ids]
        ye = [box[i][1] + box[i][3] for i in ids]
        cl_boxes.append((name, min(xs) - PAD, min(ys) - TITLE_H,
                         BW + 2 * PAD, max(ye) - min(ys) + TITLE_H + PAD))
    top = []
    for k, n, ids in up_parts:
        xs = [box[i][0] for i in ids]
        ye = [box[i][1] + box[i][3] for i in ids]
        top.append((f"{k}. {n}" if n else k, min(xs) - PAD, lvl_y[0] - TITLE6_H,
                    BW6 + 2 * PAD, max(ye) - lvl_y[0] + TITLE6_H + PAD))
    a_name = next((f"{k}. {n}" if n else k) for k, n, _ in parts
                  if k == assembly.part)
    top.insert(0, (a_name, a_x - PAD, a_y - 22, a_w + 2 * PAD, A_H + 22 + PAD))
    cl_boxes = top + cl_boxes
    return dict(box=box, lines=lines, paths=paths, clusters=cl_boxes,
                n_top=len(top),
                width=WIDTH, height=height, col_of=col_of, row_of=row_of)


# ---------------------------------------------------------------- SVG

STYLE = """
.fc text { font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
.fc .cl rect { fill: #f5f6f8; stroke: #d5d9df; }
.fc .cl.top rect { fill: #fbf7ef; stroke: #e2d3b4; }
.fc .cl text { font-size: 11.5px; font-weight: 600; fill: #4a5361;
  paint-order: stroke; stroke: #f5f6f8; stroke-width: 4px; }
.fc .cl.top text { stroke: #fbf7ef; stroke-width: 6px; }
.fc .n rect { fill: #fff; stroke: #8b95a3; stroke-width: 1; }
.fc .n.mod rect { fill: #fff1d6; stroke: #b7791f; stroke-width: 1.4; }
.fc .n.dev rect { fill: #fffaf0; stroke: #d6a85a; stroke-width: 1.2; }
.fc .n.asm rect { fill: #fde2dc; stroke: #b4432f; stroke-width: 1.8; }
.fc .n text { font-size: 11.5px; fill: #1f2933; }
.fc .n text .num { font-weight: 700; }
.fc .n.asm text { font-size: 13px; }
.fc a.n:hover rect, .fc a.n:focus rect { stroke: #1d4ed8; stroke-width: 2.2; }
.fc .e { fill: none; stroke-linejoin: round; }
.fc .e.dep { stroke: #4b5563; stroke-width: 1.1; }
.fc .e.inc { stroke: #a9b4c2; stroke-width: 1.1; stroke-dasharray: 4 2; }
.fc .e.del { stroke: #b4432f; stroke-width: 2; }
.fc .dl rect { fill: #fff; stroke: #b4432f; stroke-width: 1; }
.fc .dl text { font-size: 11px; font-weight: 600; fill: #8c2f1f; }
.fc.hl .e { opacity: 0.12; }
.fc.hl .e.on { opacity: 1; stroke-width: 2.2; }
.fc.hl .dl { opacity: 0.25; }
.fc.hl .dl.on { opacity: 1; }
"""

SCRIPT = """
(function () {
  var svg = document.currentScript && document.currentScript.closest
    ? document.currentScript.closest('svg') : null;
  svg = svg || document.querySelector('svg.fc');
  if (!svg) return;
  function set(id, on) {
    svg.classList.toggle('hl', on);
    svg.querySelectorAll('[data-u]').forEach(function (e) {
      var hit = on && (e.getAttribute('data-u') === id || e.getAttribute('data-v') === id);
      e.classList.toggle('on', hit);
    });
  }
  svg.querySelectorAll('a.n').forEach(function (a) {
    var id = a.getAttribute('data-id');
    a.addEventListener('mouseenter', function () { set(id, true); });
    a.addEventListener('mouseleave', function () { set(id, false); });
    a.addEventListener('focus', function () { set(id, true); });
    a.addEventListener('blur', function () { set(id, false); });
  });
})();
"""


def esc(s):
    return html.escape(s, quote=True)


def svg_path(pts, r=4):
    """Polyline with rounded corners."""
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return f"M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f}"
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for (xa, ya), (xb, yb), (xc, yc) in zip(pts, pts[1:], pts[2:]):
        def towards(x0, y0, x1, y1, dist):
            L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if L == 0:
                return x0, y0
            t = min(dist, L / 2) / L
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        p1 = towards(xb, yb, xa, ya, r)
        p2 = towards(xb, yb, xc, yc, r)
        d.append(f"L{p1[0]:.1f},{p1[1]:.1f} Q{xb:.1f},{yb:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    d.append(f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}")
    return " ".join(d)


def render_svg(sheets, g, L):
    by_id = {s.id: s for s in sheets}
    mods = {s.id for s in g["modules"]}
    devs = {s.id for s in g["devs"]}
    asm = g["assembly"].id
    W, H = L["width"], L["height"]
    out = [f'<svg class="fc" xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H:.0f}" '
           f'width="{W}" height="{H:.0f}" role="img" '
           f'aria-label="How the chapters depend on each other" '
           f'style="max-width:100%;height:auto">',
           "<title>How the chapters depend on each other</title>",
           "<defs>"]
    for kind, color in (("dep", "#4b5563"), ("inc", "#a9b4c2"), ("del", "#b4432f")):
        out.append(f'<marker id="ah-{kind}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L10,5 L0,9 z" fill="{color}"/></marker>')
    out.append(f"</defs><style>/*<![CDATA[*/{STYLE}/*]]>*/</style>")
    # Cluster boxes; the titles of the upper clusters go over the edges,
    # which rise through them to the assembly.
    late = []
    for k, (name, x, y, w, h) in enumerate(L["clusters"]):
        upper = k < L["n_top"]
        cls = "cl top" if upper else "cl"
        tl = wrap(name, w - 2 * PAD, 3 if upper else 2)
        texts = "".join(f'<tspan x="{x + PAD:.1f}" dy="{0 if j == 0 else 12.5}">{esc(t)}</tspan>'
                        for j, t in enumerate(tl))
        title = (f'<g class="{cls}"><text x="{x + PAD:.1f}" y="{y + 15:.1f}">'
                 f'{texts}</text></g>')
        out.append(f'<g class="{cls}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                   f'height="{h:.1f}" rx="8"/></g>')
        (late if upper else out).append(title)
    # Edges under the nodes; light ones first.
    order = {"inc": 0, "dep": 1, "del": 2}
    for (u, v), kind in sorted(g["edges"].items(), key=lambda kv: order[kv[1]]):
        pts = L["paths"][(u, v)]
        out.append(f'<path class="e {kind}" data-u="{u}" data-v="{v}" '
                   f'd="{svg_path(pts)}" marker-end="url(#ah-{kind})">'
                   f'<title>{esc(by_id[u].num)} → {esc(by_id[v].num)}</title></path>')
    out += late
    for s in sheets:
        if s.id not in L["box"]:
            continue
        x, y, w, h = L["box"][s.id]
        cls = ("n asm" if s.id == asm else "n mod" if s.id in mods
               else "n dev" if s.id in devs else "n")
        ls = L["lines"][s.id]
        fs = 13 if s.id == asm else FS
        lh = LH + (1.5 if s.id == asm else 0)
        ty = y + h / 2 - (len(ls) - 1) * lh / 2 + fs * 0.35
        tx = x + 6 if s.id != asm else x + w / 2
        anchor = "" if s.id != asm else ' text-anchor="middle"'
        spans = []
        for j, t in enumerate(ls):
            dy = 0 if j == 0 else lh
            if j == 0 and t.startswith(f"{s.num}  "):
                body = (f'<tspan class="num">{esc(s.num)}</tspan>'
                        f'<tspan>\u2002{esc(t[len(s.num) + 2:])}</tspan>')
            else:
                body = esc(t)
            spans.append(f'<tspan x="{tx:.1f}" dy="{dy}">{body}</tspan>')
        out.append(f'<a class="{cls}" data-id="{s.id}" href="{esc(s.html)}" '
                   f'xlink:href="{esc(s.html)}"><title>{esc(s.num)}. {esc(s.title)}</title>'
                   f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4"/>'
                   f'<text x="{tx:.1f}" y="{ty:.1f}"{anchor}>{"".join(spans)}</text></a>')
    # Delivery labels on top.
    for m in g["modules"]:
        labs = g["deliveries"].get(m.id, [])
        if not labs:
            continue
        (x0, y0), (x1, y1) = L["paths"][(m.id, asm)]
        t = 0.42
        lx, ly = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        text = ", ".join(labs)
        tw = len(text) * 6.6 + 10
        out.append(f'<g class="dl" data-u="{m.id}" data-v="{asm}">'
                   f'<rect x="{lx - tw / 2:.1f}" y="{ly - 9:.1f}" width="{tw:.1f}" '
                   f'height="17" rx="8"/><text x="{lx:.1f}" y="{ly + 4:.1f}" '
                   f'text-anchor="middle">{esc(text)}</text></g>')
    out.append(f"<script>//<![CDATA[{SCRIPT}//]]></script>")
    out.append("</svg>")
    return "\n".join(out)


def render_dot(sheets, parts, g):
    by_id = {s.id: s for s in sheets}
    mods = {s.id for s in g["modules"]}
    devs = {s.id for s in g["devs"]}
    asm = g["assembly"].id
    out = ["// Generated by scripts/make-flowchart.py; do not edit.",
           "digraph chapters {", '  rankdir=BT; node [shape=box, style="rounded,filled", '
           'fillcolor=white, fontname="Helvetica", fontsize=10];',
           '  edge [color="#4b5563"];']
    for k, (key, name, ids) in enumerate(parts):
        out.append(f'  subgraph cluster_{k} {{ label="{key}. {name}"; '
                   'style=filled; color="#d5d9df"; fillcolor="#f5f6f8";')
        for i in ids:
            s = by_id[i]
            fill = ("#fde2dc" if i == asm else "#fff1d6" if i in mods
                    else "#fffaf0" if i in devs else "white")
            label = f"{s.num}. {s.title}".replace('"', '\\"')
            out.append(f'    "{i}" [label="{label}", URL="{s.html}", fillcolor="{fill}"];')
        out.append("  }")
    for (u, v), kind in sorted(g["edges"].items()):
        attrs = ""
        if kind == "inc":
            attrs = ' [color="#a9b4c2", style=dashed]'
        elif kind == "del":
            attrs = (f' [color="#b4432f", penwidth=2, '
                     f'label="{", ".join(g["deliveries"].get(u, []))}"]')
        out.append(f'  "{u}" -> "{v}"{attrs};')
    out.append("}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- page

def read_aux_numbers(s):
    """The numbers of the labels in the sheet's .aux, or None if there is
    no .aux or it is older than the current chapter number."""
    aux = s.tex[:-4] + ".aux"
    if not os.path.exists(aux):
        return None
    with open(aux, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"\\newlabel\{chap\}\{\{([^}]*)\}", text)
    if not m or m.group(1) != s.num:
        return None
    return set(re.findall(r"\\newlabel\{[^}]*\}\{\{([^}]*)\}", text))


def org_link(s, text):
    return f"[[file:{s.html}][{text}]]"


def compress(nums):
    """Runs of three or more consecutive main-sequence numbers -> 'a–b'."""
    out, k = [], 0
    while k < len(nums):
        j = k
        while (j + 1 < len(nums) and nums[j][0].isdigit()
               and nums[j + 1][0].isdigit()
               and int(nums[j + 1][0]) == int(nums[j][0]) + 1):
            j += 1
        if j - k >= 2:
            out.append(f"{nums[k][1]}–{nums[j][1]}")
        else:
            out += [n[1] for n in nums[k:j + 1]]
        k = j + 1
    return out


def render_text(text, by_id, pos, checks):
    def sheet(i):
        if i not in by_id:
            die(f"{PLANS} names sheet {i}, which is not in the index")
        return by_id[i]

    def many(m):
        ids = sorted({x for x in m.group(1).split()}, key=lambda i: pos[sheet(i).id])
        items = compress([(by_id[i].num, org_link(by_id[i], by_id[i].num)) for i in ids])
        word = "Chapter" if len(ids) == 1 else "Chapters"
        if len(items) == 1:
            return f"{word} {items[0]}"
        return f"{word} {', '.join(items[:-1])} and {items[-1]}"

    def plain(m):
        s = sheet(m.group(1))
        tail = m.group(2) or ""
        if tail:
            checks.append((s, s.num + tail))
        return s.num + tail

    text = re.sub(r"<([^>]*)>", many, text)
    def full(m):
        s = sheet(m.group(1))
        word = "" if s.side else "Chapter "
        return f"{word}{s.num}, {org_link(s, '/' + s.title + '/')}"

    text = re.sub(r"\[\[(\d{8}T\d{6})\]\]", full, text)
    text = re.sub(r"\[(\d{8}T\d{6})\]",
                  lambda m: org_link(sheet(m.group(1)), sheet(m.group(1)).num), text)
    text = re.sub(r"\{(\d{8}T\d{6})\}((?:\.\d+)*)", plain, text)
    return text


def render_page(sheets, g, svg):
    by_id = {s.id: s for s in sheets}
    pos = {s.id: k for k, s in enumerate(sheets)}
    asm = g["assembly"]
    with open(PLANS, encoding="utf-8") as f:
        data = json.load(f)
    checks = []
    out = ["# Generated by scripts/make-flowchart.py from the index, the sheets",
           f"# and {PLANS}; do not edit.",
           "#+TITLE: How the chapters fit together",
           "#+OPTIONS: toc:nil num:nil author:nil date:nil",
           # The chart is drawn 1200 units wide; let it use the window
           # rather than the text column.
           "#+HTML_HEAD: <style>figure.fc-fig{position:relative;left:50%;"
           "transform:translateX(-50%);width:min(1200px,calc(100vw - 32px));"
           "margin:1em 0} figure.fc-fig svg{display:block;width:100%}</style>",
           "",
           "Back to the [[file:index.html][index]].",
           "",
           "Each box is a chapter and links to it.  Parts I–V are the lower"
           " columns, read from the bottom up: a chapter sits above the chapters"
           " it builds on.  Above them are the later parts, which state the"
           " ingredients in general, each over the Part that treats it in its"
           " simplest setting.  In each later part, the chapters that supply"
           " inputs to the assembly are on top and the chapters that develop"
           " those inputs from the Lean code are below them.  On top of"
           f" everything is the final chapter, /{asm.title}/.  Hover over a"
           " chapter to pick out its arrows.",
           "",
           "#+BEGIN_EXPORT html",
           '<figure class="fc-fig">',
           svg,
           "</figure>",
           "#+END_EXPORT",
           "",
           "*Legend.*",
           "- Dark arrow: the later chapter builds on the earlier one"
           " (from its /Prerequisites/).",
           "- Light dashed arrow: a chapter of Parts I–V is a simplest"
           " incarnation of a chapter of a later part (from its /Prerequisites/,"
           " its"
           " /Simplest incarnation/ remarks, and the map of the inputs in"
           f" /{asm.title}/).",
           "- Pale boxes: chapters of a later part without a /Deliverable/"
           " paragraph, which set up the objects or develop inputs in the form"
           " the Lean formalization proves; arrows to and from them come from"
           " /Prerequisites/.",
           "- Red arrow: a chapter of a later part supplies the inputs named on"
           " it to"
           " the assembly (where its /Deliverable/ paragraph and the map of the"
           " inputs agree).  The conditions (K1)–(K8) of a chain record are"
           " counted as the inputs (A1)–(A7) they give.",
           "- An arrow is left out when a path of other arrows already leads"
           " from the one chapter to the other.",
           ]
    if g["unsupplied"]:
        labs = ", ".join(f"({l})" for l in g["unsupplied"])
        out.append(f"- Not supplied by any one chapter: {labs}; see the map of"
                   f" the inputs in {org_link(asm, '/' + asm.title + '/')}.")
    out += ["", "* Sample seminar plans", "",
            "These are suggestions drafted by AI agents and have not been"
            " tested in a seminar.  The sessions are 90 minutes.", ""]
    for p in data["plans"]:
        out.append(f"** {p['title']}")
        out.append("")
        if p.get("intro"):
            out += [render_text(p["intro"], by_id, pos, checks), ""]
        for k, s in enumerate(p["sessions"], 1):
            out.append(f"{k}. {render_text(s, by_id, pos, checks)}")
        out.append("")
        for a in p.get("after", []):
            out += [render_text(a, by_id, pos, checks), ""]
    if data.get("notes"):
        out += ["** Practical notes", ""]
        for n in data["notes"]:
            out.append(f"- {render_text(n, by_id, pos, checks)}")
        out.append("")
    # Check section and theorem numbers against the .aux files.
    cache = {}
    for s, num in dict.fromkeys(checks):
        if s.id not in cache:
            cache[s.id] = read_aux_numbers(s)
        nums = cache[s.id]
        if nums is not None and num not in nums:
            warn(f"{PLANS}: {num} is not a number in {s.tex[:-4]}.aux")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()
    sheets, parts = read_index()
    g = build_graph(sheets, parts)
    for m in g["modules"]:
        if (paragraph(g["src"][m.id], "Deliverable")
                and not g["deliveries"].get(m.id)):
            warn(f"{m.tex}: no inputs found in its Deliverable paragraph")
    L = layout(sheets, parts, g)
    svg = render_svg(sheets, g, L)
    files = {"flowchart.svg": svg + "\n",
             "flowchart.dot": render_dot(sheets, parts, g),
             "flowchart.org": render_page(sheets, g, svg)}
    for name, text in files.items():
        with open(os.path.join(args.outdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    n_edges = sum(1 for k in g["edges"].values())
    print(f"make-flowchart: {len(sheets)} chapters, {n_edges} arrows; "
          f"wrote {', '.join(files)}")


if __name__ == "__main__":
    main()
