from collections.abc import Mapping
import sys
from typing import IO, Any, Literal, TypeAlias, TypeGuard, cast
from rich.console import Console
from rich.theme import Theme
from typeguard import check_type, TypeCheckError

from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies
from splatlog.rich import to_theme

StdioName = Literal["stdout", "stderr"]

ToRichConsole: TypeAlias = (
    Console | Mapping[str, Any] | StdioName | IO[str] | None
)
"""
What we can convert to a {py:class}`rich.console.Console`. See
{py:func}`splatlog.rich.console.to_console`.
"""


def is_stdio_name(value: Any) -> TypeGuard[StdioName]:
    """Is `value` a {py:type}`splatlog.rich.console.StdioName`?

    ```{note}

    Equivalent to {py:func}`splatlog.lib.satisfies`, which (to my understanding)
    can not be typed to support type-narrowing over a {py:type}`typing.Literal`.

    ```
    """
    try:
        check_type(value, StdioName)
    except TypeCheckError:
        return False
    return True


def to_stdio(name: StdioName) -> IO[str]:
    match name:
        case "stdout":
            return sys.stdout
        case "stderr":
            return sys.stderr
        case _:
            raise TypeError(
                "expected {}, given {}: {}".format(
                    fmt(StdioName), fmt(type(name)), fmt(name)
                )
            )


def is_to_rich_console(value: Any) -> TypeGuard[ToRichConsole]:
    """Is `value` a {py:type}`splatlog.rich.console.ToRichConsole`?

    ```{note}

    Equivalent to {py:func}`splatlog.lib.satisfies`, which (to my understanding)
    can not be typed to support type-narrowing over a {py:type}`typing.Union`.

    ```
    """
    try:
        check_type(value, ToRichConsole)
    except TypeCheckError:
        return False
    return True


def to_console(value: ToRichConsole, *, theme: Theme | None = None) -> Console:
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
