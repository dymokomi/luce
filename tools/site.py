#!/usr/bin/env python3
"""Build luce.luciaos.com from the repository: the Tour, the Guide and the Reference, as
static HTML in the site's own style.

    tools/site.py [OUT]          writes the site to OUT (default build/site)

Every page comes from a Markdown file of docs/: the Tour and the Guide from docs/guide/,
the Reference from docs/luce.md (one page per chapter) and docs/RUNTIME.md. The Markdown is the subset the docs use,
converted here so that the build needs nothing installed: headings, paragraphs, lists,
tables, block quotes, fenced code (highlighted, with a copy button; an `output` block shows
what the program before it prints), and inline code, emphasis and links. A link to another
document becomes a link to its page; `§N.M` in prose links to that section of the
Reference. The stylesheets and script are tools/site/, served as /assets/.
"""
import html
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build" / "site"
ASSETS = ROOT / "tools" / "site"
VERSION = (ROOT / "VERSION").read_text().strip()

# ---- pages ----------------------------------------------------------------------------------

class Page:
    """One page of the site: its section tab, its URL path, its title and its Markdown."""
    def __init__(self, tab, path, title, markdown, source):
        self.tab, self.path, self.title, self.markdown, self.source = tab, path, title, markdown, source


def slug(text):
    text = re.sub(r"<[^>]+>|`", "", text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


def first_heading(markdown):
    m = re.search(r"^# (.+)$", markdown, re.M)
    return m.group(1).strip() if m else ""


def chapter_files(directory):
    """The numbered chapters of a guide directory, in order, after its README."""
    return sorted(p for p in directory.glob("*.md") if p.name != "README.md")


def collect():
    pages = []
    guide = DOCS / "guide"
    pages.append(Page("home", "", "Luce", (guide / "README.md").read_text(), guide / "README.md"))
    tour = guide / "tour"
    pages.append(Page("tour", "tour/", "A Tour of Luce", (tour / "README.md").read_text(), tour / "README.md"))
    for p in chapter_files(tour):
        name = re.sub(r"^\d+-", "", p.stem)
        pages.append(Page("tour", f"tour/{name}/", first_heading(p.read_text()), p.read_text(), p))
    topics = guide / "topics"
    if (topics / "README.md").exists():
        pages.append(Page("guide", "guide/", "The Guide", (topics / "README.md").read_text(), topics / "README.md"))
        for p in chapter_files(topics):
            name = re.sub(r"^\d+-", "", p.stem)
            pages.append(Page("guide", f"guide/{name}/", first_heading(p.read_text()), p.read_text(), p))
    # the Reference, one page per numbered chapter of the specification
    spec = (DOCS / "luce.md").read_text()
    parts = re.split(r"^(?=## \d+\. )", spec, flags=re.M)
    intro = parts[0]
    pages.append(Page("reference", "reference/", "The Reference", reference_index(intro, parts[1:]), DOCS / "luce.md"))
    for part in parts[1:]:
        title = first_line(part)[3:].strip()
        number = title.split(".")[0]
        body = "# " + title + part[len(first_line(part)):]
        pages.append(Page("reference", f"reference/{reference_slug(title)}/", title, body.replace("\n### ", "\n## "), DOCS / "luce.md"))
    runtime = (DOCS / "RUNTIME.md").read_text()
    pages.append(Page("reference", "reference/runtime/", first_heading(runtime), runtime.replace("\n### ", "\n## "), DOCS / "RUNTIME.md"))
    return pages


def first_line(text):
    return text.split("\n", 1)[0]


def reference_slug(title):
    return slug(re.sub(r"^\d+\.\s*", "", title))


def reference_index(intro, chapters):
    lines = ["# The Reference", "",
             "The specification of Luce: every rule of the language and the reason for it. "
             "It is the document the compiler is held to; where the Tour and the Guide simplify, "
             "this is exact.", ""]
    for part in chapters:
        title = first_line(part)[3:].strip()
        lines.append(f"- [{title}]({reference_slug(title)}/)")
    lines += ["", "[The runtime](runtime/) states what the runtime promises: when objects are "
              "destroyed and in what order, how the cycle collector runs, how values are hashed."]
    return "\n".join(lines) + "\n"


# ---- links ----------------------------------------------------------------------------------

def link_table(pages):
    """Where each source document and each Reference section lives on the site."""
    by_source = {}
    for page in pages:
        by_source.setdefault(page.source.resolve(), page.path)
    sections = {}
    for page in pages:
        if page.tab != "reference" or not page.path.startswith("reference/") or page.path == "reference/":
            continue
        for m in re.finditer(r"^#{1,2} ((\d+)(?:\.(\d+))?\.? .*)$", page.markdown, re.M):
            key = m.group(2) + ("." + m.group(3) if m.group(3) else "")
            anchor = "" if not m.group(3) else "#" + slug(m.group(1))
            sections[key] = page.path + anchor
    return by_source, sections


def relative(page, site_path):
    """`site_path`, a path from the site's root, as a link from `page`: every link is
    relative, so the site works wherever it is served, a preview under /next/ included."""
    return ("../" * page.path.count("/") or "./") + site_path


def resolve(target, page, by_source):
    """A Markdown link target, relative to the page's source, as a site URL."""
    if re.match(r"^[a-z]+:", target) or target.startswith("#") or target.startswith("/"):
        return target
    path, _, anchor = target.partition("#")
    if not path:
        return "#" + anchor
    file = (page.source.parent / path).resolve()
    if file.is_dir():
        file = file / "README.md"
    if anchor and file.name == "luce.md":
        # a section of the specification: its chapter's page, `5-types` or `8-9-inline-assembly`
        m = re.match(r"(\d+)(?:-(\d+))?-", anchor)
        if m and (m.group(1) + ("." + m.group(2) if m.group(2) else "")) in SECTIONS:
            return relative(page, SECTIONS[m.group(1) + ("." + m.group(2) if m.group(2) else "")])
    url = by_source.get(file)
    if url is None:
        return "https://github.com/dymokomi/luce/blob/main/" + str(file.relative_to(ROOT)) + ("#" + anchor if anchor else "")
    return relative(page, url) + ("#" + anchor if anchor else "")


# ---- Markdown ---------------------------------------------------------------------------------

KEYWORDS = set("""and as break catch class continue elif else enum false for from func if import in
interface is let match none not or pub recover return self spawn struct test true try type var
wait while with handle destroy const""".split())
TYPES = set("""int float bool str bytes unit never list map set task range Error ErrorCode Weak Result
i8 i16 i32 i64 isize u8 u16 u32 u64 usize f32 f64""".split())
BUILTINS = set("assert discard error trap hash print".split())
TOKEN = re.compile(r'(?P<c>#.*$)|(?P<s>[fbr]?"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)+\')|(?P<n>\b(?:0x[0-9a-fA-F_]+|0b[01_]+|0o[0-7_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:e[+-]?\d+)?)(?:[iuf](?:8|16|32|64|size))?\b)|(?P<w>[A-Za-z_][A-Za-z0-9_]*)', re.M)


def highlight(code):
    out = []
    last = 0
    declaring = False
    for m in TOKEN.finditer(code):
        out.append(html.escape(code[last:m.start()]))
        text = html.escape(m.group(0))
        kind = m.lastgroup
        if kind == "w":
            word = m.group(0)
            if declaring:
                kind, declaring = "d", False
            elif word in KEYWORDS:
                kind = "k"
                declaring = word in ("func", "struct", "enum", "union", "interface", "type", "handle")
            elif word in TYPES or (word[0].isupper() and not word.isupper()):
                kind = "t"
            elif word in BUILTINS:
                kind = "b"
            else:
                kind = None
        out.append(f'<span class="{kind}">{text}</span>' if kind else text)
        last = m.end()
    out.append(html.escape(code[last:]))
    return "".join(out)


def inline(text, page, by_source, sections):
    """Inline Markdown: code spans, links, emphasis, and `§N.M` references. Code spans are
    set aside first, so emphasis and links may hold them."""
    spans = []

    def keep(m):
        spans.append("<code>" + html.escape(m.group(1)) + "</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(resolve(m.group(2), page, by_source))}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"§(\d+(?:\.\d+)?)", lambda m: f'<a href="{relative(page, sections[m.group(1)])}">§{m.group(1)}</a>' if m.group(1) in sections else m.group(0), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def cells(line):
    """A table row's cells; `\\|` is a `|` inside a cell."""
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [p.strip().replace("\\|", "|") for p in parts]


def render(page, by_source, sections):
    """The page's Markdown as HTML, and its second-level headings for the page outline."""
    lines = page.markdown.split("\n")
    out, outline = [], []
    i = 0
    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para), page, by_source, sections) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if re.match(r"^<!--.*-->\s*$", line):
            i += 1
            continue
        fence = re.match(r"^```(\w*)\s*$", line)
        if fence:
            flush()
            language = fence.group(1)
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code = "\n".join(lines[i + 1:j])
            i = j + 1
            if language == "output":
                out.append('<figure class="sample"><div class="cap out">output</div><div class="code result"><pre><samp>'
                           + html.escape(code) + "</samp></pre></div></figure>")
            elif language == "sh":
                out.append('<div class="code"><button class="copy" type="button">copy</button><pre><code class="language-sh">'
                           + html.escape(code) + "</code></pre></div>")
            else:
                body = highlight(code) if language in ("luce", "lucb") else html.escape(code)
                out.append(f'<div class="code"><button class="copy" type="button">copy</button><pre><code class="language-{language or "text"}">'
                           + body + "</code></pre></div>")
            continue
        heading = re.match(r"^(#{1,4}) (.+)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level == 1:
                out.append("<h1>" + inline(text, page, by_source, sections) + "</h1>")
            else:
                anchor = slug(text)
                if level == 2:
                    outline.append((anchor, re.sub(r"`", "", text)))
                out.append(f'<h{level} id="{anchor}">{inline(text, page, by_source, sections)}<a class="anchor" href="#{anchor}" aria-label="link to this section">#</a></h{level}>')
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|\s*$", lines[i + 1]):
            flush()
            head = cells(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            cell = lambda c: inline(c, page, by_source, sections)
            out.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{cell(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table></div>")
            continue
        item = re.match(r"^(\s*)([-*]|\d+\.) (.*)$", line)
        if item:
            flush()
            ordered = item.group(2)[0].isdigit()
            items = []
            while i < len(lines):
                m = re.match(r"^(\s*)([-*]|\d+\.) (.*)$", lines[i])
                if m and len(m.group(1)) == len(item.group(1)):
                    items.append([m.group(3)])
                    i += 1
                elif items and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^```", lines[i].strip()):
                    items[-1].append(lines[i].strip())
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join("<li>" + inline(" ".join(t), page, by_source, sections) + "</li>" for t in items) + f"</{tag}>")
            continue
        if line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(quote), page, by_source, sections) + "</p></blockquote>")
            continue
        if line.strip() == "":
            flush()
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out), outline


# ---- the shell ----------------------------------------------------------------------------------

TABS = [("home", "", "Start"), ("tour", "tour/", "Tour"), ("guide", "guide/", "Guide"),
        ("reference", "reference/", "Reference")]


def shell(page, body, outline, pages):
    depth = page.path.count("/")
    up = "../" * depth or "./"
    tabs = "".join(f'<a{" class=\"here\"" if tab == page.tab else ""} href="{up}{path}">{name}</a>' for tab, path, name in TABS
                   if tab != "guide" or any(p.tab == "guide" for p in pages))
    siblings = [p for p in pages if p.tab == page.tab]
    nav = ""
    if len(siblings) > 1:
        nav = ('<details class="nav" open><summary>Pages</summary><ul>'
               + "".join(f'<li><a{" class=\"here\"" if p is page else ""} href="{up}{p.path}">{html.escape(re.sub(r"`", "", p.title))}</a></li>' for p in siblings)
               + "</ul></details>")
    if outline:
        nav += ('<details class="nav" open><summary>On this page</summary><ul>'
                + "".join(f'<li class="h2"><a href="#{a}">{html.escape(t)}</a></li>' for a, t in outline) + "</ul></details>")
    title = "Luce" if page.path == "" else f"{re.sub(r'`', '', page.title)} · Luce"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{up}assets/core.css">
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="icon" href="{up}assets/mark.svg" type="image/svg+xml">
<script>try{{var t=localStorage.getItem("luce-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<header class="top">
<a class="mark" href="{up}">Luce</a>
<nav class="tabs">{tabs}</nav>
<div class="tools">
<a class="cross" href="https://luce-base.luciaos.com">Luce Base</a><a class="cross" href="https://github.com/dymokomi/luce">Source</a><a class="cross" href="https://luciaos.com">LuciaOS</a>
<button id="theme" type="button" aria-label="Switch between light and dark">◑</button>
</div>
</header>
<div class="shell">
<div class="side">{nav}</div>
<main id="content">
<article>
{body}
</article>
<footer class="foot"><p>Luce {VERSION}. This page is built from <a href="https://github.com/dymokomi/luce/blob/main/{page.source.relative_to(ROOT)}">{page.source.relative_to(ROOT)}</a>.</p></footer>
</main>
</div>
<script src="{up}assets/site.js" defer></script>
</body>
</html>
"""


# The Reference's sections by number, `5` and `5.4`: where each is on the site.
SECTIONS = {}


def main():
    pages = collect()
    by_source, sections = link_table(pages)
    SECTIONS.update(sections)
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for asset in ASSETS.iterdir():
        shutil.copy(asset, OUT / "assets" / asset.name)
    for page in pages:
        body, outline = render(page, by_source, sections)
        target = OUT / page.path / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell(page, body, outline, pages))
    broken = broken_links(OUT)
    for item in broken:
        print("broken link:", item, file=sys.stderr)
    if broken:
        sys.exit(1)
    print(f"wrote {len(pages)} pages to {OUT}")


def broken_links(out):
    """Every relative link of every page that leads to no page or file of the site, or to a
    section the page it names does not have."""
    broken = []
    ids = {}
    for page in out.rglob("*.html"):
        ids[page.resolve()] = set(re.findall(r'id="([^"]+)"', page.read_text()))
    for page in out.rglob("*.html"):
        for target in re.findall(r'(?:href|src)="([^"]+)', page.read_text()):
            if re.match(r"^[a-z]+:", target):
                continue
            path_part, _, anchor = target.partition("#")
            path = (page.parent / path_part).resolve() if path_part else page.resolve()
            if path.is_dir():
                path = path / "index.html"
            if not path.is_file():
                broken.append(f"{page.relative_to(out)}: {target}")
            elif anchor and path.suffix == ".html" and anchor not in ids.get(path, set()):
                broken.append(f"{page.relative_to(out)}: {target} (no such section)")
    return broken


if __name__ == "__main__":
    main()
