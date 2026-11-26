#!/usr/bin/env python3
"""Stable tags for the chapters, sections and numbered results.

Chapter, section and problem numbers change whenever a chapter or a
problem is inserted.  A tag, as in the Stacks project, does not: it is a
four-character name such as 2B7K that keeps pointing at the same item,
so that a reader can cite "Tag 2B7K" or link to tag/2B7K.html.

The tags are recorded in tags.tsv, one per line:

    TAG <TAB> SHEET <TAB> LABEL [<TAB> STATUS]

SHEET is the Denote timestamp of the sheet (the start of its file name),
LABEL the LaTeX label of the item, empty for the chapter itself, and
STATUS is empty, or "retired", "retired -> TAG2" (replaced by TAG2),
optionally followed by "; note".  Lines starting with # are comments.

Tags are drawn from 0-9 and A-Z without 0, O, 1 and I, and are assigned
in order.  A tag is never reused, reassigned or deleted: an item that is
removed keeps its line, marked retired.

Usage, from the repository root:

  scripts/make-tags.py            tag every untagged chapter, \\section
                                  and labelled result of the stable
                                  Parts (STABLE below), appending lines
                                  to tags.tsv; existing lines are kept
  scripts/make-tags.py --check    change nothing; fail if a tagged label
                                  has disappeared without being retired,
                                  or a tag or an item occurs twice; list
                                  untagged items (a warning, or an
                                  error with --strict)
  scripts/make-tags.py --check --since REV
                                  also fail if a line of tags.tsv at git
                                  revision REV was changed or deleted,
                                  other than by marking it retired
  scripts/make-tags.py --site DIR write DIR/tag/TAG.html (a redirect to
                                  the item) for every tag, and
                                  DIR/tags.html (the list), reading the
                                  numbers from DIR/*.aux
"""
import glob
import html
import json
import os
import re
import sys
import unicodedata

GUIDE = "20261125T012000--grh-workbook__guide.org"
TAGS = "tags.tsv"
CHAPTERS = "chapters.tex"

# The chapters whose items are tagged: the Parts (by their Roman numeral
# in the index heading "* Part I. ...") and the side-series sheets (by
# their names, "S1. ...").  Extend this when a Part settles.
STABLE_PARTS = ["I", "II", "III", "IV", "V"]
STABLE_SIDE = ["S1", "S2"]

# Sheets whose tags were retired by mistake and are live again: a tag of
# one of these sheets may go from retired to live.  Each entry needs a
# reason; see CONTRIBUTING.md.  (Never use this for an item that was
# really removed: retire it and give the new item a new tag.)
UNRETIRED = {
    # Withdrawn on 26 Nov 2026 and restored the same day, unchanged,
    # by the owner's decision (Stepanov; side series S1, S2).
    "20261125T007000", "20261124T220500", "20261124T221500",
}

# Environments whose labelled instances are tagged.
TAGGED_ENVS = ["problem", "theorem", "proposition", "lemma", "definition"]

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
TAG_RE = re.compile(f"^[{ALPHABET}]{{4}}$")
STATUS_RE = re.compile(
    r"^retired(?:\s*->\s*(?P<by>\S+))?\s*(?:;\s*(?P<note>.*))?$")

HEADER = """\
# Stable tags of the GRH workbook: TAG, SHEET (Denote timestamp), LABEL
# (empty for the chapter itself), and an optional STATUS ("retired",
# "retired -> TAG2", optionally followed by "; note"), separated by tabs.
# Never edit or delete a line: run scripts/make-tags.py to add tags, and
# mark a removed item retired.  See CONTRIBUTING.md.
"""

LINK = re.compile(
    r"^\s*- \[\[file:(?P<id>\d{8}T\d{6})--(?P<slug>[^\]]*?)__workbook\.html\]"
    r"\[(?P<label>[^\]]*)\]\]")


def die(msg):
    sys.exit(f"make-tags: {msg}")


