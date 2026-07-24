Rich Rendering
==============================================================================

The docs can *execute* [Rich][] snippets at build time and embed the resulting
console output as inline SVG. This is provided by the local `rich` directive
(see `docs/_ext/rich_block.py`).

[Rich]: https://rich.readthedocs.io/en/stable/index.html

Console Markup
------------------------------------------------------------------------------

[Console markup][] uses BBCode-like tags to style text — for example
`[yellow]Hey, I'm yellow![/]`{l=python}.

[Console markup]: https://rich.readthedocs.io/en/stable/markup.html

:::{rich}
from rich import print

print("[yellow]Hey, I'm yellow![/]")
print("[bold red]alert![/bold red] Something happened")
print("[bold italic yellow on red]This is hard to read[/]")
:::

Enriching Values
------------------------------------------------------------------------------

`splatlog.rich.enrich` turns Python values into Rich renderables. Here it styles
a number and an `splatlog.rich.EnrichedId`:

:::{rich}
from rich.console import Console
from splatlog.rich import enrich, EnrichedId

console = Console()

# Numbers enrich to inline, styled text:
console.print("An enriched int: ", enrich(12345))
console.print("Custom grouping: ", enrich(1234567, i_fmt="{:_}"))

# An EnrichedId renders as a styled block:
console.print(EnrichedId(12345))
:::

Tables & Other Renderables
------------------------------------------------------------------------------

Any Rich renderable works, not just `print`:

:::{rich}
:width: 60

from rich import print
from rich.table import Table

table = Table(title="Log Levels")
table.add_column("Name", style="cyan")
table.add_column("Value", style="magenta", justify="right")
for name, value in [("DEBUG", 10), ("INFO", 20), ("WARNING", 30)]:
    table.add_row(name, str(value))

print(table)
:::

Hiding the Source
------------------------------------------------------------------------------

Pass `:no-source:` to show only the rendered output:

:::{rich}
:no-source:
:title: splatlog

from rich import print
print(":sparkles: [bold green]All set![/] :sparkles:")
:::
