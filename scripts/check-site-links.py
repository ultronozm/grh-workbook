#!/usr/bin/env python3
"""Check local HTML links and anchors in a built site (default: _site)."""
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.anchors = set()
        self.links = []
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if not value:
                continue
            if key == "id" or (tag == "a" and key == "name"):
                self.anchors.add(value)
            if key in {"href", "src", "xlink:href"}:
                self.links.append((self.getpos()[0], value))


def main(root):
    root = root.resolve()
    pages = {path: Page(path) for path in sorted(root.rglob("*.html"))}
    if not pages:
        sys.exit(f"check-site-links: no HTML pages in {root}")
    errors = 0
    for source, page in pages.items():
        for line, link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            path = unquote(url.path)
            target = ((root / path.lstrip("/")) if path.startswith("/") else
                      (source.parent / path) if path else source).resolve()
            if target.is_dir():
                target /= "index.html"
            fragment = unquote(url.fragment)
            if not target.is_relative_to(root) or not target.is_file():
                problem = "missing file"
            elif fragment and target in pages and fragment not in pages[target].anchors:
                problem = "missing anchor"
            else:
                continue
            print(f"{source.relative_to(root)}:{line}: {problem}: {link}")
            errors += 1
    print(f"check-site-links: {len(pages)} pages, {errors} broken links")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "_site")))
