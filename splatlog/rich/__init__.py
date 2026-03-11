"""
Helpers for working with the {py:mod}`rich` terminal formatting package.

{py:mod}`rich` is what we use to produce colorful, tabular log messages in the
terminal.
"""

from __future__ import annotations
from typing import Any

from splatlog.types import ToRichConsole


# Re-exports
from .theme import (
    ToTheme as ToTheme,
    THEME as THEME,
    PALETTE_ANSI_DARK,
    THEME_ANSI_DARK,
    to_theme as to_theme,
    get_default_theme as get_default_theme,
    set_default_theme as set_default_theme,
    override_ansi_colors as override_ansi_colors,
)
from .ntv_table import NtvTable, TableSource
from .enrich import (
    REPR_HIGHLIGHTER as REPR_HIGHLIGHTER,
    enrich as enrich,
    enrich_type as enrich_type,
    enrich_type_of as enrich_type_of,
    EnrichedType as EnrichedType,
)
from .inline import Inline as Inline
from .console import to_console as to_console
from .handler import RichHandler as RichHandler

__all__ = [
    # .theme
    "ToTheme",
    "THEME",
    "PALETTE_ANSI_DARK",
    "THEME_ANSI_DARK",
    "to_theme",
    "get_default_theme",
    "set_default_theme",
    "override_ansi_colors",
    # .enriched_type
    "EnrichedType",
    # .ntv_table
    "NtvTable",
    "TableSource",
    # .enrich
    "REPR_HIGHLIGHTER",
    "enrich",
    "enrich_type",
    "enrich_type_of",
    # .inline
    "Inline",
    # .console
    "to_console",
    # .handler
    "RichHandler",
    # local
    "capture_riches",
]


def capture_riches(
    *objects: Any, console: ToRichConsole | None = None, **print_kwds
) -> str:
    """
    Capture Rich output as a string.

    Prints the given objects using a Rich console and returns the captured
    output as a string.

    ## Parameters

    -   `*objects`: Objects to print.
    -   `console`: {py:class}`rich.console.Console` specification (see
        {py:func}`to_console`).
    -   `**print_kwds`: Additional keyword arguments for
        {py:meth}`rich.console.Console.print`.

    ## Returns

    The captured console output as a string.

    ## Examples

    ```python
    >>> print(capture_riches("Hello", "World"))
    Hello World
    <BLANKLINE>

    ```
    """
    # Convert the arg to a `rich.console.Console` instance. In the default case
    # `None` this will construct a `Console` with the library defaults.
    console = to_console(console)

    with console.capture() as capture:
        console.print(*objects, **print_kwds)
    return capture.get()
