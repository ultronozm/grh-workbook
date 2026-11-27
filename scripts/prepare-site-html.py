#!/usr/bin/env python3
"""Publish sheet context and set the browser policy on deploy HTML."""
import argparse
import base64
import hashlib
from html import escape, unescape
import json
from pathlib import Path
import re
import posixpath
from urllib.parse import urlsplit


CDN = "https://cdn.jsdelivr.net"
MATHJAX = CDN + "/npm/mathjax@3.2.2/es5/tex-chtml-full.js"
INTEGRITY = "sha384-NR8saakDju74wZ6sprPPhEoWbaP3iVtXVJH12mRSiaIgxMdi33mOQj8bnF2WxzY3"
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.I | re.S)
POLICY = re.compile(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n', re.I)
ALTERNATE = re.compile(r'<link rel="alternate" type="text/plain"[^>]*>\n')
PROBLEM = re.compile(r"\\begin\{problem\}.*?\\end\{problem\}", re.S)


def publish_context(page, html):
    ids = {
        unescape(label): json.loads(unescape(encoded))[0]
        for label, encoded in re.findall(
            r'<div id="([^"]+)" class="problem" data-progress-ids="([^"]+)"', html)
    }
    tex = page.with_suffix(".tex").read_text(encoding="utf-8")
    tex = re.sub(r"(?m)(?<!\\)((?:\\\\)*)%[^\n]*(?:\n|$)", r"\1\n", tex)
    preamble, body = tex.split(r"\begin{document}", 1)
    body = body.rsplit(r"\end{document}", 1)[0]
    body = re.sub(r"\\maketitle|\\refstepcounter\{chap\}\\label\{chap\}", "", body)
    # Keep the title and notation definitions. Package and page setup is irrelevant.
    header = re.findall(r"(?m)^\\(?:title\{|(?:re|new|provide)command\b|DeclareMathOperator\b).*$", preamble)
    seen = set()

    def mark(match):
        statement = match[0]
        label = re.search(r"\\label\{([^}]+)\}", statement)
        if label and label[1] in ids:
            seen.add(label[1])
            newline = "" if match.string.startswith("\n", match.end()) else "\n"
            return f"{statement}\n% End problem: {ids[label[1]]}{newline}"
        return statement

    body = PROBLEM.sub(mark, body)
    if seen != ids.keys():
        raise ValueError(f"{page}: missing source problems {sorted(ids.keys() - seen)}")
    target = page.with_suffix(".txt")
    target.write_text("\n".join(header) + "\n\n" + body.strip() + "\n", encoding="utf-8")
    alternate = f'<link rel="alternate" type="text/plain" href="{escape(target.name)}">\n'
    return ALTERNATE.sub("", html).replace("</head>", alternate + "</head>", 1)


def secure(html, endpoint, page):
    hashes = set()
    mathjax = False
    comments = False

    def script(match):
        nonlocal mathjax, comments
        attrs, body = match.groups()
        src = re.search(r'\bsrc\s*=\s*["\']([^"\']+)', attrs, re.I)
        if src:
            url = src[1]
            if url == "https://giscus.app/client.js":
                path = posixpath.relpath("comments.js", page.parent.as_posix())
                attrs = attrs.replace(url, path)
                comments = True
                return f"<script{attrs}></script>"
            if url.split("/")[-1] == "comments.js":
                comments = True
            if url.startswith(CDN + "/npm/mathjax@"):
                if mathjax:
                    return ""
                mathjax = True
                loading = " async" if re.search(r"\sasync\b", attrs) else (
                    " defer" if re.search(r"\sdefer\b", attrs) else "")
                return (f'<script{loading} src="{MATHJAX}" integrity="{INTEGRITY}"'
                        ' crossorigin="anonymous"></script>')
        elif body.lstrip().startswith("window.MathJax =") and mathjax:
            # Org can add its own configuration after the guide's MathJax setup.
            return ""
        elif body:
            # The HTML parser strips the CDATA delimiters in inline SVG.
            if body.startswith("//<![CDATA[") and body.endswith("//]]>"):
                body = "//" + body[len("//<![CDATA["):-len("]]>")]
            digest = hashlib.sha256(body.encode("utf-8")).digest()
            hashes.add("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
        return match[0]

    html = SCRIPT.sub(script, POLICY.sub("", html))
    scripts = " ".join(["'self'", CDN, *sorted(hashes)])
    connect = " ".join(filter(None, ["'self'", "https://api.anthropic.com", "https://api.openai.com", endpoint]))
    policy = (f"default-src 'none'; script-src {scripts}; connect-src {connect}; "
              f"style-src 'self' 'unsafe-inline'; font-src 'self' {CDN}; "
              "img-src 'self' data:; base-uri 'none'; form-action 'none'; object-src 'none'")
    if comments:
        policy += "; frame-src https://giscus.app"
    meta = f'<meta http-equiv="Content-Security-Policy" content="{policy}">\n'
    return re.sub(r"(<head\b[^>]*>)[ \t]*\n?", lambda head: head[1] + "\n" + meta,
                  html, count=1, flags=re.I)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages", nargs="*", type=Path)
    args = parser.parse_args()
    endpoint = re.search(r'const SYNC_ENDPOINT = "([^"]*)";',
                         Path("progress.js").read_text(encoding="utf-8"))[1]
    if endpoint:
        url = urlsplit(endpoint)
        endpoint = f"{url.scheme}://{url.netloc}"
    for page in args.pages or sorted(Path(".").rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        if page.parent == Path(".") and page.name.endswith("__workbook.html") and (
                'name="workbook-chapter"' in html and page.with_suffix(".tex").is_file()):
            html = publish_context(page, html)
        output = secure(html, endpoint, page)
        if output != page.read_text(encoding="utf-8"):
            page.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
