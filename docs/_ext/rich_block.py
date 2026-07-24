"""
Local Sphinx extension providing a `rich` directive that *executes* a block of
Python and embeds the resulting `Rich <https://rich.readthedocs.io/>`_ console
output as an inline SVG.

Usage (MyST `colon_fence`)::

    :::{rich}
    from rich import print
    from splatlog.rich import enrich, EnrichedId

    print("This is an", enrich(int), "number:", enrich(12345))
    :::

The code is run at build time against a recording
{py:class}`rich.console.Console`; both the built-in `print` and
`from rich import print` are routed to it (the latter via the module-level
console that {py:func}`rich.get_console` returns). The recorded output is
exported with {py:meth}`rich.console.Console.export_svg` — self-contained
(colors, font reference, and terminal chrome all baked in) and responsive, since
the `<svg>` carries a `viewBox` but no fixed `width`/`height`.

Options:

`:width:` (int, default 80)
    Console width in characters. Governs where output wraps and the SVG's
    intrinsic aspect ratio.
`:title:` (text, default empty)
    Title shown in the terminal window's title bar.
`:no-source:` (flag)
    Hide the source-code block; show only the rendered output.
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)


class RichBlock(SphinxDirective):
    """Execute a Python snippet and embed its Rich output as SVG."""

    has_content = True
    option_spec = {
        "width": directives.positive_int,
        "title": directives.unchanged,
        "no-source": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        code = "\n".join(self.content)
        children: list[nodes.Node] = []

        if "no-source" not in self.options:
            source = nodes.literal_block(code, code)
            source["language"] = "python"
            children.append(source)

        try:
            svg = self._render(code)
        except Exception as error:  # noqa: BLE001 — surface *any* failure
            logger.warning(
                "rich block failed to execute: %s",
                error,
                location=(self.env.docname, self.lineno),
                type="rich_block",
            )
            children.append(
                nodes.error(
                    "", nodes.paragraph("", f"rich block error: {error}")
                )
            )
            return children

        container = nodes.container(classes=["rich-block"])
        container += nodes.raw("", svg, format="html")
        children.append(container)
        return children

    def _render(self, code: str) -> str:
        import rich
        from splatlog.rich import to_console

        console = to_console(
            record=True,
            width=self.options.get("width", 80),
            force_terminal=True,
            color_system="truecolor",
        )

        # Route both `print(...)` and `from rich import print` to `console`.
        # `rich.print` resolves the console lazily via `rich.get_console()`,
        # which returns the module-global `rich._console`; swap it for ours for
        # the duration of the exec, then restore.
        prev_console = rich._console
        rich._console = console
        try:
            exec(code, {"print": console.print, "__name__": "__rich_block__"})
        finally:
            rich._console = prev_console

        return console.export_svg(title=self.options.get("title", ""))


def setup(app: Sphinx) -> dict[str, t.Any]:
    app.add_directive("rich", RichBlock)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
