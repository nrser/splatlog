"""
Support for working with {py:class}`rich.theme.Theme`.
"""

from __future__ import annotations
from typing import IO, TypeAlias, cast

from rich.theme import Theme
from rich.style import Style, StyleType

from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies

# Typings
# ============================================================================

ToRichTheme: TypeAlias = Theme | IO[str] | dict[str, StyleType] | None
"""
What we can convert to a {py:class}`rich.theme.Theme`. See
{py:func}`splatlog.rich.theme.to_theme` for details.
"""

# Constants
# ============================================================================

THEME = Theme(
    {
        "log.level": Style(bold=True),
        "log.name": Style(color="blue", dim=True),
        "log.name.sep": Style(color="white", dim=True),
        "log.class": Style(color="yellow", dim=True),
        "log.funcName": Style(color="cyan", dim=True),
        "log.label": Style(color="white", dim=True),
        "log.data.name": Style(color="blue", italic=True),
        "log.data.type": Style(color="#4ec9b0", italic=True),
    }
)
"""
Base theme with `splatlog`-specific additions.
"""

# Globals
# ============================================================================

_default_theme: Theme = THEME


def get_default_theme() -> Theme:
    return _default_theme


def set_default_theme(theme: ToRichTheme) -> None:
    global _default_theme
    _default_theme = to_theme(theme)


# Conversion
# ============================================================================


def to_theme(value: ToRichTheme) -> Theme:
    """Convert a `value` into a {py:class}`rich.theme.Theme`.

    ##
    -   {py:class}`rich.console.Console`: already cast, may be used as-is.

    -   {py:type}`splatlog.typings.StdoutName`: write to the named standard output
        stream.

    -   {py:class}`typing.IO`: write to the given string I/O stream.

    -   {py:data}`None`: cast with library defaults.
    """
    if value is None:
        # Convert `None` to a copy of the default theme
        return Theme(_default_theme.styles)

    if isinstance(value, Theme):
        # Given a `rich.theme.Theme`, which can be used directly
        return value

    if satisfies(value, IO[str]):
        # Given an open file to read the theme from
        return Theme.from_file(value)

    if isinstance(value, dict):
        # Given a `dict` layer it over the default `THEME` so it has our
        # custom styles (if you don't want this pass a `Theme` instance)
        styles = cast(dict[str, StyleType], THEME.styles.copy())
        styles.update(value)
        return Theme(styles, inherit=False)

    raise TypeError(
        "Expected `theme` to be {}, given {}: {}".format(
            fmt(ToRichTheme), fmt(type(value)), fmt(value)
        )
    )
