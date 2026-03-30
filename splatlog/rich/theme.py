"""
Support for working with {py:class}`rich.theme.Theme`.
"""

from __future__ import annotations
from collections.abc import Mapping
from typing import IO, cast

from rich.color import Color, ColorType
from rich.theme import Theme
from rich.style import Style, StyleType

from splatlog.lib.typeguard import satisfies
from splatlog.types import ToTheme, assert_never

# Constants
# ============================================================================
THEME = Theme({
    #
    # `log` — Used to print log records
    # ====================================================================
    #
    # Style for logging levels ("DEBUG", "INFO", etc.). Each built-in level has
    # their own style with distinct color, but `log.level` is applied to all of
    # them.
    "log.level": Style(bold=True),
    "log.name": Style(color="blue", dim=True),
    "log.name.sep": Style(color="bright_black"),
    "log.class": Style(color="yellow", dim=True),
    "log.funcName": Style(color="cyan", dim=True),
    "log.label": Style(color="bright_black"),
    "log.data.name": Style(color="blue", italic=True),
    "log.data.type": Style(color="#4ec9b0", italic=True),
    #
    # `report` — Used to print logging state reports
    # ====================================================================
    #
    "report.logger.name": Style(color="blue", bold=True),
    "report.logger.name.sep": Style(color="bright_black"),
    # Style used to fade parent name segments of logger names; added to
    # `report.logger.name`
    "report.logger.name.parent": Style(dim=True, bold=False),
    "report.handler": Style(color="green", bold=True, reverse=True),
    "report.filter": Style(color="red", bold=True, reverse=True),
})
"""
Base theme with `splatlog`-specific additions in the `log` (extended) and
`report` (created) prefix namespaces.

The styles layer on top of the undocumented
{py:data}`rich.default_styles.DEFAULT_STYLES` (see
[source](https://github.com/Textualize/rich/blob/master/rich/default_styles.py)),
which consists of:

Basic Styles
----------------------------------------------------------------------------

-   `none`: {py:obj}`rich.style.Style.null`, a specialized empty style
    (`Style()`-equivalent) that triggers fast paths.

-   `reset`: All attributes `"default"` or {py:data}`False`.

-   Attribute manifestations:

    `dim`, `bright`, `bold`, `strong`, `italic`, `emphasize`, `underline`,
    `blink`, `blink2`, `reverse`, `strike`

    all of which should be pretty strait-forward, with the exception of
    `reverse`.

    From what I can tell, `reverse` is a relative transformation that inverts
    the current style — applying to white text on black background will produce
    black text on white background.

-   Colors: The ANSI colors

    `black`, `red`, `green`, `yellow`, `magenta`, `cyan`, `white`

    and only those colors, for whatever reason.

-   ```python
    "code": Style(reverse=True, bold=True)
    ```

`inspect` Namespace
----------------------------------------------------------------------------

```python
"inspect.attr": Style(color="yellow", italic=True),
"inspect.attr.dunder": Style(color="yellow", italic=True, dim=True),
"inspect.callable": Style(bold=True, color="red"),
"inspect.async_def": Style(italic=True, color="bright_cyan"),
"inspect.def": Style(italic=True, color="bright_cyan"),
"inspect.class": Style(italic=True, color="bright_cyan"),
"inspect.error": Style(bold=True, color="red"),
"inspect.equals": Style(),
"inspect.help": Style(color="cyan"),
"inspect.doc": Style(dim=True),
"inspect.value.border": Style(color="green"),
```

`live` Namespace
----------------------------------------------------------------------------

```python
"live.ellipsis": Style(bold=True, color="red"),
```

`layout` Namespace
----------------------------------------------------------------------------

```python
"layout.tree.row": Style(dim=False, color="red"),
"layout.tree.column": Style(dim=False, color="blue"),
```

`logging` Namespace
----------------------------------------------------------------------------

```python
"logging.keyword": Style(bold=True, color="yellow"),
"logging.level.notset": Style(dim=True),
"logging.level.debug": Style(color="green"),
"logging.level.info": Style(color="blue"),
"logging.level.warning": Style(color="yellow"),
"logging.level.error": Style(color="red", bold=True),
"logging.level.critical": Style(color="red", bold=True, reverse=True),
```

`log` Namespace
----------------------------------------------------------------------------

```python
"log.level": Style.null(),
"log.time": Style(color="cyan", dim=True),
"log.message": Style.null(),
"log.path": Style(dim=True),
```

`repr` Namespace
----------------------------------------------------------------------------

```python
"repr.ellipsis": Style(color="yellow"),
"repr.indent": Style(color="green", dim=True),
"repr.error": Style(color="red", bold=True),
"repr.str": Style(color="green", italic=False, bold=False),
"repr.brace": Style(bold=True),
"repr.comma": Style(bold=True),
"repr.ipv4": Style(bold=True, color="bright_green"),
"repr.ipv6": Style(bold=True, color="bright_green"),
"repr.eui48": Style(bold=True, color="bright_green"),
"repr.eui64": Style(bold=True, color="bright_green"),
"repr.tag_start": Style(bold=True),
"repr.tag_name": Style(color="bright_magenta", bold=True),
"repr.tag_contents": Style(color="default"),
"repr.tag_end": Style(bold=True),
"repr.attrib_name": Style(color="yellow", italic=False),
"repr.attrib_equal": Style(bold=True),
"repr.attrib_value": Style(color="magenta", italic=False),
"repr.number": Style(color="cyan", bold=True, italic=False),
"repr.number_complex": Style(color="cyan", bold=True, italic=False),  # same
"repr.bool_true": Style(color="bright_green", italic=True),
"repr.bool_false": Style(color="bright_red", italic=True),
"repr.none": Style(color="magenta", italic=True),
"repr.url": Style(underline=True, color="bright_blue", italic=False, bold=False),
"repr.uuid": Style(color="bright_yellow", bold=False),
"repr.call": Style(color="magenta", bold=True),
"repr.path": Style(color="magenta"),
"repr.filename": Style(color="bright_magenta"),
```

`rule` Namespace
----------------------------------------------------------------------------

```python
"rule.line": Style(color="bright_green"),
"rule.text": Style.null(),
```

`json` Namespace
----------------------------------------------------------------------------

```python
"json.brace": Style(bold=True),
"json.bool_true": Style(color="bright_green", italic=True),
"json.bool_false": Style(color="bright_red", italic=True),
"json.null": Style(color="magenta", italic=True),
"json.number": Style(color="cyan", bold=True, italic=False),
"json.str": Style(color="green", italic=False, bold=False),
"json.key": Style(color="blue", bold=True),
```

`prompt` Namespace
----------------------------------------------------------------------------

```python
"prompt": Style.null(),
"prompt.choices": Style(color="magenta", bold=True),
"prompt.default": Style(color="cyan", bold=True),
"prompt.invalid": Style(color="red"),
"prompt.invalid.choice": Style(color="red"),
```

`pretty` Namespace
----------------------------------------------------------------------------

```python
"pretty": Style.null(),
```

`scope` Namespace
----------------------------------------------------------------------------

```python
"scope.border": Style(color="blue"),
"scope.key": Style(color="yellow", italic=True),
"scope.key.special": Style(color="yellow", italic=True, dim=True),
"scope.equals": Style(color="red"),
```

`table` Namespace
----------------------------------------------------------------------------

```python
"table.header": Style(bold=True),
"table.footer": Style(bold=True),
"table.cell": Style.null(),
"table.title": Style(italic=True),
"table.caption": Style(italic=True, dim=True),
```

`traceback` Namespace
----------------------------------------------------------------------------

```python
"traceback.error": Style(color="red", italic=True),
"traceback.border.syntax_error": Style(color="bright_red"),
"traceback.border": Style(color="red"),
"traceback.text": Style.null(),
"traceback.title": Style(color="red", bold=True),
"traceback.exc_type": Style(color="bright_red", bold=True),
"traceback.exc_value": Style.null(),
"traceback.offset": Style(color="bright_red", bold=True),
"traceback.error_range": Style(underline=True, bold=True),
"traceback.note": Style(color="green", bold=True),
"traceback.group.border": Style(color="magenta"),
```

`bar` Namespace
----------------------------------------------------------------------------

```python
"bar.back": Style(color="grey23"),
"bar.complete": Style(color="rgb(249,38,114)"),
"bar.finished": Style(color="rgb(114,156,31)"),
"bar.pulse": Style(color="rgb(249,38,114)"),
```

`progress` Namespace
----------------------------------------------------------------------------

```python
"progress.description": Style.null(),
"progress.filesize": Style(color="green"),
"progress.filesize.total": Style(color="green"),
"progress.download": Style(color="green"),
"progress.elapsed": Style(color="yellow"),
"progress.percentage": Style(color="magenta"),
"progress.remaining": Style(color="cyan"),
"progress.data.speed": Style(color="red"),
"progress.spinner": Style(color="green"),
```

`status` Namespace
----------------------------------------------------------------------------

```python
"status.spinner": Style(color="green"),
```

`tree` Namespace
----------------------------------------------------------------------------

```python
"tree": Style(),
"tree.line": Style(),
```

`markdown` Namespace
----------------------------------------------------------------------------

```python
"markdown.paragraph": Style(),
"markdown.text": Style(),
"markdown.em": Style(italic=True),
"markdown.emph": Style(italic=True),  # For commonmark backwards compatibility
"markdown.strong": Style(bold=True),
"markdown.code": Style(bold=True, color="cyan", bgcolor="black"),
"markdown.code_block": Style(color="cyan", bgcolor="black"),
"markdown.block_quote": Style(color="magenta"),
"markdown.list": Style(color="cyan"),
"markdown.item": Style(),
"markdown.item.bullet": Style(bold=True),
"markdown.item.number": Style(color="cyan"),
"markdown.hr": Style(dim=True),
"markdown.h1.border": Style(),
"markdown.h1": Style(bold=True, underline=True),
"markdown.h2": Style(color="magenta", underline=True),
"markdown.h3": Style(color="magenta", bold=True),
"markdown.h4": Style(color="magenta", italic=True),
"markdown.h5": Style(italic=True),
"markdown.h6": Style(dim=True),
"markdown.h7": Style(italic=True, dim=True),
"markdown.link": Style(color="bright_blue"),
"markdown.link_url": Style(color="blue", underline=True),
"markdown.s": Style(strike=True),
"markdown.table.border": Style(color="cyan"),
"markdown.table.header": Style(color="cyan", bold=False),
```

`iso8601` Namespace
----------------------------------------------------------------------------

```python
"iso8601.date": Style(color="blue"),
"iso8601.time": Style(color="magenta"),
"iso8601.timezone": Style(color="yellow"),
```
"""