# ---------------------------------------------------------------- tags.tsv

class Entry:
    def __init__(self, lineno, tag, sheet, label, status):
        self.lineno, self.tag, self.sheet = lineno, tag, sheet
        self.label, self.status = label, status
        m = STATUS_RE.match(status) if status else None
        self.retired = bool(m)
        self.by = m.group("by") if m else None
        self.note = (m.group("note") or "") if m else ""


def read_tags(path=TAGS):
    """Return the lines of tags.tsv as Entries, and a list of errors."""
    entries, errors = [], []
    if not os.path.exists(path):
        return entries, errors
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 2 or len(cols) > 4:
                errors.append(f"{path}:{n}: expected 2-4 tab-separated columns")
                continue
            cols += [""] * (4 - len(cols))
            tag, sheet, label, status = (c.strip() for c in cols)
            e = Entry(n, tag, sheet, label, status)
            if not TAG_RE.match(tag):
                errors.append(f"{path}:{n}: malformed tag {tag!r}")
            if not re.match(r"^\d{8}T\d{6}$", sheet):
                errors.append(f"{path}:{n}: malformed sheet {sheet!r}")
            if status and not e.retired:
                errors.append(f"{path}:{n}: unknown status {status!r}")
            entries.append(e)
    return entries, errors


def tag_index(tag):
    n = 0
    for c in tag:
        n = n * len(ALPHABET) + ALPHABET.index(c)
    return n


def index_tag(n):
    s = ""
    for _ in range(4):
        n, r = divmod(n, len(ALPHABET))
        s = ALPHABET[r] + s
    if n:
        die("out of tags")
    return s


# ------------------------------------------------------------------ index

def read_index():
    """Return [(id, slug, number, part)] in index order.  PART is the
    Roman numeral of the Part, or "side" for the side series."""
    with open(GUIDE, encoding="utf-8") as f:
        guide = f.read()
    out, part = [], None
    for line in guide.split("\n"):
        if line.startswith("* "):
            heading = line[2:].strip()
            pm = re.match(r"^Part ([IVXLC]+)\.", heading)
            part = (pm.group(1) if pm else
                    "side" if "side series" in heading.lower() else heading)
            continue
        m = LINK.match(line)
        if m:
            num = re.match(r"^\s*([A-Z]*\d+)\.", m.group("label"))
            out.append((m.group("id"), m.group("slug"),
                        num.group(1) if num else "", part))
    return out


def stable_sheets():
    return [(i, s) for i, s, num, part in read_index()
            if (part in STABLE_PARTS
                or (part == "side" and num in STABLE_SIDE))]


def sheet_file(ident, ext=".tex", directory="."):
    hits = sorted(glob.glob(os.path.join(directory, f"{ident}--*__workbook{ext}")))
    return hits[0] if hits else None


# ------------------------------------------------------------- TeX source

def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def balanced(s, i, open_="{", close="}"):
    """If s[i] is OPEN_, return the index after its matching CLOSE."""
    if i >= len(s) or s[i] != open_:
        return None
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return None


def skip_ws(s, i):
    while i < len(s) and s[i] in " \t\n":
        i += 1
    return i


LABEL_AT = re.compile(r"\\label\{([^}]*)\}")


def items(tex):
    """Return the taggable items of TEX in order as (label, kind, title):
    labelled \\section's (kind "section") and labelled environments in
    TAGGED_ENVS (kind the environment).  The label must follow the
    command, or the environment's optional argument, directly."""
    tex = strip_comments(tex)
    out = []
    pat = re.compile(r"\\section(?![a-zA-Z*])|\\begin\{(" +
                     "|".join(TAGGED_ENVS) + r")\}")
    for m in pat.finditer(tex):
        i = m.end()
        title = ""
        if m.group(1):
            kind = m.group(1)
            j = skip_ws(tex, i)
            if j < len(tex) and tex[j] == "[":
                k = balanced(tex, j, "[", "]")
                if k:
                    title, i = tex[j + 1:k - 1], k
        else:
            kind = "section"
            j = skip_ws(tex, i)
            if j < len(tex) and tex[j] == "[":
                j = skip_ws(tex, balanced(tex, j, "[", "]") or j + 1)
            k = balanced(tex, j)
            if not k:
                continue
            title, i = tex[j + 1:k - 1], k
        lm = LABEL_AT.match(tex, skip_ws(tex, i))
        if lm:
            out.append((lm.group(1), kind, title.strip()))
    return out


