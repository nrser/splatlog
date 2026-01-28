from collections.abc import Mapping
import sys
from typing import IO, Any, cast
from rich.console import Console
from rich.theme import Theme

from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies
from splatlog.typings import ToRichConsole, is_stdio_name, to_stdio

from .theme import to_theme


def to_console(
    value: ToRichConsole | None = None, *, theme: Theme | None = None
) -> Console:
    """Convert a `value` into a {py:class}`rich.console.Console`.

    ## Parameters

    -   `value`: Converted as follows:

        -   {py:class}`rich.console.Console`: already cast, may be used as-is.

        -   {py:type}`splatlog.typings.StdioName`: write to the named standard
            output stream.

        -   {py:class}`typing.IO`: write to the given string I/O stream.

        -   {py:data}`None`: cast with library defaults.

    -   `theme`: Option to independently specify what theme is

    """
    if value is None:
        return Console(file=sys.stderr, theme=theme)

    if isinstance(value, Console):
        return value

    if isinstance(value, Mapping):
        return Console(
            **cast(
                Mapping[str, Any],
                {
                    "file": sys.stderr,
                    **value,
                    "theme": to_theme(value.get("theme")),
                },
            )
        )

    if is_stdio_name(value):
        return Console(file=to_stdio(value), theme=theme)

    if satisfies(value, IO[str]):
        return Console(file=value, theme=theme)

    raise TypeError(
        "expected `console` to be {}, given {}: {}".format(
            fmt(ToRichConsole),
            fmt(type(value)),
            fmt(value),
        )
    )