PALETTE_ANSI_DARK: dict[str, str] = dict(
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
"""The current default theme, initially set to {py:data}`THEME`."""


def get_default_theme() -> Theme:
    """Get the current default theme."""
    return _default_theme


def set_default_theme(theme: ToTheme) -> None:
    """
    Set the default theme.

    ## Parameters

    -   `theme`: A theme or value coercible to one via {py:func}`to_theme`.
    """
    global _default_theme
    _default_theme = to_theme(theme)


# Conversion
# ============================================================================


def to_theme(value: ToTheme | None = None) -> Theme:
    """Convert a `value` into a {py:class}`rich.theme.Theme`.

    ## Parameters

    -   `value`: Converted as follows:

        -   {py:class}`rich.theme.Theme`: returned as-is.

        -   {py:class}`~collections.abc.Mapping`: layered over the default
            {py:data}`THEME`.

        -   {py:class}`typing.IO`: read theme from file via
            {py:meth}`rich.theme.Theme.from_file`.

        -   {py:data}`None`: returns a copy of the default theme.

    ## Returns

    A {py:class}`rich.theme.Theme` instance.

    ## Examples

    Default returns a copy of the base theme:

    ```python
    >>> theme = to_theme()
    >>> isinstance(theme, Theme)
    True

    ```

    Pass a {py:class}`~collections.abc.Mapping` to add/override styles:

    ```python
    >>> theme = to_theme({"custom.style": "bold red"})
    >>> "custom.style" in theme.styles
    True

    ```

    Existing Theme is returned as-is:

    ```python
    >>> original = Theme({})
    >>> to_theme(original) is original
    True

    ```
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

    if isinstance(value, Mapping):
        # Given a `Mapping` layer it over the default `THEME` so it has our
        # custom styles (if you don't want this pass a `Theme` instance)
        styles = cast(dict[str, StyleType], THEME.styles.copy())
        styles.update(value)
        return Theme(styles, inherit=False)

    assert_never(value, ToTheme)


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


THEME_ANSI_DARK = override_ansi_colors(THEME, **PALETTE_ANSI_DARK)
