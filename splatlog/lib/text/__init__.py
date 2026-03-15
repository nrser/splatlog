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

# NOTE  These need to be imported from the modules they're defined in, doc gen
#       doesn't work if imported from `.formatting`
from .formatting.decorator import formatter, Formatter, FmtResult
from .formatting.opts import FmtOpts
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
    fmt_seq,
    fmt_datetime,
    fmt_date,
    fmt_time,
    fmt_timedelta,
)


__all__ = [
    "formatter",
    "Formatter",
    "FmtOpts",
    "FmtResult",
    "fmt",
    "fmt_name",
    "fmt_type",
    "fmt_type_of",
    "fmt_type_value",
    "fmt_type_hint",
    "fmt_routine",
    "fmt_range",
    "fmt_list",
    "fmt_seq",
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