def all_labels(tex):
    return set(LABEL_AT.findall(strip_comments(tex)))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------- assign/check

def untagged(entries):
    """The taggable items of the stable sheets without a live tag."""
    have = {(e.sheet, e.label) for e in entries if not e.retired}
    out = []
    for ident, slug in stable_sheets():
        path = sheet_file(ident)
        if not path:
            die(f"the index lists {ident}--{slug}, which has no .tex file")
        if (ident, "") not in have:
            out.append((ident, "", "chapter", path))
        for label, kind, _ in items(read(path)):
            if (ident, label) not in have:
                out.append((ident, label, kind, path))
    return out


def check(entries, errors, strict):
    seen_tag, seen_item = {}, {}
    tags = {e.tag for e in entries}
    for e in entries:
        if e.tag in seen_tag:
            errors.append(f"{TAGS}:{e.lineno}: tag {e.tag} also on line "
                          f"{seen_tag[e.tag]}")
        seen_tag.setdefault(e.tag, e.lineno)
        if e.retired:
            if e.by and e.by not in tags:
                errors.append(f"{TAGS}:{e.lineno}: {e.tag} is replaced by "
                              f"{e.by}, which is not a tag")
            continue
        key = (e.sheet, e.label)
        if key in seen_item:
            errors.append(f"{TAGS}:{e.lineno}: {e.sheet} {e.label or '(chapter)'}"
                          f" already has tag {seen_item[key]}")
        seen_item.setdefault(key, e.tag)
        path = sheet_file(e.sheet)
        if not path:
            errors.append(f"{TAGS}:{e.lineno}: tag {e.tag}: sheet {e.sheet} "
                          "has disappeared; mark the tag retired")
        elif e.label and e.label not in all_labels(read(path)):
            errors.append(f"{TAGS}:{e.lineno}: tag {e.tag}: label "
                          f"{e.label} has disappeared from {path}; restore it "
                          "or mark the tag retired")
    missing = untagged(entries)
    for ident, label, kind, path in missing:
        msg = f"untagged {kind} {label or ''} in {path}".replace("  ", " ")
        (errors.append if strict else print)(
            msg if strict else f"make-tags: warning: {msg}")
    if missing and not strict:
        print(f"make-tags: warning: {len(missing)} untagged items; "
              "run scripts/make-tags.py")
    if errors:
        for err in errors:
            print(f"make-tags: {err}", file=sys.stderr)
        sys.exit(1)


def check_since(entries, errors, rev):
    """Append to ERRORS the lines of tags.tsv at REV that were changed."""
    import subprocess
    import tempfile
    r = subprocess.run(["git", "show", f"{rev}:{TAGS}"], capture_output=True,
                       text=True)
    if r.returncode:
        print(f"make-tags: no {TAGS} at {rev}; nothing to compare")
        return
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
        f.write(r.stdout)
    try:
        old, _ = read_tags(f.name)
    finally:
        os.remove(f.name)
    now = {e.tag: e for e in entries}
    for o in old:
        e = now.get(o.tag)
        if e is None:
            errors.append(f"tag {o.tag} ({o.sheet} {o.label}) was deleted; "
                          "a tag is never deleted, only retired")
        elif (e.sheet, e.label) != (o.sheet, o.label):
            errors.append(f"tag {o.tag} was moved from {o.sheet} {o.label} to "
                          f"{e.sheet} {e.label}; retire it instead")
        elif o.retired and not e.retired and o.sheet not in UNRETIRED:
            errors.append(f"tag {o.tag} was retired at {rev} and is live again")


