#!/usr/bin/env python3
"""Draw how the chapters depend on each other, and render the seminar plans.

Everything is read from the sources, so the chart follows the index:

  * the index (the guide) gives the chapters, their order, numbers,
    titles, IDs and Parts;
  * each sheet's \\externaldocument lines name the sheets it cites, and
    the references in its Prerequisites paragraph say which of them it
    builds on.  These are the only arrows.  References to later chapters
    are pointers, not prerequisites, and are dropped; so is an arrow
    implied by a path of other arrows (transitive reduction).

The chart is one grid.  Below, one column per Part except the last, the
chapters of a Part stacked with the earliest at the bottom.  The last
Part (Part VI, the proof) is a row across the top, in index order from
left to right, and its last chapter, the end of the proof, sits above
that row.  Arrows within the columns run in the gutters between them and
in the gaps below the rows; arrows into the top row enter its boxes from
below; arrows inside the top row, and into the last chapter, run in the
gap above the row.  The layout and the orthogonal edge routing are done
here, so Graphviz is not needed; a DOT file is written as well, for
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
        if side:
            warn(f"side-series sheet {m.group('id')} is left out of the chart")
            continue
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


def read_deps(sheets):
    """Map each sheet ID to the IDs of the earlier sheets named in its
    Prerequisites paragraph."""
    by_id = {s.id: s for s in sheets}
    pos = {s.id: k for k, s in enumerate(sheets)}
    deps = {}
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
            elif pos[t] < pos[s.id]:
                out.add(t)
        deps[s.id] = out
    return deps


# ---------------------------------------------------------------- graph

def build_graph(sheets):
    deps = read_deps(sheets)
    edges = {(u, v) for v, us in deps.items() for u in us}
    succ = defaultdict(set)
    for (u, v) in edges:
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

    return {e for e in edges if not reaches(e[0], e[1], e)}


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



def layout(sheets, parts, edges):
    """One grid: a column per Part but the last, the earliest chapter of
    a Part at the bottom; the last Part as a row on top, its last chapter
    above the row."""
    if len(parts) < 2:
        die("the chart needs at least two Parts")
    col_parts, (top_key, top_name, top_ids) = parts[:-1], parts[-1]
    if len(top_ids) < 2:
        die(f"{top_key} needs at least two chapters")
    row_ids, top = top_ids[:-1], top_ids[-1]
    C, K = len(col_parts), len(row_ids)
    col_of, row_of = {}, {}
    for c, (_, _, ids) in enumerate(col_parts):
        for r, i in enumerate(reversed(ids)):
            col_of[i], row_of[i] = c, r
    rows = max(len(p[2]) for p in col_parts)
    kcol = {i: k for k, i in enumerate(row_ids)}

    # Classify the edges, and choose sides and gutters from estimated
    # positions (as fractions of the width).
    plan = {}
    for (u, v) in edges:
        if u in col_of and v in col_of:
            cu, ru, cv, rv = col_of[u], row_of[u], col_of[v], row_of[v]
            if cu == cv and ru == rv + 1:
                plan[(u, v)] = ("straight",)
            else:
                gut, side = (cu + 1, "R") if cv > cu else (cu, "L")
                plan[(u, v)] = ("routed", gut, side, rv)
        elif u in col_of:
            cu = col_of[u]
            if v == top:
                rg = min(K, max(0, round((cu + 0.5) / C * K)))
                dest = rg / K
            else:
                rg, dest = None, (kcol[v] + 0.5) / K
            gut, side = (cu + 1, "R") if dest > (cu + 0.5) / C else (cu, "L")
            plan[(u, v)] = ("up", gut, side, rg) if v != top else ("uptop", gut, side, rg)
        elif v == top:
            plan[(u, v)] = ("rt",)
        else:
            plan[(u, v)] = ("rr",)

    # Vertical lanes in the gutters of the columns (in row units: row r at
    # r, the gap below it at r + 0.5, the transfer gap at -0.5) and of the
    # top row.
    gutter_iv = defaultdict(dict)
    rgut_iv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            _, gut, side, gap = p
            ru = row_of[e[0]]
            gutter_iv[gut][e] = (min(ru, gap + 0.5), max(ru, gap + 0.5))
        elif p[0] in ("up", "uptop"):
            gutter_iv[p[1]][e] = (-0.5, row_of[e[0]])
            if p[0] == "uptop":
                rgut_iv[p[3]][e] = (0, 1)
    lanes_g, nlanes_g = {}, {}
    for gut, iv in gutter_iv.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        lanes_g.update(ln)
        nlanes_g[gut] = n
    lanes_r, nlanes_r = {}, {}
    for gut, iv in rgut_iv.items():
        ln, n = assign_lanes({e: (a * 10, b * 10) for e, (a, b) in iv.items()})
        lanes_r.update(ln)
        nlanes_r[gut] = n
    GW = max(36, 2 * PAD + 10 + max(nlanes_g.values(), default=1) * LANE)
    BW = (WIDTH - 2 * MARGIN - (C + 1) * GW) / C
    GWr = max(18, 10 + max(nlanes_r.values(), default=1) * LANE)
    BWr = (WIDTH - 2 * MARGIN - (K + 1) * GWr) / K

    def col_x(c):
        return MARGIN + GW + c * (BW + GW)

    def gutter_x(gut, e):
        n = nlanes_g[gut]
        return MARGIN + gut * (BW + GW) + GW / 2 + (lanes_g[e] - (n - 1) / 2) * LANE

    def rcol_x(k):
        return MARGIN + GWr + k * (BWr + GWr)

    def rgut_x(gut, e):
        n = nlanes_r[gut]
        return MARGIN + gut * (BWr + GWr) + GWr / 2 + (lanes_r[e] - (n - 1) / 2) * LANE

    a_w = min(max(2 * BWr + GWr, 0.34 * WIDTH), WIDTH - 2 * MARGIN)
    a_x = WIDTH / 2 - a_w / 2

    by_id = {s.id: s for s in sheets}
    lines = {}
    for i in col_of:
        s = by_id[i]
        lines[i] = wrap(f"{s.num}  {s.plain}", BW - 12)
    for i in row_ids:
        s = by_id[i]
        lines[i] = wrap(f"{s.num}  {s.plain}", BWr - 12, 6)
    lines[top] = wrap(f"{by_id[top].num}  {by_id[top].plain}", a_w - 12, 2)
    BH = max(len(lines[i]) for i in col_of) * LH + 10
    BHr = max(len(lines[i]) for i in row_ids) * LH + 10
    A_H = len(lines[top]) * LH + 14

    # Attachment points on the top row and the last chapter.
    def center(i):
        if i == top:
            return WIDTH / 2
        if i in kcol:
            return rcol_x(kcol[i]) + BWr / 2
        return col_x(col_of[i]) + BW / 2

    def src_x(e):
        p = plan[e]
        if p[0] == "up":
            return gutter_x(p[1], e)
        if p[0] == "uptop":
            return rgut_x(p[3], e)
        return center(e[0])

    def spread(x0, w, lst):
        lst.sort(key=lambda t: t[0])
        return {key: x0 + w * 0.12 + w * 0.76 * (k + 1) / (len(lst) + 1)
                for k, (_, key) in enumerate(lst)}

    bottom_in = defaultdict(list)      # row box or top <- from below
    top_att = defaultdict(list)        # row box top: (other x, (e, end))
    entries = defaultdict(list)        # lower boxes, from below
    for e, p in plan.items():
        u, v = e
        if p[0] == "up":
            bottom_in[v].append((gutter_x(p[1], e), e))
        elif p[0] in ("uptop", "rt"):
            bottom_in[top].append((src_x(e), e))
            if p[0] == "rt":
                top_att[u].append((WIDTH / 2, (e, "u")))
        elif p[0] == "rr":
            top_att[u].append((center(v), (e, "u")))
            top_att[v].append((center(u), (e, "v")))
        elif p[0] == "straight":
            entries[v].append((col_x(col_of[v]) + BW / 2, e))
        else:
            entries[v].append((gutter_x(p[1], e), e))
    in_x = {}
    for v, lst in bottom_in.items():
        if v == top:
            in_x.update(spread(a_x, a_w, lst))
        else:
            in_x.update(spread(rcol_x(kcol[v]), BWr, lst))
    att_x = {}
    for v, lst in top_att.items():
        att_x.update(spread(rcol_x(kcol[v]), BWr, lst))
    entry_x = {}
    for v, lst in entries.items():
        entry_x.update(spread(col_x(col_of[v]), BW, lst))

    # Horizontal lanes: gap "A" above the top row, the transfer gap -1
    # below it, and the gaps r below the rows of the columns.
    gap_iv = defaultdict(dict)
    for e, p in plan.items():
        if p[0] == "routed":
            gx = gutter_x(p[1], e)
            gap_iv[p[3]][e] = (min(gx, entry_x[e]), max(gx, entry_x[e]))
        elif p[0] == "up":
            gx = gutter_x(p[1], e)
            gap_iv[-1][e] = (min(gx, in_x[e]), max(gx, in_x[e]))
        elif p[0] == "uptop":
            gx, rx = gutter_x(p[1], e), rgut_x(p[3], e)
            gap_iv[-1][e] = (min(gx, rx), max(gx, rx))
            gap_iv["A"][e] = (min(rx, in_x[e]), max(rx, in_x[e]))
        elif p[0] == "rt":
            ux = att_x[(e, "u")]
            gap_iv["A"][e] = (min(ux, in_x[e]), max(ux, in_x[e]))
        elif p[0] == "rr":
            ux, vx = att_x[(e, "u")], att_x[(e, "v")]
            gap_iv["A"][e] = (min(ux, vx), max(ux, vx))
    lanes_h, nlanes_h = {}, {}
    for gap, iv in gap_iv.items():
        ln, n = assign_lanes(iv)
        for e, k in ln.items():
            lanes_h[(gap, e)] = k
        nlanes_h[gap] = n

    def gap_h(gap):
        return 10 + nlanes_h.get(gap, 0) * LANE

    # Vertical positions.
    TITLE_H = 2 * 12 + 8
    TOP_TITLE = 22
    y = MARGIN + PAD + TOP_TITLE
    a_y = y
    y += A_H
    gap_top = {"A": y}
    y += gap_h("A")
    r_y = y
    y += BHr + PAD
    gap_top[-1] = y
    y += gap_h(-1) + TITLE_H
    row_y = {}
    for r in range(rows):
        row_y[r] = y
        y += BH
        gap_top[r] = y
        y += gap_h(r)
    height = y + MARGIN

    def lane_y(gap, e):
        return gap_top[gap] + 5 + (lanes_h[(gap, e)] + 0.5) * LANE

    box = {}
    for i in col_of:
        box[i] = (col_x(col_of[i]), row_y[row_of[i]], BW, BH)
    for i in row_ids:
        box[i] = (rcol_x(kcol[i]), r_y, BWr, BHr)
    box[top] = (a_x, a_y, a_w, A_H)

    exits = defaultdict(list)
    for e, p in plan.items():
        if p[0] in ("routed", "up", "uptop"):
            exits[(e[0], p[2])].append(e)
    exit_y = {}
    for (u, side), lst in exits.items():
        lst.sort(key=lambda e: lane_y(plan[e][3] if plan[e][0] == "routed" else -1, e))
        x, y0, w, h = box[u]
        for k, e in enumerate(lst):
            exit_y[e] = y0 + h * (k + 1) / (len(lst) + 1)

    paths = {}
    for e, p in plan.items():
        u, v = e
        ux, uy, uw, uh = box[u]
        vx, vy, vw, vh = box[v]
        if p[0] == "straight":
            ex = entry_x[e]
            paths[e] = [(ex, uy), (ex, vy + vh)]
        elif p[0] == "routed":
            gx = gutter_x(p[1], e)
            sx = ux + uw if p[2] == "R" else ux
            hy = lane_y(p[3], e)
            ex = entry_x[e]
            paths[e] = [(sx, exit_y[e]), (gx, exit_y[e]), (gx, hy),
                        (ex, hy), (ex, vy + vh)]
        elif p[0] in ("up", "uptop"):
            gx = gutter_x(p[1], e)
            sx = ux + uw if p[2] == "R" else ux
            hy = lane_y(-1, e)
            pts = [(sx, exit_y[e]), (gx, exit_y[e]), (gx, hy)]
            if p[0] == "up":
                pts += [(in_x[e], hy), (in_x[e], vy + vh)]
            else:
                rx, ha = rgut_x(p[3], e), lane_y("A", e)
                pts += [(rx, hy), (rx, ha), (in_x[e], ha), (in_x[e], vy + vh)]
            paths[e] = pts
        elif p[0] == "rt":
            ux0, ha = att_x[(e, "u")], lane_y("A", e)
            paths[e] = [(ux0, uy), (ux0, ha), (in_x[e], ha), (in_x[e], vy + vh)]
        else:
            ux0, vx0, ha = att_x[(e, "u")], att_x[(e, "v")], lane_y("A", e)
            paths[e] = [(ux0, uy), (ux0, ha), (vx0, ha), (vx0, vy)]

    clusters = []
    xs = [box[i][0] for i in row_ids]
    clusters.append((f"{top_key}. {top_name}" if top_name else top_key,
                     min(xs) - PAD, a_y - TOP_TITLE,
                     max(xs) + BWr + PAD - (min(xs) - PAD),
                     r_y + BHr + PAD - (a_y - TOP_TITLE)))
    for key, name, ids in col_parts:
        ys = [box[i][1] for i in ids]
        ye = [box[i][1] + box[i][3] for i in ids]
        clusters.append((f"{key}. {name}" if name else key,
                         box[ids[0]][0] - PAD, min(ys) - TITLE_H,
                         BW + 2 * PAD, max(ye) - min(ys) + TITLE_H + PAD))
    return dict(box=box, lines=lines, paths=paths, clusters=clusters,
                plan=plan, top=top, row_ids=row_ids,
                width=WIDTH, height=height)


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
.fc .n.asm rect { fill: #fde2dc; stroke: #b4432f; stroke-width: 1.8; }
.fc .n text { font-size: 11.5px; fill: #1f2933; }
.fc .n text .num { font-weight: 700; }
.fc .n.asm text { font-size: 13px; }
.fc a.n:hover rect, .fc a.n:focus rect { stroke: #1d4ed8; stroke-width: 2.2; }
.fc .e { fill: none; stroke-linejoin: round; }
.fc .e.dep { stroke: #4b5563; stroke-width: 1.1; }
.fc .e.inc { stroke: #a9b4c2; stroke-width: 1.1; stroke-dasharray: 4 2; }
.fc .e.top { stroke: #b7791f; stroke-width: 1.3; }
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


def edge_kind(L, e):
    """Dark within Parts I-V, light dashed from them into the last Part,
    amber inside the last Part."""
    p = L["plan"][e][0]
    return {"straight": "dep", "routed": "dep", "up": "inc",
            "uptop": "inc"}.get(p, "top")


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


def render_svg(sheets, L):
    by_id = {s.id: s for s in sheets}
    top, row = L["top"], set(L["row_ids"])
    W, H = L["width"], L["height"]
    out = [f'<svg class="fc" xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H:.0f}" '
           f'width="{W}" height="{H:.0f}" role="img" '
           f'aria-label="How the chapters depend on each other" '
           f'style="max-width:100%;height:auto">',
           "<title>How the chapters depend on each other</title>",
           "<defs>"]
    for kind, color in (("dep", "#4b5563"), ("inc", "#a9b4c2"), ("top", "#b7791f")):
        out.append(f'<marker id="ah-{kind}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L10,5 L0,9 z" fill="{color}"/></marker>')
    out.append(f"</defs><style>/*<![CDATA[*/{STYLE}/*]]>*/</style>")
    titles = []
    for k, (name, x, y, w, h) in enumerate(L["clusters"]):
        cls = "cl top" if k == 0 else "cl"
        tl = wrap(name, (w if k else 0.3 * w) - 2 * PAD, 2)
        texts = "".join(f'<tspan x="{x + PAD:.1f}" dy="{0 if j == 0 else 12.5}">{esc(t)}</tspan>'
                        for j, t in enumerate(tl))
        out.append(f'<g class="{cls}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                   f'height="{h:.1f}" rx="8"/></g>')
        titles.append(f'<g class="{cls}"><text x="{x + PAD:.1f}" y="{y + 15:.1f}">'
                      f'{texts}</text></g>')
    order = {"inc": 0, "dep": 1, "top": 2}
    for e in sorted(L["paths"], key=lambda e: order[edge_kind(L, e)]):
        u, v = e
        kind = edge_kind(L, e)
        out.append(f'<path class="e {kind}" data-u="{u}" data-v="{v}" '
                   f'd="{svg_path(L["paths"][e])}" marker-end="url(#ah-{kind})">'
                   f'<title>{esc(by_id[u].num)} → {esc(by_id[v].num)}</title></path>')
    out += titles
    for s in sheets:
        if s.id not in L["box"]:
            continue
        x, y, w, h = L["box"][s.id]
        cls = "n asm" if s.id == top else "n mod" if s.id in row else "n"
        ls = L["lines"][s.id]
        fs = 13 if s.id == top else FS
        lh = LH + (1.5 if s.id == top else 0)
        ty = y + h / 2 - (len(ls) - 1) * lh / 2 + fs * 0.35
        tx = x + 6 if s.id != top else x + w / 2
        anchor = "" if s.id != top else ' text-anchor="middle"'
        spans = []
        for j, t in enumerate(ls):
            dy = 0 if j == 0 else lh
            if j == 0 and t.startswith(f"{s.num}  "):
                body = (f'<tspan class="num">{esc(s.num)}</tspan>'
                        f'<tspan> {esc(t[len(s.num) + 2:])}</tspan>')
            else:
                body = esc(t)
            spans.append(f'<tspan x="{tx:.1f}" dy="{dy}">{body}</tspan>')
        out.append(f'<a class="{cls}" data-id="{s.id}" href="{esc(s.html)}" '
                   f'xlink:href="{esc(s.html)}"><title>{esc(s.num)}. {esc(s.plain)}</title>'
                   f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4"/>'
                   f'<text x="{tx:.1f}" y="{ty:.1f}"{anchor}>{"".join(spans)}</text></a>')
    out.append(f"<script>//<![CDATA[{SCRIPT}//]]></script>")
    out.append("</svg>")
    return "\n".join(out)


def render_dot(sheets, parts, L):
    by_id = {s.id: s for s in sheets}
    top, row = L["top"], set(L["row_ids"])
    out = ["// Generated by scripts/make-flowchart.py; do not edit.",
           "digraph chapters {", '  rankdir=BT; node [shape=box, style="rounded,filled", '
           'fillcolor=white, fontname="Helvetica", fontsize=10];',
           '  edge [color="#4b5563"];']
    for k, (key, name, ids) in enumerate(parts):
        out.append(f'  subgraph cluster_{k} {{ label="{key}. {name}"; '
                   'style=filled; color="#d5d9df"; fillcolor="#f5f6f8";')
        for i in ids:
            s = by_id[i]
            fill = "#fde2dc" if i == top else "#fff1d6" if i in row else "white"
            label = f"{s.num}. {s.plain}".replace('"', '\\"')
            out.append(f'    "{i}" [label="{label}", URL="{s.html}", fillcolor="{fill}"];')
        out.append("  }")
    for (u, v) in sorted(L["paths"]):
        kind = edge_kind(L, (u, v))
        attrs = {"inc": ' [color="#a9b4c2", style=dashed]',
                 "top": ' [color="#b7791f"]'}.get(kind, "")
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


def render_page(sheets, parts, svg):
    by_id = {s.id: s for s in sheets}
    pos = {s.id: k for k, s in enumerate(sheets)}
    top_key, top_name, top_ids = parts[-1]
    top = by_id[top_ids[-1]]
    with open(PLANS, encoding="utf-8") as f:
        data = json.load(f)
    checks = []
    lower = f"{parts[0][0][5:]}–{parts[-2][0][5:]}" if len(parts) > 2 else parts[0][0][5:]
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
           f"Each box is a chapter and links to it.  Parts {lower} are the"
           " columns, read from the bottom up: a chapter sits above the chapters"
           f" of its Part that it builds on.  {top_key}, /{top_name}/, is the row"
           " across the top, where each ingredient is stated in the generality"
           f" of the proof; above it is the last chapter, /{top.title}/.  Hover"
           " over a chapter to pick out its arrows.",
           "",
           "#+BEGIN_EXPORT html",
           '<figure class="fc-fig">',
           svg,
           "</figure>",
           "#+END_EXPORT",
           "",
           "*Legend.*  Every arrow comes from the /Prerequisites/ paragraph of"
           " the chapter it points to.",
           f"- Dark arrow: within Parts {lower}, the later chapter builds on the"
           " earlier one.",
           f"- Light dashed arrow: a chapter of {top_key} builds on a chapter of"
           f" Parts {lower}, usually its simplest setting.",
           f"- Amber arrow: within {top_key}.",
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
    edges = build_graph(sheets)
    L = layout(sheets, parts, edges)
    svg = render_svg(sheets, L)
    files = {"flowchart.svg": svg + "\n",
             "flowchart.dot": render_dot(sheets, parts, L),
             "flowchart.org": render_page(sheets, parts, svg)}
    for name, text in files.items():
        with open(os.path.join(args.outdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    print(f"make-flowchart: {len(sheets)} chapters, {len(edges)} arrows; "
          f"wrote {', '.join(files)}")


if __name__ == "__main__":
    main()
