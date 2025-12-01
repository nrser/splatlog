from __future__ import annotations
import logging
from pathlib import Path
import sys
from types import TracebackType
from typing import (
    IO,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeGuard,
    Union,
    Mapping,
    TYPE_CHECKING,
)

from rich.console import Console
from rich.theme import Theme
from typeguard import check_type, TypeCheckError

from splatlog.lib.text import fmt

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

# The "actual" representation of a log level, per the built-in `logging`
# package. Log messages with an equal or higher level number than the
# logger class' level number are emitted; those with a lower log number are
# ignored.
LevelValue = int

LevelName = str

# This corresponds to the `logging._Level` type in PyLance.
Level = Union[LevelValue, LevelName]

# Verbosity
# ============================================================================
#
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

StdioName = Literal["stdout", "stderr"]


def is_stdio_name(value: Any) -> TypeGuard[StdioName]:
    """\
    Is `value` a {py:type}`StdioName`?

    > 📝 NOTE Equivalent to {py:func}`splatlog.lib.satisfies`, which (to my
    > understanding) can not be typed to support type-narrowing over a
    > {py:type}`typing.Literal`.
    """
    try:
        check_type(value, StdioName)
    except TypeCheckError:
        return False
    return True


RichConsoleCastable = Union[None, Console, StdioName, IO[str]]


def is_rich_console_castable(value: Any) -> TypeGuard[RichConsoleCastable]:
    """\
    Is `value` a {py:type}`StdioName`?

    > 📝 NOTE Equivalent to {py:func}`splatlog.lib.satisfies`, which (to my
    > understanding) can not be typed to support type-narrowing over a
    > {py:type}`typing.Union`.
    """
    try:
        check_type(value, RichConsoleCastable)
    except TypeCheckError:
        return False
    return True


RichThemeCastable = Union[None, Theme, IO[str]]

# Named Handlers
# ============================================================================

NamedHandlerCast = Callable[[Any], None | logging.Handler]

KwdMapping = Mapping[str, Any]
HandlerCastable = Union[None, logging.Handler, KwdMapping]

ConsoleHandlerCastable = Union[
    HandlerCastable, bool, RichConsoleCastable, Level
]

JSONEncoderStyle = Literal["compact", "pretty"]

ExportHandlerCastable = Union[HandlerCastable, str, Path]

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
