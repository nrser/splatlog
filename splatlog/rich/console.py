"""
Console creation and coercion utilities.
"""

from collections.abc import Mapping
import sys
from typing import IO, Any, Unpack
from rich.console import Console
from rich.style import Style
from rich.theme import Theme

from splatlog.lib.types import satisfies
from splatlog.types import (
    ConsoleKwds,
    ToRichConsole,
    assert_never,
    is_stdio_name,
    to_stdio,
)

from .theme import to_theme


def to_console(
    value: ToRichConsole | None = None, **kwds: Unpack[ConsoleKwds]
) -> Console:
    """Convert a `value` into a {py:class}`rich.console.Console`.

    ## Parameters

    -   `value`: The base to build from. Converted as follows:

        -   {py:class}`~rich.console.Console`: returned as-is. Because it is
            already a fully-constructed object, any `kwds` are _ignored_.

        -   {py:type}`~splatlog.types.ConsoleKwds` mapping: used as keyword
            arguments to {py:class}`rich.console.Console`.

        -   {py:class}`rich.theme.Theme`: shorthand for a console using that
            theme (may still be overridden by a `theme` keyword).

        -   {py:type}`~splatlog.types.StdioName`: write to the named standard
            output stream (`"stdout"`{l=py} or `"stderr"`{l=py}).

        -   {py:class}`typing.IO`: write to the given string I/O stream.

        -   {py:data}`None`: build from `kwds` alone (writing to
            {py:data}`sys.stderr` unless overridden).

    -   `kwds`: {py:class}`~rich.console.Console` keyword arguments (see
        {py:type}`~splatlog.types.ConsoleKwds`). These take **priority** over
        anything provided by `value` — if both set a key, the `kwds` value wins.

        The `theme` keyword is coerced through
        {py:func}`~splatlog.rich.theme.to_theme`, so it accepts anything
        {py:type}`~splatlog.types.ToTheme` allows. When `kwds` don't include a
        `theme`, the one carried by `value` — or, failing that, the default
        splatlog theme — applies.

    ## Returns

    A {py:class}`~rich.console.Console` instance.

    ## Examples

    Create a console with library defaults — uses the default splatlog theme
    {py:data}`~splatlog.rich.THEME` and writes to {py:data}`sys.stderr`.

    ```python
    >>> console = to_console()

    >>> import sys
    >>> console.file is sys.stderr
    True

    ```

    Write to stdout instead:

    ```python
    >>> console = to_console("stdout")
    >>> console.file is sys.stdout
    True

    ```

    Pass console options as a mapping:

    ```python
    >>> console = to_console({"force_terminal": True, "width": 120})
    >>> console.width
    120

    ```

    Options can also be given (or overridden) as keyword arguments:

    ```python
    >>> console = to_console({"width": 120}, width=80)
    >>> console.width
    80

    ```

    A `theme` keyword takes priority over one embedded in `value`:

    ```python
    >>> from rich.theme import Theme
    >>> from rich.style import Style

    >>> console = to_console(
    ...     {"theme": Theme({"info": "red"})},
    ...     theme=Theme({"info": "blue"}),
    ... )
    >>> console.get_style("info") == Style.parse("blue")
    True

    ```

    Without a `theme` keyword, the one carried by `value` is used:

    ```python
    >>> console = to_console({"theme": Theme({"info": "red"})})
    >>> console.get_style("info") == Style.parse("red")
    True

    ```
    """

    # A fully-constructed `Console` can't be reconfigured, so hand it back as-is.
    if isinstance(value, Console):
        return value

    # Collect the constructor kwds contributed by `value`, defaulting the output
    # stream to `sys.stderr`.
    console_kwds: dict[str, Any] = {"file": sys.stderr}

    if value is None:
        pass
    elif isinstance(value, Theme):
        console_kwds["theme"] = value
    elif isinstance(value, Mapping):
        console_kwds.update(value)
    elif is_stdio_name(value):
        console_kwds["file"] = to_stdio(value)
    elif satisfies(value, IO[str]):
        console_kwds["file"] = value
    else:
        assert_never(value, ToRichConsole)

    # Resolve the theme before `kwds` clobber it: a `theme` in `kwds` wins;
    # otherwise fall back to the one contributed by `value` (or the default).
    kwd_theme = kwds.get("theme")
    theme = kwd_theme if kwd_theme is not None else console_kwds.get("theme")

    # `kwds` take priority over whatever `value` contributed.
    console_kwds.update(kwds)

    # Always coerce to a `Theme` (`None` becomes the default splatlog theme).
    console_kwds["theme"] = to_theme(theme)

    return Console(**console_kwds)


def to_style(
    value: str | Style, *, console: ToRichConsole | None = None
) -> Style:
    """
    Convert a `value` to a {py:class}`rich.style.Style`, resolving from the
    styles in the given {py:class}`rich.console.Console`.

    Simply resolves the `console` using {py:func}`to_console` and calls
    {py:meth}`~rich.console.Console.get_style` with
    {py:obj}`rich.style.Style.null` as the `default`.

    Examples
    ----------------------------------------------------------------------------

    If `console` is omitted then a new instance is constructed over the
    {py:func}`splatlog.rich.get_default_theme` to source from.

    ```pycon
    >>> to_style("report.logger.name")
    Style(color=Color('blue', ColorType.STANDARD, number=4), bold=True)

    ```

    Falls back to the empty {py:obj}`rich.style.Style.null` style on missing
    style names.

    ```pycon
    >>> to_style("non.existent")
    Style()

    ```

    To customize styles, or just avoid constructing a
    {py:class}`~rich.console.Console` on every call, include a `console` keyword
    argument.

    ```pycon
    >>> from rich.console import Console
    >>> from rich.theme import Theme
    >>> from rich.style import Style

    >>> console = to_console()

    >>> with console.use_theme(Theme({
    ...     "report.logger.name": Style(color="#2563eb", bold=True)
    ... })):
    ...     print(to_style("report.logger.name", console=console))
    bold #2563eb

    >>> with console.use_theme(Theme({
    ...     "report.logger.name": Style(color="#047857", italic=True)
    ... })):
    ...     print(to_style("report.logger.name", console=console))
    italic #047857

    ```
    """
    return to_console(console).get_style(value, default=Style.null())
