"""
Text utilities.

:::{warning}
### No cross-package `import` at top-level

This module is considered _foundational_ due to its primary use in formatting
error messages. To avoid circular imports it is prohibited from importing other
{py:mod}`splatlog` modules at the top-level.

Imports of other {py:mod}`splatlog` modules should be avoided, and placed inside
function or method bodies if they can't be.

:::
"""

from __future__ import annotations
from collections import abc
from typing import Any

from rich.console import Console
from rich.padding import Padding, PaddingDimensions
from rich.table import Table

# NOTE  These need to be imported from the modules they're defined in, doc gen
#       doesn't work if imported from `.formatting`
from .formatting.decorator import formatter, Formatter, FmtResult
from .formatting.opts import (
    FmtOpts,
    FmtFallback,
    FmtKwds,
    FmtTdBase,
    fmt_pretty_repr,
)
from .formatting.formatters import (
    fmt,
    fmt_name,
    fmt_type,
    fmt_type_of,
    fmt_type_value,
    fmt_type_hint,
    fmt_routine,
    fmt_range,
    fmt_list,
    fmt_datetime,
    fmt_date,
    fmt_time,
    fmt_timedelta,
)


__all__ = [
    # .formatting.decorator
    "formatter",
    "Formatter",
    # .formatting.opts
    "fmt_pretty_repr",
    "FmtOpts",
    "FmtResult",
    "FmtFallback",
    "FmtKwds",
    "FmtTdBase",
    # .formatting.formatters
    "fmt",
    "fmt_name",
    "fmt_type",
    "fmt_type_of",
    "fmt_type_value",
    "fmt_type_hint",
    "fmt_routine",
    "fmt_range",
    "fmt_list",
    "fmt_datetime",
    "fmt_datetime",
    "fmt_date",
    "fmt_time",
    "fmt_timedelta",
]


# WARNING   No cross-package `import` at top-level.
#
#           Don't import other `splatlog` modules here, see module doc at top.


def str_find_all(s: str, char: str) -> abc.Iterable[int]:
    """
    Find all occurrences of a character in a string.

    ## Parameters

    -   `s`: The string to search.
    -   `char`: The character to find.

    ## Returns

    An iterable of indices where `char` occurs in `s`.
    """
    i = s.find(char)
    while i != -1:
        yield i
        i = s.find(char, i + 1)


def tabulate(
    rows: list[list[Any]],
    pad: PaddingDimensions = 0,
    space: PaddingDimensions = (0, 2),
    width: int | None = None,
) -> str:
    """
    Render a list of lists as a table, horizontally aligning each column with
    spaces.

    ## Parameters

    -   `rows`: The list of lists to render.
    -   `pad`: Table padding (outside).
    -   `space`: Cell padding (inside).

    ## Returns

    String rendering of the table.
    """
    if not rows:
        return ""

    max_cols = max(len(row) for row in rows)

    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        collapse_padding=True,
        padding=space,
    )

    # Add columns
    for _ in range(max_cols):
        table.add_column()

    # Add rows
    for row in rows:
        # Normalize all rows to the max cols, padding with `""` cells
        if fill_cols := max_cols - len(row):
            row = row + [""] * fill_cols
        table.add_row(*row)

    if pad:
        table = Padding(table, pad)

    console = Console(
        width=width,
        color_system=None,
        force_terminal=False,
    )

    with console.capture() as capture:
        console.print(table)

    return capture.get()
