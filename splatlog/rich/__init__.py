"""
Helpers for working with [rich][]

[rich]: https://pypi.org/project/rich/
"""

from __future__ import annotations
from typing import Any


# Re-exports
from .theme import (
    ToTheme as ToTheme,
    THEME as THEME,
    ANSI_PALETTE_DARK as ANSI_PALETTE_DARK,
    to_theme as to_theme,
    get_default_theme as get_default_theme,
    set_default_theme as set_default_theme,
    override_ansi_colors as override_ansi_colors,
)
from .typings import Rich as Rich, is_rich as is_rich
from .enriched_type import EnrichedType as EnrichedType
from .ntv_table import NtvTable, TableSource
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

# .theme
ToTheme.__module__ = __name__
THEME.__module__ = __name__
to_theme.__module__ = __name__
get_default_theme.__module__ = __name__
set_default_theme.__module__ = __name__
override_ansi_colors.__module__ = __name__
NtvTable.__module__ = __name__
TableSource.__module__ = __name__


__all__ = [
    # .theme
    "ToTheme",
    "THEME",
    "ANSI_PALETTE_DARK",
    "to_theme",
    "get_default_theme",
    "set_default_theme",
    "override_ansi_colors",
    # .ntv_table
    "NtvTable",
    "TableSource",
    # .
    "capture_riches",
]


def capture_riches(
    *objects: Any, console: ToRichConsole | None = None, **print_kwds
) -> str:
    # Convert the arg to a `rich.console.Console` instance. In the default case
    # `None` this will construct a `Console` with the library defaults.
    console = to_console({} if console is None else console)

    with console.capture() as capture:
        console.print(*objects, **print_kwds)
    return capture.get()
