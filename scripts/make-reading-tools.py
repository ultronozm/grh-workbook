#!/usr/bin/env python3
"""Build backlinks and search data from the converted workbook sheets."""
from collections import defaultdict
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


HEADINGS = {f"h{level}" for level in range(1, 7)}
KINDS = "definition theorem proposition lemma problem remark".split()
LABEL = re.compile(r"^(" + "|".join(KINDS) + r")\s+S?\d+(?:\.\d+)*\b", re.I)
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
BACKLINKS = re.compile(r"<!-- used-in:start -->.*?<!-- used-in:end -->\n", re.S)


@dataclass
class Element:
    tag: str
    ident: str
    kind: str = ""
    text: list = field(default_factory=list)
    end: int = 0

    @property
    def label(self):
        match = LABEL.match(self.plain)
        return match[0] if match else ""

    @property
    def plain(self):
        return " ".join("".join(self.text).split())


class Sheet(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.html = BACKLINKS.sub("", path.read_text(encoding="utf-8"))
        self.lines = [0, *(m.end() for m in re.finditer("\n", self.html))]
        self.chapter = ""
        self.stack = []
        self.blocks = {}
        self.titles = []
        self.links = []
        self.feed(self.html)
        self.close()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "workbook-chapter":
            self.chapter = attrs["content"]
        if tag == "a" and attrs.get("href"):
            source = next((e for e in reversed(self.stack) if e.kind in KINDS), None)
            self.links.append((source, attrs["href"]))
        if tag in {"p", "li", "br"}:
            self.handle_data(" ")
        if tag in VOID:
            return
        ident = attrs.get("id", "")
        classes = attrs.get("class", "").split()
        kind = ""
        if tag == "div" and ident:
            kind = next((k for k in KINDS if k in classes), "")
        if tag == "h1" and "title" in classes:
            kind = "title"
        elif tag in HEADINGS and ident:
            kind = "section"
        if tag in {"script", "style"} or "stable-tag" in classes:
            kind = "skip"
        self.stack.append(Element(tag, ident, kind))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            element = self.stack[i]
            if element.tag == tag:
                del self.stack[i:]
                if element.kind in {"title", "section"}:
                    self.titles.append(element)
                if element.kind in KINDS and element.label:
                    line, column = self.getpos()
                    element.end = self.lines[line - 1] + column
                    self.blocks[element.ident] = element
                break
        if tag in {"p", "li"}:
            self.handle_data(" ")

    def handle_data(self, data):
        if any(e.kind == "skip" for e in self.stack):
            return
        for element in self.stack:
            if element.kind in KINDS or element.kind in {"title", "section"}:
                element.text.append(data)


def chapter_order(number):
    return (not number.isdecimal(), int(number.lstrip("S")) if re.fullmatch(r"S?\d+", number) else 0)


def backlink_html(uses, chapter):
    def links(items):
        groups = defaultdict(list)
        for number, url, label in items:
            groups[number].append((url, label))
        def anchor(url, label):
            return f'<a href="{escape(url)}">{escape(label)}</a>'

        rendered = []
        for number, group in groups.items():
            if number == chapter:
                rendered.append(", ".join(anchor(url, label) for url, label in group))
                continue
            sheet_link = next((anchor(url, label) for url, label in group if "#" not in url), None)
            chapter_label = sheet_link or f"Chapter {number}"
            blocks = ", ".join(anchor(url, label) for url, label in group if "#" in url)
            rendered.append(f"{chapter_label}: {blocks}" if blocks else chapter_label)
        return "; ".join(rendered)

    visible = links(uses[:6])
    if len(uses) > 6:
        visible += (f' <details><summary>and {len(uses) - 6} more</summary>'
                    f'<div>{links(uses[6:])}</div></details>')
    return f'<!-- used-in:start --><div class="used-in">Used in: {visible}</div><!-- used-in:end -->\n'


def build_backlinks(sheets):
    incoming = defaultdict(dict)
    for name, sheet in sheets.items():
        for source, href in sheet.links:
            url = urlsplit(href)
            if url.scheme or url.netloc or url.query or not url.fragment:
                continue
            target = (unquote(url.path).removeprefix("./") or name, unquote(url.fragment))
            if target[0] not in sheets or target[1] not in sheets[target[0]].blocks:
                continue
            if source and source.ident in sheet.blocks:
                if target == (name, source.ident):
                    continue
                link = (name if name != target[0] else "") + "#" + source.ident
                label = source.label
            elif name != target[0]:
                link, label = name, f"Chapter {sheet.chapter}"
            else:
                continue
            incoming[target][link] = (sheet.chapter, link, label)

    for name, sheet in sheets.items():
        output = sheet.html
        for block in sorted(sheet.blocks.values(), key=lambda block: block.end, reverse=True):
            uses = incoming[name, block.ident].values()
            if uses:
                uses = sorted(uses, key=lambda use: (use[0] != sheet.chapter, chapter_order(use[0])))
                output = output[:block.end] + backlink_html(uses, sheet.chapter) + output[block.end:]
        if output != sheet.path.read_text(encoding="utf-8"):
            sheet.path.write_text(output, encoding="utf-8")


def build_search(sheets):
    rows = []
    for name, sheet in sheets.items():
        for element in sheet.titles + list(sheet.blocks.values()):
            if element.kind not in {"title", "section", "definition", "theorem", "problem"}:
                continue
            url = name + ("#" + element.ident if element.ident else "")
            label = element.label or element.plain
            body = element.plain[len(label):].lstrip(". ")
            rows.append([sheet.chapter, url, label, body])
    Path("workbook-search.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main():
    sheets = sorted((Sheet(path) for path in Path(".").glob("*__workbook.html")),
                    key=lambda sheet: (chapter_order(sheet.chapter), sheet.path.name))
    chapters = {sheet.path.name: sheet for sheet in sheets if sheet.chapter}
    build_backlinks(chapters)
    build_search(chapters)


if __name__ == "__main__":
    main()
