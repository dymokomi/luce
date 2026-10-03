"""The header box every generated source under src/ opens with, as a hand-written one does:
the module's name and what it is, then which tool wrote it from what, so the shape check
(luce-base tools/shape.py --root) holds generated files to the same rule."""

RULE = "#" + "=" * 94


def header(name, title, origin):
    """The header box for module `name`: `title` on its first line, `origin` (one or more
    lines) saying which tool generated it from what, and that edits go there."""
    lines = [RULE, "#", f"#   {name} - {title}", "#", "#   DESCRIPTION:"]
    lines += [f"#       {line}" for line in origin.split("\n")]
    lines += ["#", RULE, ""]
    return "\n".join(lines) + "\n"
