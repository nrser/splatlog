"""
Helpers for working with [rich][]

[rich]: https://pypi.org/project/rich/
"""

from __future__ import annotations
from typing import Any

from rich.theme import Theme
from rich.color import Color, ColorType
from rich.style import Style

# Re-exports
from .theme import THEME as THEME
from .typings import Rich as Rich, is_rich as is_rich
from .enriched_type import EnrichedType as EnrichedType
from .ntv_table import ntv_table as ntv_table
from .enrich import (
    REPR_HIGHLIGHTER as REPR_HIGHLIGHTER,
    enrich as enrich,
    enrich_type as enrich_type,
    enrich_type_of as enrich_type_of,
)
from .inline import Inline as Inline
from .formatter import (
    RichFormatter as RichFormatter,
    RichFormatterConverter as RichFormatterConverter,
    RichFormatterConversions as RichFormatterConversions,
    RichRepr as RichRepr,
    implements_rich_repr as implements_rich_repr,
    RichText as RichText,
    implements_rich_text as implements_rich_text,
)
from .console import (
    StdoutName as StdoutName,
    ToRichConsole as ToRichConsole,
    is_stdout_name as is_stdout_name,
    is_to_rich_console as is_to_rich_console,
    to_console as to_console,
)


def capture_riches(
    *objects: Any, console: ToRichConsole = None, **print_kwds
) -> str:
    # Convert the arg to a `rich.console.Console` instance. In the default case
    # `None` this will construct a `Console` with the library defaults.
    console = to_console(console)

    with console.capture() as capture:
        console.print(*objects, **print_kwds)
    return capture.get()


def override_ansi_colors(theme=THEME, **name_color_map: str | Color) -> Theme:
    """Copy `theme`, overriding styles using ANSI colors named in
    `name_color_map` with their corresponding values.

    Used to fix display of ANSI named colors in situations where it's difficult
    to adjust the "terminal" color values (Jupyter notebooks in VSCode
    extension) but True Color (24-bit color) rendering is available.

    ## Parameters

    -   `theme`: theme to apply overrides to, defaults to the splatlog theme.
    -   `name_color_map`: mapping of ANSI color names (`"blue"`, `"red"`, etc.)
        to replacement. The replacement is used as the `color` argument to
        {py:class}`rich.style.Style`. Typically a hex string like `"#439af4"`.

    ## Example

    ```python
    from rich.console import Console

    console = Console(
        theme=override_ansi_colors(blue="#509dea", bright_blue="#439af4")
    )
    ```
    """

    styles: dict[str, Style] = {}
    for name, style in theme.styles.items():
        if (
            isinstance(style, Style)
            and style.color
            and style.color.type is ColorType.STANDARD
            and style.color.name in name_color_map
        ):
            styles[name] = Style.chain(
                style, Style(color=name_color_map[style.color.name])
            )
        else:
            styles[name] = style

    return Theme(styles)