def assign(entries, errors):
    if errors:
        for err in errors:
            print(f"make-tags: {err}", file=sys.stderr)
        die(f"fix {TAGS} first")
    nxt = max((tag_index(e.tag) + 1 for e in entries), default=0)
    new = []
    for ident, label, _, _ in untagged(entries):
        new.append(f"{index_tag(nxt)}\t{ident}\t{label}\n")
        nxt += 1
    if not new:
        return
    exists = os.path.exists(TAGS)
    with open(TAGS, "a", encoding="utf-8") as f:
        if not exists:
            f.write(HEADER)
        f.writelines(new)
    print(f"make-tags: added {len(new)} tags to {TAGS}")


# ------------------------------------------------------------------- site

def aux_labels(path):
    """Map label -> (number, title) from the \\newlabel lines of PATH."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    for line in read(path).split("\n"):
        if not line.startswith("\\newlabel{"):
            continue
        k = balanced(line, len("\\newlabel"))
        if not k:
            continue
        label = line[len("\\newlabel") + 1:k - 1]
        args, i = [], k + 1
        while i < len(line) and line[i] == "{" and len(args) < 3:
            j = balanced(line, i)
            if not j:
                break
            args.append(line[i + 1:j - 1])
            i = j
        if args:
            out[label] = (args[0], args[2] if len(args) > 2 else "")
    return out


def chapter_numbers(directory):
    path = os.path.join(directory, CHAPTERS)
    if not os.path.exists(path):
        path = CHAPTERS
    return dict(re.findall(r"\\chapters@set\{([^}]*)\}\{([^}]*)\}", read(path)))


def sheet_title(tex):
    m = re.search(r"\\title(?:\[[^\]]*\])?\{", tex)
    if not m:
        return ""
    k = balanced(tex, m.end() - 1)
    return tex[m.end():k - 1] if k else ""


def macros(tex):
    """The argument-free \\newcommand's and \\DeclareMathOperator's of TEX,
    as a map from name to replacement."""
    out = {}
    tex = strip_comments(tex)
    for m in re.finditer(r"\\(?:re)?newcommand\*?\{?\\([a-zA-Z]+)\}?(?=\{)", tex):
        k = balanced(tex, m.end())
        if k:
            out[m.group(1)] = tex[m.end() + 1:k - 1]
    for m in re.finditer(r"\\DeclareMathOperator(\*?)\{\\([a-zA-Z]+)\}(?=\{)", tex):
        k = balanced(tex, m.end())
        if k:
            op = "operatorname" + m.group(1)
            out[m.group(2)] = f"\\{op}{{{tex[m.end() + 1:k - 1]}}}"
    return out


def expand(s, defs):
    """Expand the macros DEFS in S (a few rounds, for nested ones)."""
    for _ in range(4):
        t = re.sub(r"\\([a-zA-Z]+)(?![a-zA-Z])",
                   lambda m: defs.get(m.group(1), m.group(0)), s)
        if t == s:
            break
        s = t
    return s


def detex(s, defs=None):
    """Text for HTML, leaving math to MathJax."""
    s = s.strip()
    if s.startswith("{") and balanced(s, 0) == len(s):
        s = s[1:-1]
    s = re.sub(r"\\cite\[([^\]]*)\]\{([^}]*)\}", r"[\2, \1]", s)
    s = re.sub(r"\\cite\{([^}]*)\}", r"[\1]", s)
    if defs:
        s = expand(s, defs)
    while True:
        m = re.search(r"\\texorpdfstring(?=\{)", s)
        j = m and balanced(s, m.end())
        k = j and balanced(s, j)
        if not k:
            break
        s = s[:m.start()] + s[m.end() + 1:j - 1] + s[k:]
    s = re.sub(r"\\(?:emph|textit|textbf|textrm|mbox|text)\{([^{}]*)\}", r"\1", s)
    accents = {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302",
               "~": "\u0303", "c": "\u0327", "v": "\u030c", "u": "\u0306",
               "=": "\u0304", "H": "\u030b"}
    s = re.sub(r"\\([\"'`^~=]|[cvuH](?![a-zA-Z]))\s*\{?([a-zA-Z])\}?",
               lambda m: m.group(2) + accents[m.group(1)], s)
    for a, b in [("---", "\u2014"), ("--", "\u2013"), ("``", "\u201c"),
                 ("''", "\u201d"), ("~", " "), ("\\&", "&"), ("\\,", " "),
                 ("\\S", "\u00a7"), ("\\ ", " ")]:
        parts = re.split(r"(\$[^$]*\$)", s)
        s = "".join(p if p.startswith("$") else p.replace(a, b) for p in parts)
    return html.escape(unicodedata.normalize("NFC", s.strip()), quote=False)


def site(directory):
    entries, errors = read_tags()
    if errors:
        for err in errors:
            print(f"make-tags: {err}", file=sys.stderr)
        sys.exit(1)
    chapnum = chapter_numbers(directory)
    by_tag = {e.tag: e for e in entries}
    cache = {}

    def info(e):
        """(page, anchor, chapter, kind, number, title) for entry E."""
        if e.sheet not in cache:
            tex = sheet_file(e.sheet, directory=directory) or sheet_file(e.sheet)
            src = read(tex) if tex else ""
            page = os.path.basename(tex)[:-4] + ".html" if tex else None
            aux = aux_labels(tex[:-4] + ".aux") if tex else {}
            found = {lab: (kind, title) for lab, kind, title in items(src)}
            cache[e.sheet] = (page, chapnum.get(e.sheet, "?"), aux, found,
                              detex(sheet_title(src)), macros(src))
        page, chap, aux, found, ctitle, defs = cache[e.sheet]
        if not e.label:
            return page, "", chap, "Chapter", chap, ctitle
        kind, title = found.get(e.label, ("item", ""))
        number = aux.get(e.label, ("?", ""))[0]
        if kind == "section":
            return page, e.label, chap, "Section", "\u00a7" + number, detex(title, defs)
        return (page, e.label, chap, kind.capitalize(), number,
                detex(title, defs))

    tagdir = os.path.join(directory, "tag")
    os.makedirs(tagdir, exist_ok=True)
    for old in glob.glob(os.path.join(tagdir, "*.html")):
        os.remove(old)

    head = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>{title}</title>\n{extra}'
            '<link rel="stylesheet" href="{css}">\n'
            '<script>window.MathJax = {{tex: {{inlineMath: [["$","$"],["\\\\(","\\\\)"]]}}}};</script>\n'
            '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js"></script>\n'
            '</head>\n<body>\n')

    def describe(e):
        page, anchor, chap, kind, number, title = info(e)
        what = (f"Chapter {chap}" if kind == "Chapter"
                else f"{kind} {number} of Chapter {chap}")
        return what + (f", <em>{title}</em>" if title else "")

    rows, retired = [], []
    for e in entries:
        path = os.path.join(tagdir, e.tag + ".html")
        if e.retired:
            target = by_tag.get(e.by) if e.by else None
            body = f"<p>Tag {e.tag} has been retired.</p>\n"
            if e.note:
                body += f"<p>{html.escape(e.note)}</p>\n"
            if target:
                body += (f'<p>It is replaced by <a href="{e.by}.html">Tag '
                         f'{e.by}</a>: {describe(target)}.</p>\n')
            extra = ""
            retired.append(e)
        else:
            page, anchor, *_ = info(e)
            if not page:
                print(f"make-tags: warning: no page for tag {e.tag}",
                      file=sys.stderr)
                continue
            url = "../" + page + ("#" + anchor if anchor else "")
            q = html.escape(url)
            extra = (f'<meta http-equiv="refresh" content="0; url={q}">\n'
                     f'<link rel="canonical" href="{q}">\n'
                     f'<script>location.replace({json.dumps(url)});</script>\n')
            body = (f'<p>Tag {e.tag} is {describe(e)}: '
                    f'<a href="{q}">go there</a>.</p>\n')
            rows.append(e)
        with open(path, "w", encoding="utf-8") as f:
            f.write(head.format(title=f"Tag {e.tag}", extra=extra,
                                css="../tex.css"))
            f.write(body + '<p><a href="../tags.html">All tags</a></p>\n'
                    "</body>\n</html>\n")

    def chap_key(c):
        return (0, int(c), "") if c.isdigit() else (1, 0, c)

    out = [head.format(title="Tags", extra="", css="tex.css"),
           '<div class="my-links-container"><a href="." class="my-link">home</a></div>\n'
           '<h1 class="title">Tags</h1>\n'
           "<p>Chapter, section and problem numbers change when chapters or "
           "problems are inserted.  Each chapter, section and numbered result "
           "of the settled parts also has a <em>tag</em>, four characters "
           "that never change and are never reused.  To cite an item "
           "permanently, cite its tag (\u201cTag 2224\u201d) or link to "
           '<a href="tag/2224.html"><code>tag/2224.html</code></a>, '
           "which leads to the item wherever it "
           "currently is.  On each page the tag is shown in grey beside the "
           "item.</p>\n"
           '<table class="tags">\n<thead><tr><th>Tag</th><th>Chapter</th>'
           "<th>Item</th><th>Title</th></tr></thead>\n<tbody>\n"]
    rows.sort(key=lambda e: (chap_key(info(e)[2]), 0 if not e.label else 1,
                             e.lineno))
    for e in rows:
        page, anchor, chap, kind, number, title = info(e)
        url = html.escape(page + ("#" + anchor if anchor else ""))
        item = "" if kind == "Chapter" else f"{kind} {number}"
        cls = ' class="chapter"' if kind == "Chapter" else ""
        out.append(f'<tr id="{e.tag}"{cls}><td><a href="tag/{e.tag}.html">'
                   f'{e.tag}</a></td><td>{chap}</td>'
                   f'<td><a href="{url}">{item or "Chapter " + chap}</a></td>'
                   f"<td>{title}</td></tr>\n")
    out.append("</tbody>\n</table>\n")
    if retired:
        out.append("<h2>Retired tags</h2>\n<ul>\n")
        for e in retired:
            rep = (f' Replaced by <a href="tag/{e.by}.html">{e.by}</a>.'
                   if e.by else "")
            note = f" {html.escape(e.note)}" if e.note else ""
            out.append(f'<li id="{e.tag}"><a href="tag/{e.tag}.html">{e.tag}'
                       f"</a>.{note}{rep}</li>\n")
        out.append("</ul>\n")
    out.append("</body>\n</html>\n")
    with open(os.path.join(directory, "tags.html"), "w", encoding="utf-8") as f:
        f.write("".join(out))
    print(f"make-tags: wrote tags.html and {len(entries)} pages in {tagdir}")


def main():
    args = sys.argv[1:]
    if "--site" in args:
        i = args.index("--site")
        if i + 1 >= len(args):
            die("--site needs a directory")
        site(args[i + 1])
        return
    entries, errors = read_tags()
    if "--check" in args:
        if "--since" in args:
            i = args.index("--since")
            if i + 1 >= len(args):
                die("--since needs a git revision")
            check_since(entries, errors, args[i + 1])
        check(entries, errors, "--strict" in args)
    else:
        assign(entries, errors)


if __name__ == "__main__":
    main()
