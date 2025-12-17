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
from .theme import (
    ToRichTheme as ToRichTheme,
    THEME as THEME,
    to_theme as to_theme,
    get_default_theme as get_default_theme,
    set_default_theme as set_default_theme,
)
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
from .console import (
    StdioName as StdioName,
    ToRichConsole as ToRichConsole,
    is_stdio_name as is_stdio_name,
    is_to_rich_console as is_to_rich_console,
    to_console as to_console,
)


def capture_riches(
    *objects: Any, console: ToRichConsole | None = None, **print_kwds
) -> str:
    # Convert the arg to a `rich.console.Console` instance. In the default case
    # `None` this will construct a `Console` with the library defaults.
    console = to_console({} if console is None else console)

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

    # For each override, make sure there is a style with that name. The `rich`
    # base styles only include _some_ of the ANSI colors, but if you override
    # `blue` you want to make sure that's used for `[blue]` and not the terminal
    # color
    for name, color in name_color_map.items():
        if name not in styles:
            styles[name] = Style(color=color)

    return Theme(styles)
