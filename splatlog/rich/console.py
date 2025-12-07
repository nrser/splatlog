import sys
from typing import IO, Any, Literal, TypeAlias, TypeGuard
from rich.console import Console
from rich.theme import Theme
from typeguard import check_type, TypeCheckError

from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies

StdoutName = Literal["stdout", "stderr"]

ToRichConsole: TypeAlias = Console | StdoutName | IO[str] | None
"""
What we can convert to a {py:class}`rich.console.Console`. See
{py:func}`splatlog.rich.console.to_rich_console`.
"""


def is_stdout_name(value: Any) -> TypeGuard[StdoutName]:
    """Is `value` a {py:type}`splatlog.rich.console.StdioName`?

    ```{note}

    Equivalent to {py:func}`splatlog.lib.satisfies`, which (to my understanding)
    can not be typed to support type-narrowing over a {py:type}`typing.Literal`.

    ```
    """
    try:
        check_type(value, StdoutName)
    except TypeCheckError:
        return False
    return True


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

        -   {py:type}`splatlog.typings.StdoutName`: write to the named standard
            output stream.

        -   {py:class}`typing.IO`: write to the given string I/O stream.

        -   {py:data}`None`: cast with library defaults.

    -   `theme`: Option to independently specify what theme is

    """
    if value is None:
        return Console(file=sys.stderr, theme=theme)

    if isinstance(value, Console):
        return value

    if is_stdout_name(value):
        return Console(
            file=(sys.stderr if value == "stderr" else sys.stdout),
            theme=theme,
        )

    if satisfies(value, IO[str]):
        return Console(file=value, theme=theme)

    raise TypeError(
        "expected `console` to be {}, given {}: {}".format(
            fmt(ToRichConsole),
            fmt(type(value)),
            fmt(value),
        )
    )
