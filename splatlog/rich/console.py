"""
Console creation and coercion utilities.
"""

from collections.abc import Mapping
import sys
from typing import IO, Any, cast
from rich.console import Console

from splatlog.lib.typeguard import satisfies
from splatlog.types import (
    ToRichConsole,
    ToTheme,
    assert_never,
    is_stdio_name,
    to_stdio,
)

from .theme import to_theme


def to_console(
    value: ToRichConsole | None = None, *, theme: ToTheme | None = None
) -> Console:
    """Convert a `value` into a {py:class}`rich.console.Console`.

    ## Parameters

    -   `value`: Converted as follows:

        -   {py:class}`rich.console.Console`: returned as-is.

        -   {py:class}`~collections.abc.Mapping`: used as keyword arguments to
            {py:class}`rich.console.Console`.

        -   {py:type}`splatlog.types.StdioName`: write to the named standard
            output stream (`"stdout"` or `"stderr"`).

        -   {py:class}`typing.IO`: write to the given string I/O stream.

        -   {py:data}`None`: create with library defaults (writes to
            {py:data}`sys.stderr`).

    -   `theme`: fallback theme to use, in the case that `value` doesn't provide
        one.

        {py:class}`rich.console.Console` values never use the `theme`.
        {py:class}`~collections.abc.Mapping` uses the `theme` when the `"theme"`
        key is _absent_ (_any_ value, including {py:data}`None`, will be used).

        Passed to {py:func}`splatlog.rich.to_theme` to convert it to a
        {py:class}`rich.theme.Theme` instance.

    ## Returns

    A {py:class}`rich.console.Console` instance.

    ## Examples

    Create a console with library defaults — uses
    {py:func}`splatlog.rich.get_default_theme` and writes to
    {py:data}`sys.stderr`.

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

    Provide a fallback {py:class}`rich.theme.Theme` to be used when `value`
    doesn't include one:

    ```python
    >>> from rich.theme import Theme
    >>> from rich.style import Style

    >>> console = to_console("stderr", theme=Theme({"info": "blue"}))
    >>> console.get_style("info") == Style.parse("blue")
    True

    ```
    """

    if value is None:
        return Console(file=sys.stderr, theme=to_theme(theme))

    if isinstance(value, Console):
        return value

    if isinstance(value, Mapping):
        # If the mapping has a `theme` use that
        if "theme" in value:
            theme = value["theme"]

        return Console(
            **cast(
                Mapping[str, Any],
                {
                    # Provide a default for `file`
                    "file": sys.stderr,
                    **value,
                    # Override the `theme`
                    "theme": to_theme(theme),
                },
            )
        )

    if is_stdio_name(value):
        return Console(file=to_stdio(value), theme=to_theme(theme))

    if satisfies(value, IO[str]):
        return Console(file=value, theme=to_theme(theme))

    assert_never(value, ToRichConsole)
