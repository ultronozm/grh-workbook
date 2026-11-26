#!/usr/bin/env python3
"""Draw how the chapters depend on each other, and render the seminar plans.

Everything is read from the sources, so the chart follows the index:

  * the index (the guide) gives the chapters, their order, numbers,
    titles, IDs and Parts;
  * each sheet's \\externaldocument lines name the sheets it cites, and
    the references in its Prerequisites paragraph say which of them it
    builds on.  These are the only arrows; build_graph says which are
    drawn and how.

The chart has two sections (layout).  On top, set apart on a shaded
band, the proof (the Parts from FIRST_PROOF_PART on): a column per Part,
each a tree with the chapter stating the Part's results at its head, and
above them the main inequality, which they all feed.  Below, the basics:
a column per Part, the chapters stacked with the earliest at the bottom,
and the side series under the shortest column.  The only per-sheet
knowledge is in the index and the Prerequisites paragraphs, so the chart
follows the index as sheets are added.  The layout and the orthogonal
edge routing are done here, so Graphviz is not needed; a DOT file is
written as well, for reference.

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
from pathlib import Path
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
REF = re.compile(r"\\(?:eq|auto|c|C)?ref\{(?P<pre>[A-Za-z0-9]+-)")


def die(msg):
    sys.exit(f"make-flowchart: {msg}")


def warn(msg):
    print(f"make-flowchart: warning: {msg}", file=sys.stderr)


# ---------------------------------------------------------------- reading

class Sheet:
    def __init__(self, ident, slug, num, title, part, part_name, side):
        self.id, self.slug, self.num, self.title = ident, slug, num, title
        self.part, self.part_name, self.side = part, part_name, side
        # The title without TeX math delimiters, for the chart.
        self.plain = re.sub(r"\$([^$]*)\$", r"\1", title)
        self.tex = f"{ident}--{slug}__workbook.tex"
        self.html = f"{ident}--{slug}__workbook.html"
        self.desc = ""

    def __repr__(self):
        return f"<{self.num}>"


def read_index():
    """Return the sheets in index order and the Parts as (key, name, ids).
    Side-series sheets, if any, are left out of the chart."""
    with open(GUIDE, encoding="utf-8") as f:
        guide = f.read()
    sheets, parts = [], []
    heading = None
    for line in guide.split("\n"):
        if sheets and line.startswith("  ") and not sheets[-1].desc:
            # The description under an entry, without its math.
            d = re.sub(r"\$[^$]*\$", "", line.strip())
            d = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s+", " ", d))
            sheets[-1].desc = d.strip()
            continue
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
    text = re.sub(r"(?<!\\)%.*", "", text)
    return {m.group("pre") for m in REF.finditer(text)}


# ---------------------------------------------------------------- graph

# Part-level layout: Parts before this one are the basics, drawn as the
# columns of the lower grid; this Part and the later ones (other than a
# side series) are the proof, drawn as a separate section on top.
FIRST_PROOF_PART = "Part VI"


def read_cites(sheets):
    """Map each sheet ID to the IDs of all sheets named in its
    Prerequisites paragraph, earlier or later."""
    by_id = {s.id: s for s in sheets}
    cites = {}
    for s in sheets:
        with open(s.tex, encoding="utf-8") as f:
            src = f.read()
        pre = {m.group("pre"): m.group("id") for m in EXTDOC.finditer(src)}
        para = paragraph(src, "Prerequisites")
        if not para:
            warn(f"{s.tex} has no Prerequisites paragraph")
        out = set()
        for p in prefixes(para):
            t = pre.get(p)
            if t is None:
                warn(f"{s.tex}: Prerequisites cites prefix {p} without "
                     "\\externaldocument")
            elif t not in by_id:
                warn(f"{s.tex}: Prerequisites cites {t}, which is not in the index")
            elif t != s.id:
                out.add(t)
        cites[s.id] = out
    return cites


def build_graph(sheets, parts):
    """The arrows of the chart, with their kinds.

    * dep: within the basics (and the side series), from the Prerequisites
      of the later chapter.
    * inc: from a basics chapter into a chapter of the proof whose
      Prerequisites name it.
    * tree: inside a Part of the proof, from a sheet to the chapter it
      serves.  The first chapter of the Part states its results; a sheet
      it names hangs under it, a sheet named by such a sheet under that
      one, and so on (breadth first, in index order); a sheet that no
      chapter of the Part names hangs under the last placed chapter
      before it in the index.
    * main: into the sink, the chapter of the proof whose Prerequisites
      name the first chapters of the most other Parts of the proof (the
      main inequality); from the chapters of the proof it names that are
      first chapters of their Parts or in its own Part.
    Arrows between Parts of the proof other than into the sink are left
    out.  An arrow of kind dep or inc implied by a path is dropped."""
    by_id = {s.id: s for s in sheets}
    pos = {s.id: k for k, s in enumerate(sheets)}
    cites = read_cites(sheets)
    keys = [k for k, _, _ in parts]
    side_parts = [p for p in parts if by_id[p[2][0]].side]
    main_parts = [p for p in parts if p not in side_parts]
    start = (keys.index(FIRST_PROOF_PART) if FIRST_PROOF_PART in keys
             else len(keys))
    proof = [p for p in main_parts if keys.index(p[0]) >= start]
    basics = [p for p in main_parts if keys.index(p[0]) < start]
    proof_ids = {i for _, _, ids in proof for i in ids}
    basic_ids = {i for _, _, ids in basics + side_parts for i in ids}
    heads = {k: ids[0] for k, _, ids in proof}

    def score(i):
        return sum(1 for k, h in heads.items()
                   if h in cites[i] and k != by_id[i].part)
    sink = max(proof_ids, key=lambda i: (score(i), pos[i])) if proof_ids else None
    if sink is not None and score(sink) == 0:
        sink = None

    kind = {}
    for v in basic_ids:
        for u in cites[v] & basic_ids:
            if pos[u] < pos[v]:
                kind[(u, v)] = "dep"
    for v in proof_ids:
        for u in cites[v] & basic_ids:
            kind[(u, v)] = "inc"

    parent, depth, order = {}, {}, {}
    for key, _, ids in proof:
        root = sink if sink in ids else ids[0]
        members = [i for i in ids if i != root]
        placed = {root: 0}
        queue = [root]
        while queue:
            x = queue.pop(0)
            for y in sorted(cites[x], key=pos.get):
                if y in members and y not in placed:
                    placed[y] = placed[x] + 1
                    parent[y] = x
                    queue.append(y)
        last = root
        for i in members:
            if i in placed:
                last = i
            else:
                parent[i] = last
                placed[i] = placed[last] + 1
        # The column, in depth-first order with children in index order.
        children = defaultdict(list)
        for i in members:
            children[parent[i]].append(i)
        col = []

        def visit(x):
            col.append(x)
            for c in sorted(children[x], key=pos.get):
                visit(c)
        if root == sink:
            for c in sorted(children[root], key=pos.get):
                visit(c)
            base = 1
        else:
            visit(root)
            base = 0
        order[key] = col
        for i in col:
            depth[i] = placed[i] - base
        for i in members:
            kind[(i, parent[i])] = "main" if parent[i] == sink else "tree"
    if sink is not None:
        for key, _, ids in proof:
            h = ids[0]
            if h != sink and sink not in ids and h in cites[sink]:
                kind[(h, sink)] = "main"
        for key, _, ids in proof:
            if (sink not in ids and ids[0] not in cites[sink]):
                warn(f"the main inequality does not name {by_id[ids[0]].tex}")

    succ = defaultdict(set)
    for (u, v) in kind:
        succ[u].add(v)

    def reaches(a, b, skip):
        stack, seen = [x for x in succ[a] if (a, x) != skip], set()
        while stack:
            x = stack.pop()
            if x == b:
                return True
            if x not in seen:
                seen.add(x)
                stack.extend(succ[x])
        return False

    kind = {e: k for e, k in kind.items()
            if k in ("tree", "main") or not reaches(e[0], e[1], e)}
    return dict(kind=kind, sink=sink, proof=proof, basics=basics,
                side=side_parts, order=order, depth=depth, parent=parent)


# ---------------------------------------------------------------- layout

FS = 11.5            # node font size
LH = 13.5            # line height
CHAR = 0.53 * FS     # average character width (sans-serif), a bit generous
WIDTH = 1200
MARGIN = 6
LANE = 6             # spacing of parallel edges
PAD = 7              # cluster padding
INDENT = 16          # indentation per level of a tree
TRUNK = 10           # room left of the top boxes of a proof column
TITLE_H = 2 * 12.5 + 10


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


def label(s):
    return f"{s.num}  {s.plain}"


def layout(sheets, g):
    """The proof on top: the main inequality, and below it a column per
    Part of the proof, each a tree under its first chapter.  The basics
    below, set apart: a column per Part, the chapters stacked with the
    earliest at the bottom; the side series under the shortest column.
    Arrows among the basics run in the gutters between the columns and
    in the gaps below the rows; arrows from the basics into the proof
    cross the gap between the two sections and enter the boxes of the
    proof from the right."""
    by_id = {s.id: s for s in sheets}
    kind, sink = g["kind"], g["sink"]
    proof, basics = g["proof"], g["basics"]

    # ---- the lower grid: columns and rows
    C = len(basics)
    col_of, row_of = {}, {}
    for c, (_, _, ids) in enumerate(basics):
        for r, i in enumerate(reversed(ids)):
            col_of[i], row_of[i] = c, r
    rows = max((len(p[2]) for p in basics), default=0)
    clusters = [(f"{k}. {n}" if n else k, ids, False) for k, n, ids in basics]
    side_start = set()
    for key, name, ids in g["side"]:
        used = [sum(1 for i in col_of if col_of[i] == c) for c in range(C)]
        c = min(range(C), key=lambda c: (used[c], -c))
        start = used[c] + 1
        side_start.add(start)
        for r, i in enumerate(reversed(ids)):
            col_of[i], row_of[i] = c, start + r
        rows = max(rows, start + len(ids))
        clusters.append((f"{key}. {name}" if name else key, ids, False))

    # ---- the upper grid: a column per Part of the proof
    K = len(proof)
    col6 = {}
    for k, (key, _, _) in enumerate(proof):
        for i in g["order"][key]:
            col6[i] = k

    plan = {}
    for e, k in kind.items():
        u, v = e
        if k == "dep":
            cu, ru, cv, rv = col_of[u], row_of[u], col_of[v], row_of[v]
            if cu == cv and ru == rv + 1:
                plan[e] = ("straight",)
            else:
                gut, side = (cu + 1, "R") if cv > cu else (cu, "L")
                plan[e] = ("routed", gut, side, rv)
        elif k == "inc":
            # Toward the upper gutter right of the target's column.
            cu = col_of[u]
            frac = (col6[v] + 1) / K
            gut, side = (cu + 1, "R") if frac > (cu + 0.5) / C else (cu, "L")
            plan[e] = ("up", gut, side)
        else:
            plan[e] = (k,)

    # Arrows from one basics chapter into the proof are bundled: one lane
    # per source in the lower gutters, one per source and target column in
    # the gap between the sections and in the upper gutters.
    def lk(e):
        return ("up", e[0], plan[e][1]) if plan[e][0] == "up" else e

    def bk(e):
        return (e[0], col6[e[1]])

    # Lower gutters: lanes by row intervals ("up" edges rise to the top).
    giv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            ru = row_of[e[0]]
            giv[p[1]][e] = (min(ru, p[3] + 0.5), max(ru, p[3] + 0.5))
        elif p[0] == "up":
            giv[p[1]][lk(e)] = (-1, row_of[e[0]])
    lanes_g, n_g = {}, {}
    for gut, iv in giv.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        lanes_g.update(ln)
        n_g[gut] = n
    gw = [max(30, 2 * PAD + 10 + n_g.get(k, 0) * LANE) for k in range(C + 1)]
    BW = (WIDTH - 2 * MARGIN - sum(gw)) / C

    def col_x(c):
        return MARGIN + sum(gw[:c + 1]) + c * BW

    def gutter_x(gut, e):
        left = MARGIN + sum(gw[:gut]) + gut * BW
        return left + gw[gut] / 2 + (lanes_g[lk(e)] - (n_g[gut] - 1) / 2) * LANE

    # Upper gutters: one lane per arrow entering from the right.
    n6 = defaultdict(set)
    for e, p in plan.items():
        if p[0] == "up":
            n6[col6[e[1]] + 1].add(bk(e))
    n6 = {k: len(v) for k, v in n6.items()}
    gw6 = [max(24, 2 * PAD + 6 + n6.get(k, 0) * LANE) for k in range(K + 1)]
    BW6 = (WIDTH - 2 * MARGIN - sum(gw6)) / K

    def col6_x(c):
        return MARGIN + sum(gw6[:c + 1]) + c * BW6

    lines = {}
    for i in col_of:
        lines[i] = wrap(label(by_id[i]), BW - 12)
    for i in col6:
        w = BW6 - TRUNK - INDENT * g["depth"][i]
        lines[i] = wrap(label(by_id[i]), w - 12)
    BH = max((len(lines[i]) for i in col_of), default=1) * LH + 10

    # ---- vertical positions, top down
    box = {}
    y = MARGIN
    S_W = min(2.2 * BW6, WIDTH - 2 * MARGIN)
    if sink is not None:
        lines[sink] = wrap(label(by_id[sink]), S_W - 16, 2)
        sub = wrap(by_id[sink].desc, S_W - 16, 2) if by_id[sink].desc else []
        s_h = len(lines[sink]) * (LH + 1.5) + len(sub) * LH + 16
        box[sink] = (WIDTH / 2 - S_W / 2, y + PAD, S_W, s_h)
        y += PAD + s_h + 56
    up_top = y
    y6 = {}
    bottoms = []
    for k, (key, _, _) in enumerate(proof):
        yy = up_top + TITLE_H
        for i in g["order"][key]:
            d = g["depth"][i]
            x = col6_x(k) + TRUNK + INDENT * d
            h = len(lines[i]) * LH + 10
            box[i] = (x, yy, col6_x(k) + BW6 - x, h)
            yy += h + 7
        bottoms.append(yy)
    up_bottom = max(bottoms, default=up_top) + PAD

    # Transfer gap: horizontal lanes from lower to upper gutters.
    att = defaultdict(list)
    for e, p in plan.items():
        if p[0] == "up":
            att[e[1]].append(e)
    att_y = {}
    for v, lst in att.items():
        lst.sort(key=lambda e: (col_of[e[0]], -row_of[e[0]]))
        x, y0, w, h = box[v]
        for k, e in enumerate(lst):
            att_y[e] = y0 + h * (k + 1) / (len(lst) + 1)
    lane6 = {}
    top_y = defaultdict(lambda: 1e9)
    for e, p in plan.items():
        if p[0] == "up":
            top_y[bk(e)] = min(top_y[bk(e)], att_y[e])
    byg = defaultdict(list)
    for b in top_y:
        byg[b[1] + 1].append(b)
    for gut, lst in byg.items():
        # The bundle reaching highest takes the outermost lane.
        lst.sort(key=lambda b: -top_y[b])
        for k, b in enumerate(lst):
            lane6[b] = k

    def gut6_x(e):
        gut = col6[e[1]] + 1
        left = MARGIN + sum(gw6[:gut]) + gut * BW6
        return left + PAD + 3 + lane6[bk(e)] * LANE

    tiv = {}
    for e, p in plan.items():
        if p[0] == "up":
            a, b = gutter_x(p[1], e), gut6_x(e)
            lo, hi = tiv.get(bk(e), (a, a))
            tiv[bk(e)] = (min(lo, a, b), max(hi, a, b))
    lanes_t, n_t = assign_lanes(tiv)
    t_top = up_bottom + 6
    y = t_top + 8 + n_t * LANE + 10

    # Lower gaps: entries into the bottoms of boxes.
    entries = defaultdict(list)
    for e, p in plan.items():
        if p[0] == "straight":
            entries[e[1]].append((col_x(col_of[e[1]]) + BW / 2, e))
        elif p[0] == "routed":
            entries[e[1]].append((gutter_x(p[1], e), e))
    entry_x = {}
    for v, lst in entries.items():
        lst.sort(key=lambda t: t[0])
        x0 = col_x(col_of[v])
        for k, (_, e) in enumerate(lst):
            entry_x[e] = x0 + BW * 0.15 + BW * 0.7 * (k + 1) / (len(lst) + 1)
    hiv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            gx = gutter_x(p[1], e)
            hiv[p[3]][e] = (min(gx, entry_x[e]), max(gx, entry_x[e]))
    lanes_h, n_h = {}, {}
    for gap, iv in hiv.items():
        ln, n = assign_lanes(iv)
        lanes_h.update(ln)
        n_h[gap] = n

    low_top = y
    y += TITLE_H
    row_y, gap_top = {}, {}
    for r in range(rows):
        row_y[r] = y
        y += BH
        gap_top[r] = y
        y += 10 + n_h.get(r, 0) * LANE + (TITLE_H if r + 1 in side_start else 0)
    height = y + MARGIN
    for i in col_of:
        box[i] = (col_x(col_of[i]), row_y[row_of[i]], BW, BH)

    def lane_y(gap, e):
        return gap_top[gap] + 5 + (lanes_h[e] + 0.5) * LANE

    def t_y(e):
        return t_top + 5 + (lanes_t[bk(e)] + 0.5) * LANE

    # Exits from the sides of lower boxes.
    exits = defaultdict(dict)
    for e, p in plan.items():
        if p[0] in ("routed", "up"):
            exits[(e[0], p[2])].setdefault(lk(e), []).append(e)
    exit_y = {}
    for (u, side), groups in exits.items():
        keys = sorted(groups, key=lambda k: -1e9 if k[0] == "up"
                      else lane_y(plan[k][3], k))
        x, y0, w, h = box[u]
        for n, k in enumerate(keys):
            for e in groups[k]:
                exit_y[e] = y0 + h * (n + 1) / (len(keys) + 1)

    paths = {}
    main_in = sorted((e for e, p in plan.items() if p[0] == "main"
                      and e[1] == sink), key=lambda e: col6[e[0]])
    by_col = defaultdict(list)
    for e in main_in:
        by_col[col6[e[0]]].append(e)
    if sink is not None:
        sx, sy, sw, sh = box[sink]
        cols = sorted(by_col)
        ent = {c: sx + sw * (k + 1) / (len(cols) + 1) for k, c in enumerate(cols)}
    for e, p in plan.items():
        u, v = e
        ux, uy, uw, uh = box[u]
        vx, vy, vw, vh = box[v]
        if p[0] == "straight":
            ex = entry_x[e]
            paths[e] = [(ex, uy), (ex, vy + vh)]
        elif p[0] == "routed":
            _, gut, side, gap = p
            gx = gutter_x(gut, e)
            x0 = ux + uw if side == "R" else ux
            hy = lane_y(gap, e)
            paths[e] = [(x0, exit_y[e]), (gx, exit_y[e]), (gx, hy),
                        (entry_x[e], hy), (entry_x[e], vy + vh)]
        elif p[0] == "up":
            gx = gutter_x(p[1], e)
            x0 = ux + uw if p[2] == "R" else ux
            ty, x6 = t_y(e), gut6_x(e)
            paths[e] = [(x0, exit_y[e]), (gx, exit_y[e]), (gx, ty), (x6, ty),
                        (x6, att_y[e]), (vx + vw, att_y[e])]
        elif p[0] == "tree":
            tx = vx + 7
            cy = uy + min(uh / 2, 12)
            paths[e] = [(ux, cy), (tx, cy), (tx, vy + vh)]
        elif p[0] == "main":
            c = col6[u]
            if len(by_col[c]) == 1:
                paths[e] = [(ux + uw / 2, uy), (ent[c], sy + sh)]
            else:
                bx = col6_x(c) + 4
                cy = uy + min(uh / 2, 12)
                paths[e] = [(ux, cy), (bx, cy), (bx, up_top + 6),
                            (ent[c], sy + sh)]

    cl = []
    for name, ids, _ in clusters:
        xs = [box[i][0] for i in ids]
        ys = [box[i][1] for i in ids]
        ye = [box[i][1] + box[i][3] for i in ids]
        cl.append((name, min(xs) - PAD, min(ys) - TITLE_H, BW + 2 * PAD,
                   max(ye) - min(ys) + TITLE_H + PAD, False))
    top = []
    for k, (key, name, ids) in enumerate(proof):
        x = col6_x(k) - PAD
        top.append((f"{key}. {name}" if name else key, x, up_top,
                    BW6 + 2 * PAD, bottoms[k] - up_top, True))
    return dict(box=box, lines=lines, paths=paths, clusters=top + cl,
                sub=sub if sink is not None else [],
                kind=kind, sink=sink, width=WIDTH, height=height,
                tops={ids[0] for _, _, ids in proof},
                proof_ids=set(col6), split=(up_bottom + low_top) / 2)


# ---------------------------------------------------------------- SVG

COLORS = {"dep": "#4b5563", "inc": "#a9b4c2", "tree": "#b7791f",
          "main": "#b4432f"}

STYLE = """
.fc text { font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
.fc .band { fill: #fdfaf3; stroke: #e8d9b8; stroke-width: 1; }
.fc .cl rect { fill: #f5f6f8; stroke: #d5d9df; }
.fc .cl.top rect { fill: #fbf3e2; stroke: #e2cfa6; }
.fc .cl text { font-size: 11.5px; font-weight: 600; fill: #4a5361;
  paint-order: stroke; stroke: #f5f6f8; stroke-width: 4px; }
.fc .cl.top text { stroke: #fbf3e2; stroke-width: 5px; }
.fc .n rect { fill: #fff; stroke: #8b95a3; stroke-width: 1; }
.fc .n.side rect { stroke-dasharray: 3 2; }
.fc .n.mod rect { fill: #fff1d6; stroke: #b7791f; stroke-width: 1.4; }
.fc .n.dev rect { fill: #fffbf3; stroke: #d6a85a; stroke-width: 1; }
.fc .n.asm rect { fill: #fde2dc; stroke: #b4432f; stroke-width: 1.8; }
.fc .n text { font-size: 11.5px; fill: #1f2933; }
.fc .n text .num { font-weight: 700; }
.fc .n.asm text { font-size: 13px; }
.fc .n.asm text .sub { font-size: 11px; font-style: italic; fill: #5b2a20; }
@media screen {
  .fc .n[data-completion="done"] rect { fill: #e0eee4; }
  .fc .n[data-completion="partial"] rect { stroke: #648c79; stroke-width: 1.6; }
}
.fc a.n:hover rect, .fc a.n:focus rect { stroke: #1d4ed8; stroke-width: 2.2; }
.fc .e { fill: none; stroke-linejoin: round; }
.fc .e.dep { stroke: #4b5563; stroke-width: 1.1; }
.fc .e.inc { stroke: #a9b4c2; stroke-width: 1.1; stroke-dasharray: 4 2; }
.fc .e.tree { stroke: #b7791f; stroke-width: 1.2; }
.fc .e.main { stroke: #b4432f; stroke-width: 2; }
.fc.hl .e { opacity: 0.12; }
.fc.hl .e.on { opacity: 1; stroke-width: 2.2; }
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


def sheet_progress(page):
    try:
        source = Path(page).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    # Same escaped lists of problem IDs (including aliases) as on the index.
    ids = re.findall(r' data-progress-ids="([^"]+)"', source)
    return f' data-flowchart-progress="[{",".join(ids)}]"' if ids else ""


def render_svg(sheets, L):
    by_id = {s.id: s for s in sheets}
    sink, tops, proof_ids = L["sink"], L["tops"], L["proof_ids"]
    W, H = L["width"], L["height"]
    out = [f'<svg class="fc" xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H:.0f}" '
           f'width="{W}" height="{H:.0f}" role="img" '
           f'aria-label="How the chapters depend on each other" '
           f'style="max-width:100%;height:auto">',
           "<title>How the chapters depend on each other</title>",
           "<defs>"]
    for k, color in COLORS.items():
        out.append(f'<marker id="ah-{k}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L10,5 L0,9 z" fill="{color}"/></marker>')
    out.append(f"</defs><style>/*<![CDATA[*/{STYLE}/*]]>*/</style>")
    # The proof is set apart by a band behind its section.
    out.append(f'<rect class="band" x="{MARGIN / 2}" y="{MARGIN / 2}" '
               f'width="{W - MARGIN}" height="{L["split"]:.1f}" rx="10"/>')
    titles = []
    for name, x, y, w, h, upper in L["clusters"]:
        cls = "cl top" if upper else "cl"
        tl = wrap(name, w - 2 * PAD, 2)
        texts = "".join(f'<tspan x="{x + PAD:.1f}" dy="{0 if j == 0 else 12.5}">{esc(t)}</tspan>'
                        for j, t in enumerate(tl))
        out.append(f'<g class="{cls}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                   f'height="{h:.1f}" rx="8"/></g>')
        titles.append(f'<g class="{cls}"><text x="{x + PAD:.1f}" y="{y + 15:.1f}">'
                      f'{texts}</text></g>')
    order = {"inc": 0, "dep": 1, "tree": 2, "main": 3}
    for e in sorted(L["paths"], key=lambda e: order[L["kind"][e]]):
        u, v = e
        k = L["kind"][e]
        out.append(f'<path class="e {k}" data-u="{u}" data-v="{v}" '
                   f'd="{svg_path(L["paths"][e])}" marker-end="url(#ah-{k})">'
                   f'<title>{esc(by_id[u].num)} → {esc(by_id[v].num)}</title></path>')
    out += titles
    for s in sheets:
        if s.id not in L["box"]:
            continue
        x, y, w, h = L["box"][s.id]
        cls = ("n asm" if s.id == sink else "n mod" if s.id in tops
               else "n dev" if s.id in proof_ids else "n")
        if s.side:
            cls += " side"
        ls = L["lines"][s.id]
        big = s.id == sink
        fs = 13 if big else FS
        lh = LH + (1.5 if big else 0)
        nsub = len(L["sub"]) if big else 0
        ty = y + h / 2 - (len(ls) - 1 + nsub) * lh / 2 + fs * 0.35
        tx = x + w / 2 if big else x + 6
        anchor = ' text-anchor="middle"' if big else ""
        spans = []
        for j, t in enumerate(ls):
            dy = 0 if j == 0 else lh
            if j == 0 and t.startswith(f"{s.num}  "):
                body = (f'<tspan class="num">{esc(s.num)}</tspan>'
                        f'<tspan> {esc(t[len(s.num) + 2:])}</tspan>')
            else:
                body = esc(t)
            spans.append(f'<tspan x="{tx:.1f}" dy="{dy}">{body}</tspan>')
        if big:
            spans += [f'<tspan class="sub" x="{tx:.1f}" dy="{lh}">{esc(t)}</tspan>'
                      for t in L["sub"]]
        out.append(f'<a class="{cls}" data-id="{s.id}" href="{esc(s.html)}" '
                   f'xlink:href="{esc(s.html)}"{sheet_progress(s.html)}><title>{esc(s.num)}. {esc(s.plain)}</title>'
                   f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4"/>'
                   f'<text x="{tx:.1f}" y="{ty:.1f}"{anchor}>{"".join(spans)}</text></a>')
    out.append(f"<script>//<![CDATA[{SCRIPT}//]]></script>")
    out.append("</svg>")
    return "\n".join(out)


def render_dot(sheets, parts, L):
    by_id = {s.id: s for s in sheets}
    sink, tops, proof_ids = L["sink"], L["tops"], L["proof_ids"]
    out = ["// Generated by scripts/make-flowchart.py; do not edit.",
           "digraph chapters {", '  rankdir=BT; node [shape=box, style="rounded,filled", '
           'fillcolor=white, fontname="Helvetica", fontsize=10];',
           '  edge [color="#4b5563"];']
    for k, (key, name, ids) in enumerate(parts):
        out.append(f'  subgraph cluster_{k} {{ label="{key}. {name}"; '
                   'style=filled; color="#d5d9df"; fillcolor="#f5f6f8";')
        for i in ids:
            s = by_id[i]
            fill = ("#fde2dc" if i == sink else "#fff1d6" if i in tops
                    else "#fffaf0" if i in proof_ids else "white")
            lab = f"{s.num}. {s.plain}".replace('"', '\\"')
            out.append(f'    "{i}" [label="{lab}", URL="{s.html}", fillcolor="{fill}"];')
        out.append("  }")
    attrs = {"inc": ' [color="#a9b4c2", style=dashed]',
             "tree": ' [color="#b7791f"]',
             "main": ' [color="#b4432f", penwidth=2]'}
    for (u, v), k in sorted(L["kind"].items()):
        out.append(f'  "{u}" -> "{v}"{attrs.get(k, "")};')
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


def render_page(sheets, parts, svg, g):
    by_id = {s.id: s for s in sheets}
    side_note = [p for p in parts if by_id[p[2][0]].side]
    parts = [p for p in parts if not by_id[p[2][0]].side]
    pos = {s.id: k for k, s in enumerate(sheets)}
    with open(PLANS, encoding="utf-8") as f:
        data = json.load(f)
    checks = []
    basics = g["basics"]
    lower = (f"{basics[0][0][5:]}–{basics[-1][0][5:]}" if len(basics) > 1
             else basics[0][0][5:] if basics else "")
    intro = ("Each box is a chapter and links to it.  The shaded section on"
             " top is the proof: a column for each of its Parts, with the"
             " chapter stating the Part's results at the head and the sheets"
             " that prove them hanging below it, each under the chapter it"
             " serves.")
    if g["sink"]:
        intro += (f"  All of it feeds /{by_id[g['sink']].plain}/ at the top.")
    intro += (f"  Below, set apart, Parts {lower} treat each ingredient in its"
              " simplest setting, a column per Part read from the bottom up: a"
              " chapter sits above the chapters it builds on.  Hover over a"
              " chapter to pick out its arrows.")
    if side_note:
        intro += ("  The side series, a model in the function-field setting"
                  " that the proof does not use, is drawn under the shortest"
                  " column with dashed boxes.")
    out = ["# Generated by scripts/make-flowchart.py from the index, the sheets",
           f"# and {PLANS}; do not edit.",
           "#+TITLE: How the chapters fit together",
           "#+OPTIONS: toc:nil num:nil author:nil date:nil",
           # The chart is drawn 1200 units wide; let it use the window
           # rather than the text column.
           '#+HTML_HEAD: <script src="progress.js" defer></script>',
           "#+HTML_HEAD: <style>figure.fc-fig{position:relative;left:50%;"
           "transform:translateX(-50%);width:min(1200px,calc(100vw - 32px));"
           "margin:1em 0} figure.fc-fig svg{display:block;width:100%}</style>",
           "",
           "Back to the [[file:index.html][index]].",
           "",
           intro,
           "",
           "#+BEGIN_EXPORT html",
           '<figure class="fc-fig">',
           svg,
           "</figure>",
           "#+END_EXPORT",
           "",
           "*Legend.*  Every arrow comes from the /Prerequisites/ paragraph of"
           " the chapter it points to.",
           "- Red arrow: into the main inequality, from the frame and from the"
           " chapters stating Theorems A, B and C.",
           "- Amber line: within a Part of the proof, a sheet hangs under the"
           " chapter that names it (a sheet that no chapter of its Part names"
           " hangs under the chapter before it).  Other arrows between chapters"
           " of the proof are left out; each sheet's /Prerequisites/ lists them.",
           "- Light dashed arrow: a chapter of the proof builds on a chapter of"
           f" Parts {lower}, usually its simplest setting.  Arrows from one"
           " chapter into one column of the proof are drawn as one branching line.",
           "- Dark arrow: within Parts " f"{lower}" ", the later chapter builds"
           " on the earlier one.",
           "- An arrow is left out when a path of other arrows already leads"
           " from the one chapter to the other.",
           ]
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
    L = layout(sheets, g)
    svg = render_svg(sheets, L)
    files = {"flowchart.svg": svg + "\n",
             "flowchart.dot": render_dot(sheets, parts, L),
             "flowchart.org": render_page(sheets, parts, svg, g)}
    for name, text in files.items():
        with open(os.path.join(args.outdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    print(f"make-flowchart: {len(sheets)} chapters, {len(g['kind'])} arrows; "
          f"wrote {', '.join(files)}")


if __name__ == "__main__":
    main()
