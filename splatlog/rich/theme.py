"""
Support for working with {py:class}`rich.theme.Theme`.
"""

from __future__ import annotations
from collections.abc import Mapping
from typing import IO, TypeAlias, cast

from rich.color import Color, ColorType
from rich.theme import Theme
from rich.style import Style, StyleType

from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies

# Typings
# ============================================================================

ToTheme: TypeAlias = Theme | IO[str] | Mapping[str, StyleType]
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
        "log.name.sep": Style(color="bright_black"),
        "log.class": Style(color="yellow", dim=True),
        "log.funcName": Style(color="cyan", dim=True),
        "log.label": Style(color="bright_black"),
        "log.data.name": Style(color="blue", italic=True),
        "log.data.type": Style(color="#4ec9b0", italic=True),
    }
)
"""
Base theme with `splatlog`-specific additions.
"""

ANSI_PALETTE_DARK: dict[str, str] = dict(
    black="#0e0f12",
    red="#e06c75",
    bright_green="#5cb85c",
    bright_yellow="#f0ad4e",
    bright_blue="#52acf7",
    bright_magenta="#b95bde",
    bright_cyan="#5bc0de",
    bright_white="#ffffff",
    green="#98c379",
    yellow="#e5c07b",
    blue="#61afef",
    magenta="#c678dd",
    cyan="#56b6c2",
    white="#dee1de",
    bright_black="#636a80",
    bright_red="#d9534f",
)
"""
A palette of colors for dark background, as map of color name {py:class}`str` to
hex value {py:class}`str`.

Useful if you need to {py:func}`override_ansi_colors`, such as Jupyter notebooks
in VSCode-based IDEs.
"""

# Globals
# ============================================================================

_default_theme: Theme = THEME


def get_default_theme() -> Theme:
    return _default_theme


def set_default_theme(theme: ToTheme) -> None:
    global _default_theme
    _default_theme = to_theme(theme)


# Conversion
# ============================================================================


def to_theme(value: ToTheme | None = None) -> Theme:
    """Convert a `value` into a {py:class}`rich.theme.Theme`.

    ##
    -   {py:class}`rich.console.Console`: already cast, may be used as-is.

    -   {py:type}`splatlog.typings.StdioName`: write to the named standard output
        stream.

    -   {py:class}`typing.IO`: write to the given string I/O stream.

    -   {py:data}`None`: construct with library defaults.
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
            fmt(ToTheme), fmt(type(value)), fmt(value)
        )
    )


# Customization
# ============================================================================


def override_ansi_colors(
    theme: Theme = THEME, **name_color_map: str | Color
) -> Theme:
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
