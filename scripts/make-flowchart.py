#!/usr/bin/env python3
"""Draw how the chapters depend on each other, and render the seminar plans.

Everything is read from the sources, so the chart follows the index:

  * the index (the guide) gives the chapters, their order, numbers,
    titles, IDs and Parts;
  * each sheet's \\externaldocument lines name the sheets it cites, and
    the references in its Prerequisites paragraph say which of them it
    builds on (references to later chapters are pointers, not
    prerequisites, and are dropped);
  * the last Part holds the modules (the general statements) and, as
    its last chapter, the assembly.  A module's Prerequisites and its
    "Simplest incarnation" remarks name the earlier chapters it
    generalizes.  Which inputs (A1)-(A7), (V1)-(V3), (W1)-(W4) of the
    assembly a module supplies is read from its Deliverable paragraph
    and from the assembly's map of the inputs (the description list in
    its section sec:map), keeping the labels on which both agree;
  * a chapter of the last Part without a Deliverable paragraph whose
    Prerequisites cite an earlier chapter of that Part is a development: it treats one input of that
    chapter (its parent) in detail.  It supplies nothing to the assembly
    directly, and is drawn in a band just below the modules, under its
    parent where that column is free.

The chart is a grid: one column per Part, the chapters of a Part stacked
with the earliest at the bottom, the modules above the column that feeds
them most, the developments just below their modules, and the assembly
on top.  Edges implied by a path are dropped
(transitive reduction).  The layout and the orthogonal edge routing are
done here, so Graphviz is not needed; a DOT file is written as well, for
reference.

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
import itertools
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
    last_part = main[-1].part
    assembly = main[-1]
    modules = [s for s in main if s.part == last_part and s is not assembly]
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

    # Developments: chapters of the last Part that build on an earlier
    # one.  The parent is the earliest module reached through the
    # chapters of the last Part that it cites.
    devs, parent = [], {}
    for s in modules:
        cited = sorted((t for t in deps[s.id]
                        if t in {x.id for x in modules}), key=pos.get)
        if cited and not paragraph(src[s.id], "Deliverable"):
            p = cited[0]
            parent[s.id] = parent.get(p, p)
            devs.append(s)
    modules = [s for s in modules if s.id not in parent]

    for s in sheets:
        if s in modules:
            for m in re.finditer(r"Simplest incarnation\}?:?(.*?)(?:Status|\n[ \t]*\n)",
                                 src[s.id], re.S):
                deps[s.id] |= resolve(s, prefixes(m.group(1)),
                                      "Simplest incarnation")

    deliveries = {}
    for s in modules:
        para = paragraph(src[s.id], "Deliverable")
        if not para:
            warn(f"{s.tex} has no Deliverable paragraph")
        deliveries[s.id] = delivered(para)

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
    return deps, deliveries, inputs, assembly, modules, src, devs, parent


# ---------------------------------------------------------------- graph

def build_graph(sheets, parts):
    (deps, deliveries, inputs, assembly, modules, src,
     devs, parent) = read_sheets(sheets)
    mod_ids = {s.id for s in modules}
    edges = {}          # (u, v) -> kind: dep, inc, del

    def kind_to(v):
        return "inc" if v in mod_ids or v == assembly.id else "dep"

    for v, us in deps.items():
        for u in us:
            edges[(u, v)] = kind_to(v)
    supplier = defaultdict(list)
    for mid, labs in deliveries.items():
        for lab in labs:
            supplier[lab].append(mid)
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
                devs=devs, parent=parent)


# ---------------------------------------------------------------- layout

FS = 11.5            # node font size
LH = 13.5            # line height
CHAR = 0.53 * FS     # average character width (sans-serif), a bit generous
WIDTH = 1200
MARGIN = 6
LANE = 6             # spacing of parallel edges
PAD = 7              # cluster padding
DEV = -0.5           # the row of the developments, between modules and Parts


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
    by_id = {s.id: s for s in sheets}
    assembly, modules = g["assembly"], g["modules"]
    mod_ids = [s.id for s in modules]
    last_part = assembly.part
    col_parts = [p for p in parts if p[0] != last_part
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

    # Modules over the columns that feed them most.
    edges = g["edges"]
    feed = defaultdict(int)
    for (u, v), k in edges.items():
        if v in mod_ids and u in col_of:
            feed[(v, col_of[u])] += 1
    if len(mod_ids) <= C:
        best = max(itertools.permutations(range(C), len(mod_ids)),
                   key=lambda p: (sum(feed[(m, c)] for m, c in zip(mod_ids, p)),
                                  [-x for x in p]))
    else:
        best = [k % C for k in range(len(mod_ids))]
    for m, c in zip(mod_ids, best):
        col_of[m], row_of[m] = c, -1
    col_of[assembly.id], row_of[assembly.id] = C // 2, -2

    # Developments, in a band just below the modules: under the parent
    # if that column is free, else in the nearest free column.
    dev_ids = [s.id for s in g["devs"]]
    parent = g["parent"]
    dev_cols = set()
    for d in dev_ids:
        free = [c for c in range(C) if c not in dev_cols]
        if not free:
            die("more developments than columns; extend the layout")
        pc = col_of[parent[d]]
        c = min(free, key=lambda c: (abs(c - pc), c))
        dev_cols.add(c)
        col_of[d], row_of[d] = c, DEV

    def below(c, r):
        """The row drawn directly below row r in column c."""
        if r == -1:
            return DEV if c in dev_cols else 0
        if r == DEV:
            return 0
        return r + 1

    # Routing plan: for each edge, gutter and gap (lanes come later).
    # Gutter g lies left of column g.  Gap r lies below row r (gap -1:
    # between the modules and the first row of chapters).
    plan = {}
    for (u, v), k in edges.items():
        if k == "del":
            continue
        cu, ru, cv, rv = col_of[u], row_of[u], col_of[v], row_of[v]
        if v in dev_ids and (u in mod_ids or u in dev_ids):
            plan[(u, v)] = ("near",)
        elif cu == cv and ru == below(cv, rv):
            plan[(u, v)] = ("straight",)
        else:
            if cv > cu:
                gut, side = cu + 1, "R"
            elif cv < cu:
                gut, side = cu, "L"
            else:
                gut, side = cu, "L"
            plan[(u, v)] = ("routed", gut, side, rv)

    # Box sizes.
    gutter_lanes = defaultdict(dict)
    # Lane counts need y extents; first estimate with row indices.
    for e, p in plan.items():
        if p[0] == "routed":
            _, gut, side, gap = p
            ru = row_of[e[0]]
            gutter_lanes[gut][e] = (min(ru, gap + 0.5), max(ru, gap + 0.5))
    lanes_g, nlanes_g = {}, {}
    for gut, iv in gutter_lanes.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        lanes_g.update(ln)
        nlanes_g[gut] = n
    maxl = max(nlanes_g.values(), default=1)
    GW = max(36, 2 * PAD + 10 + maxl * LANE)
    BW = (WIDTH - 2 * MARGIN - (C + 1) * GW) / C

    def col_x(c):
        return MARGIN + GW + c * (BW + GW)

    def gutter_x(gut, lane, n):
        left = MARGIN + gut * (BW + GW)
        mid = left + GW / 2
        return mid + (lane - (n - 1) / 2) * LANE

    a_w = min(2 * BW + GW, WIDTH - 2 * MARGIN)
    a_x = WIDTH / 2 - a_w / 2

    def span_x(v):
        """Left end and width of the box of v."""
        if v == assembly.id:
            return a_x, a_w
        return col_x(col_of[v]), BW

    lines = {}
    for s in sheets:
        lines[s.id] = wrap(f"{s.num}  {s.title}", BW - 12)
    BH = max(len(lines[s.id]) for s in sheets if s.id in col_of) * LH + 10

    # Horizontal segments in gaps need x extents: entry points first.
    entries = defaultdict(list)       # v -> [(sortkey, e)]
    for e, p in plan.items():
        u, v = e
        if p[0] == "near":
            continue
        if p[0] == "straight":
            entries[v].append((span_x(v)[0] + span_x(v)[1] / 2, e))
        else:
            n = nlanes_g[p[1]]
            entries[v].append((gutter_x(p[1], lanes_g[e], n), e))
    entry_x = {}
    for v, lst in entries.items():
        lst.sort(key=lambda t: t[0])
        x0, w = span_x(v)
        for k, (_, e) in enumerate(lst):
            entry_x[e] = x0 + w * 0.15 + w * 0.7 * (k + 1) / (len(lst) + 1)
    gap_iv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            gx = gutter_x(p[1], lanes_g[e], nlanes_g[p[1]])
            ex = entry_x[e]
            gap_iv[p[3]][e] = (min(gx, ex), max(gx, ex))
    lanes_h, nlanes_h = {}, {}
    for gap, iv in gap_iv.items():
        ln, n = assign_lanes(iv)
        lanes_h.update(ln)
        nlanes_h[gap] = n

    # Vertical positions.
    TITLE_H = 2 * 12 + 8                 # cluster titles, two lines
    A_H = 2 * LH + 14                    # assembly box
    DEL_H = 96                           # band for the delivery arrows
    y = MARGIN + PAD + 22                # Part VI title
    a_y = y
    y += A_H + DEL_H
    m_y = y
    MBH = max(len(lines[m]) for m in mod_ids) * LH + 10
    y += MBH + PAD

    def gap_h(gap):
        return 10 + nlanes_h.get(gap, 0) * LANE

    gap_top = {-2: a_y + A_H + 2, -1: y}
    y += gap_h(-1)
    dev_y = DBH = None
    if dev_ids:
        DBH = max(len(lines[d]) for d in dev_ids) * LH + 10
        dev_y = y + 4
        y = dev_y + DBH + PAD
        gap_top[DEV] = y
        y += gap_h(DEV)
    y += TITLE_H
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

    box = {}
    for i in col_of:
        if i == assembly.id:
            continue
        if i in mod_ids:
            box[i] = (col_x(col_of[i]), m_y, BW, MBH)
        elif i in dev_ids:
            box[i] = (col_x(col_of[i]), dev_y, BW, DBH)
        else:
            box[i] = (col_x(col_of[i]), row_y[row_of[i]], BW, BH)
    box[assembly.id] = (a_x, a_y, a_w, A_H)
    lines[assembly.id] = wrap(f"{assembly.num}  {assembly.title}", a_w - 12, 2)

    # Exit points on the sides of the sources.
    exits = defaultdict(list)
    for e, p in plan.items():
        if p[0] == "routed":
            exits[(e[0], p[2])].append(e)
    exit_y = {}
    for (u, side), lst in exits.items():
        lst.sort(key=lambda e: lane_y(plan[e][3], e))
        x, y0, w, h = box[u]
        for k, e in enumerate(lst):
            exit_y[e] = y0 + h * (k + 1) / (len(lst) + 1)

    paths = {}
    for e, p in plan.items():
        u, v = e
        vx, vy, vw, vh = box[v]
        ux, uy, uw, uh = box[u]
        if p[0] == "near":
            continue
        ex = entry_x[e]
        if p[0] == "straight":
            paths[e] = [(ex, uy), (ex, vy + vh)]
        else:
            _, gut, side, gap = p
            gx = gutter_x(gut, lanes_g[e], nlanes_g[gut])
            sx = ux + uw if side == "R" else ux
            hy = lane_y(gap, e)
            paths[e] = [(sx, exit_y[e]), (gx, exit_y[e]), (gx, hy),
                        (ex, hy), (ex, vy + vh)]

    # From a module or development to a development: down from the
    # parent, or sideways within the band.
    for e, p in plan.items():
        if p[0] != "near":
            continue
        u, v = e
        ux, uy, uw, uh = box[u]
        vx, vy, vw, vh = box[v]
        right = vx > ux
        if u in dev_ids:
            yy = vy + vh / 2
            paths[e] = ([(ux + uw, yy), (vx, yy)] if right
                        else [(ux, yy), (vx + vw, yy)])
        elif col_of[u] == col_of[v]:
            x = ux + 0.07 * uw
            paths[e] = [(x, uy + uh), (x, vy)]
        else:
            sx = ux + (0.93 * uw if right else 0.07 * uw)
            tx = vx + (0.07 * vw if right else 0.93 * vw)
            paths[e] = [(sx, uy + uh), (sx, vy - 6), (tx, vy - 6), (tx, vy)]

    # Delivery arrows: module tops to the bottom of the assembly.
    ax, ay, aw, ah = box[assembly.id]
    dels = sorted((m for m in mod_ids), key=lambda m: box[m][0])
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
    p6_name = next((f"{k}. {n}" if n else k) for k, n, _ in parts if k == last_part)
    p6_bottom = dev_y + DBH if dev_ids else m_y + MBH
    cl_boxes.insert(0, (p6_name, MARGIN, MARGIN, WIDTH - 2 * MARGIN,
                        p6_bottom + PAD - MARGIN))
    return dict(box=box, lines=lines, paths=paths, clusters=cl_boxes,
                width=WIDTH, height=height, col_of=col_of, row_of=row_of)


# ---------------------------------------------------------------- SVG

STYLE = """
.fc text { font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
.fc .cl rect { fill: #f5f6f8; stroke: #d5d9df; }
.fc .cl.top rect { fill: #fbf7ef; stroke: #e2d3b4; }
.fc .cl text { font-size: 11.5px; font-weight: 600; fill: #4a5361;
  paint-order: stroke; stroke: #f5f6f8; stroke-width: 4px; }
.fc .cl.top text { stroke: #fbf7ef; }
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
    for k, (name, x, y, w, h) in enumerate(L["clusters"]):
        cls = "cl top" if k == 0 else "cl"
        tl = wrap(name, w - 2 * PAD, 2)
        texts = "".join(f'<tspan x="{x + PAD:.1f}" dy="{0 if j == 0 else 12.5}">{esc(t)}</tspan>'
                        for j, t in enumerate(tl))
        out.append(f'<g class="{cls}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                   f'height="{h:.1f}" rx="8"/><text x="{x + PAD:.1f}" y="{y + 15:.1f}">'
                   f'{texts}</text></g>')
    # Edges under the nodes; light ones first.
    order = {"inc": 0, "dep": 1, "del": 2}
    for (u, v), kind in sorted(g["edges"].items(), key=lambda kv: order[kv[1]]):
        pts = L["paths"][(u, v)]
        out.append(f'<path class="e {kind}" data-u="{u}" data-v="{v}" '
                   f'd="{svg_path(pts)}" marker-end="url(#ah-{kind})">'
                   f'<title>{esc(by_id[u].num)} → {esc(by_id[v].num)}</title></path>')
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
           "Each box is a chapter and links to it.  Parts I–V are the columns,"
           " read from the bottom up: a chapter sits above the chapters it"
           " builds on.  On top are the chapters of Part VI, each stating one"
           f" ingredient in general, and the final chapter, /{asm.title}/,"
           " which assembles them.  Just below a Part VI chapter are the"
           " chapters that develop one of its inputs, in the form the Lean"
           " formalization proves.  Hover over a chapter to pick out its arrows.",
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
           "- Light dashed arrow: the earlier chapter is a simplest incarnation"
           " of a Part VI chapter (from its /Prerequisites/, its"
           " /Simplest incarnation/ remarks, and the map of the inputs in"
           f" /{asm.title}/).",
           "- Pale box below a Part VI chapter: a chapter that develops one"
           " of its inputs (it cites an earlier Part VI chapter in its"
           " /Prerequisites/); the arrow comes from the chapter it builds on.",
           "- Red arrow: a Part VI chapter supplies the inputs named on it to"
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
        if not g["deliveries"].get(m.id):
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
