from __future__ import annotations
import logging
from pathlib import Path
import sys
from types import TracebackType
from typing import (
    IO,
    Any,
    Literal,
    Optional,
    Type,
    TypeAlias,
    TypeGuard,
    Union,
    TYPE_CHECKING,
)
from collections.abc import Mapping, Sequence, Callable

from rich.style import StyleType
from rich.theme import Theme
from typeguard import check_type, TypeCheckError

from splatlog.lib.text import fmt
from splatlog.rich import ToRichConsole

if TYPE_CHECKING:
    from splatlog.verbosity.verbosity_level_resolver import (
        VerbosityLevelResolver,
    )
    from splatlog.json.json_formatter import JSONFormatter
    from splatlog.json.json_encoder import JSONEncoder

# Level Types
# ============================================================================
#
# There has always been some... frustration... typing `logging` levels. There is
# no typing in the builtin module. As such, this _kind-of_ follows the VSCode /
# PyLance typings from Microsoft. At least that way it corresponds decently to
# _something_ we're likely to be using.
#

LevelValue: TypeAlias = int
"""
The operational representation of a log level, per the built-in `logging`
package. When a {py:class}`logging.Handler` is assigned a level value it acts as
a _minimum_ — log messages with a lower level value will be ignored.
"""

LevelName: TypeAlias = str
"""
A name of a log level, such as `"debug"` or `"info"`.

Because the Python {py:mod}`logging` system allows custom log levels to be
introduced this is simply an alias for {py:class}`str`, though only specific
strings are valid level names.

```{note}
This type is screwy from a formal perspective —
```

## See Also

1.  {py:func}`splatlog.levels.is_level_name`
"""

Level: TypeAlias = LevelValue | LevelName
"""
What `splatlog` accepts as a log level; either a {py:type}`LevelValue` or a
{py:type}`LevelName`.

This corresponds to the `logging._Level` type used for the argument to
{py:meth}`logging.Logger.setLevel` in PyLance.
"""

# Verbosity
# ============================================================================

# Representation of a common "verbose" flag, where the repetition is stored as
# a count:
#
# (no flag) -> 0
# -v        -> 1
# -vv       -> 2
# -vvv      -> 3
#
Verbosity = int


def is_verbosity(x: object) -> TypeGuard[Verbosity]:
    """
    Test if a value is a _verbosity_.

    ##### Examples #####

    ```python
    >>> is_verbosity(0)
    True

    >>> is_verbosity(8)
    True

    >>> is_verbosity(-1)
    False

    >>> import sys
    >>> is_verbosity(sys.maxsize)
    False

    >>> is_verbosity(sys.maxsize - 1)
    True

    ```
    """
    return isinstance(x, int) and x >= 0 and x < sys.maxsize


def as_verbosity(x: object) -> Verbosity:
    """
    Cast a value to a _verbosity_, raising `TypeError` if unsuccessful.

    ##### Examples #####

    ```python
    >>> as_verbosity(0)
    0

    >>> as_verbosity(8)
    8

    >>> as_verbosity(-1)
    Traceback (most recent call last):
      ...
    TypeError: Expected verbosity to be non-negative integer less than
        `sys.maxsize`, given int: -1

    ```
    """
    if is_verbosity(x):
        return x
    raise TypeError(
        (
            "Expected verbosity to be non-negative integer less than "
            "`sys.maxsize`, given {}: {}"
        ).format(fmt(type(x)), fmt(x))
    )


VerbosityLevel = tuple[Verbosity, Level]

VerbosityRange = tuple[range, LevelValue]

VerbosityLevels = Mapping[str, "VerbosityLevelResolver"]

VerbosityLevelsCastable = Mapping[
    str, Union["VerbosityLevelResolver", Sequence[VerbosityLevel]]
]

# Rich
# ============================================================================

StdoutName = Literal["stdout", "stderr"]


def is_stdout_name(value: Any) -> TypeGuard[StdoutName]:
    """Is `value` a {py:type}`StdioName`?

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


RichThemeCastable = Theme | IO[str] | dict[str, StyleType]
"""

"""

# Named Handlers
# ============================================================================

OnConflict: TypeAlias = Literal["raise", "ignore", "replace"]

NamedHandlerCast = Callable[[Any], None | logging.Handler]
"""
A function that casts an argument to a {py:class}`logging.Handler` or returns
`None`.

Once registered by a `name` {py:class}`str` with
{py:func}`splatlog.named_handlers.register_named_handler` or the
{py:func}`splatlog.named_handlers.named_handler` decorator you can use the
`name` in {py:func}`splatlog.setup` same as
"""

KwdMapping = Mapping[str, Any]

ToConsoleHandler = (
    logging.Handler | KwdMapping | Literal[True] | Level | ToRichConsole
)
"""
What can be converted to a `console` named handlers, via constructing a
{py:class}`splatlog.rich_handler.RichHandler`.

See {py:func}`splatlog.named_handlers.to_console_handler` for details.
"""

JSONEncoderStyle = Literal["compact", "pretty"]

ToExportHandler = logging.Handler | KwdMapping | str | Path | IO[str]

JSONFormatterCastable = Union[
    None, "JSONFormatter", JSONEncoderStyle, KwdMapping
]

JSONEncoderCastable = Union[None, "JSONEncoder", JSONEncoderStyle, KwdMapping]

# Etc
# ============================================================================

# Modes that makes sense to open a logging file in
FileHandlerMode = Literal["a", "ab", "w", "wb"]

# It's not totally clear to me what the correct typing of "exc info" is... I
# read the CPython source, I looked at the Pylance types (from Microsoft), and
# this is what I settled on for this use case.
ExcInfo = tuple[Type[BaseException], BaseException, Optional[TracebackType]]
