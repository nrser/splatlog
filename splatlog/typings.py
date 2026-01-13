from __future__ import annotations
import logging
from pathlib import Path
import sys
from types import TracebackType
from typing import (
    IO,
    Any,
    Literal,
    Never,
    Optional,
    Type,
    TypeAlias,
    Union,
    TYPE_CHECKING,
)
import typing

# TypeIs was added to stdlib typing in 3.13; simplify when requires-python >= 3.13
if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs
from collections.abc import Mapping, Sequence, Callable

from typeguard import check_type, TypeCheckError

from splatlog.lib import fmt_type_of
from splatlog.lib.text import fmt
from splatlog.rich import ToRichConsole

if TYPE_CHECKING:
    from splatlog.levels import VerbosityLevelResolver
    from splatlog.json import JSONFormatter, JSONEncoder

_ASSERT_NEVER_REPR_MAX_LENGTH: int = getattr(
    typing, "_ASSERT_NEVER_REPR_MAX_LENGTH", 100
)


def assert_never(arg: Never, typ: Any) -> Never:
    """Statically assert that a line of code is unreachable.

    Example::

        def int_or_str(arg: int | str) -> None:
            match arg:
                case int():
                    print("It's an int")
                case str():
                    print("It's a str")
                case _:
                    assert_never(arg)

    If a type checker finds that a call to assert_never() is
    reachable, it will emit an error.

    At runtime, this throws an exception when called.
    """
    raise AssertionError(
        "Expected `{}`, given `{}`: `{}`".format(
            fmt(typ), fmt_type_of(arg), fmt(arg)
        )
    )


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


def to_level_name(level_value: LevelValue) -> LevelName:
    return logging.getLevelName(level_value)


def to_level_value(level: Level) -> LevelValue:
    """
    Make a `logging` level number from more useful/intuitive things, like string
    you might get from an environment variable or command option.

    ##### Examples #####

    ##### Integers #####

    Any integer is simply returned. This follows the logic in the stdlib
    `logging` package, `logging._checkLevel` in particular.

    ```python
    >>> to_level_value(logging.DEBUG)
    10

    >>> to_level_value(123)
    123

    >>> to_level_value(-1)
    -1

    ```

    No, I have no idea what kind of mess using negative level values might
    cause.

    ##### Strings #####

    Integer levels can be provided as strings. Again, they don't have to
    correspond to any named level.

    ```python
    >>> to_level_value("8")
    8

    ```

    We also accept level *names*.

    ```python
    >>> to_level_value("debug")
    10

    ```

    We use the oddly-named `logging.getLevelName` to figure out if a string
    is a level name (when given a string that is a level name it will
    return the integer level value).

    If we don't find the exact name we're given, we also try the upper-case
    version of the string.

    ```python
    >>> to_level_value("DEBUG")
    10
    >>> to_level_value("Debug")
    10

    ```

    This works with custom levels as well.

    ```python
    >>> logging.addLevelName(8, "LUCKY")
    >>> to_level_value("lucky")
    8

    ```

    ##### Other #####

    Everything else can kick rocks:

    ```python
    >>> to_level_value([])
    Traceback (most recent call last):
        ...
    AssertionError: Expected `int | str`, given `list`: `[]`

    ```
    """

    if isinstance(level, int):
        # TODO Make consistent with `is_level_value`?
        #
        # if is_level_value(level):
        #     return level

        # raise TypeError(f"`int` {level!r} is not a named log level")

        return level

    if isinstance(level, str):
        if level.isdigit():
            return int(level)

        level_value = logging.getLevelName(level)

        if isinstance(level_value, int):
            return level_value

        upper_level = level.upper()

        level_value = logging.getLevelName(upper_level)

        if isinstance(level_value, int):
            return level_value

        raise TypeError(
            (
                "Neither given value {} or upper-case version {} are valid "
                "level names"
            ).format(fmt(level), fmt(upper_level))
        )

    assert_never(level, Level)


def is_level_name(
    name: object, *, case_sensitive: bool = False
) -> TypeIs[LevelName]:
    """
    ## Examples

    ```python
    >>> is_level_name("DEBUG")
    True

    >>> is_level_name("LEVEL_NAME_TEST")
    False

    >>> level_value = hash("LEVEL_NAME_TEST") # Use somewhat unique int
    >>> logging.addLevelName(level_value, "LEVEL_NAME_TEST")
    >>> is_level_name("LEVEL_NAME_TEST")
    True

    ```
    """
    if not isinstance(name, str):
        return False

    # `logging` uses upper-case names, so convert to that unless we've been
    # asked not to
    if not case_sensitive:
        name = name.upper()

    # `logging.getLevelNamesMapping` was added in Python 3.11, providing a much
    # more sane way to figure out if a string is a level name.

    if hasattr(logging, "getLevelNamesMapping"):
        return name in logging.getLevelNamesMapping()

    # As of writing (2025-12-03) we `requires-python = ">=3.10"`, so
    # `logging.getLevelNamesMapping` might not be there. As we already have the
    # code to do the legacy detection, so it doesn't seem worth bumping the
    # required python version.
    #
    # This is uses a weird (and deprecated, in recent Pythons) way of testing if
    # `name` is a level name — `logging.getLevelName` will return the
    # `int` level if `name` is a known level name, otherwise returning
    # `f"Level {name}`
    if isinstance(logging.getLevelName(name), int):
        return True

    return False


def is_level_value(value: object) -> TypeIs[LevelValue]:
    """
    Test if `value` is a level value.

    Specifically, tests if `value` is a _named_ level value — a builtin one like
    `logging.DEBUG` or a custom one added with `logging.addLevelName`.

    Technically, it seems like you can use _any_ `int` as a level value, but it
    seems like it makes things simpler if all `LevelValue` have `LevelName` and
    vice-versa.

    We explicitly reject the booleans {py:data}`True` and {py:data}`False`,
    because `False` in particular is equal to {py:data}`logging.NOTSET` but
    that's never what you mean by passing it.

    ## Examples

    ```python

    >>> is_level_value(logging.DEBUG)
    True

    >>> level_value = hash("LEVEL_VALUE_TEST") # Use somewhat unique int
    >>> is_level_value(level_value)
    False

    >>> logging.addLevelName(level_value, "LEVEL_VALUE_TEST")
    >>> is_level_value(level_value)
    True

    >>> is_level_value(True)
    False

    >>> is_level_value(False)
    False

    ```
    """
    return (
        isinstance(value, int)
        and not (value is True or value is False)
        and logging.getLevelName(value) != f"Level {value}"
    )


def is_level(value: object, *, case_sensitive: bool = False) -> TypeIs[Level]:
    """
    Is `value` a logging level, in string or integer form? Tests if
    {py:func}`is_level_name` or {py:func}`is_level_value`.
    """
    return is_level_name(
        value, case_sensitive=case_sensitive
    ) or is_level_value(value)


def assert_level(level: Level, *, var_name: str = "level"):
    if isinstance(level, str):
        if not is_level_name(level):
            raise ValueError(
                "Expected `{}` to be `{}`, given `str` but {} is not a valid level name".format(
                    var_name, fmt(Level), fmt(level)
                )
            )
    elif isinstance(level, int):
        if not is_level_value(level):
            raise ValueError(
                "Expected `{}` to be `{}`, given `int` but {} is not a valid level value".format(
                    var_name, fmt(Level), fmt(level)
                )
            )
    else:
        assert_never(level, Level)


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

VerbosityLevel = tuple[Verbosity, Level]

VerbosityLevels = Mapping[str, "VerbosityLevelResolver"]

VerbosityValue = Union["VerbosityLevelResolver", Sequence[VerbosityLevel]]

ToVerbosityLevels = Mapping[str, VerbosityValue]


def is_verbosity(x: object) -> TypeIs[Verbosity]:
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


def to_verbosity(x: object) -> Verbosity:
    """
    Cast a value to a _verbosity_, raising `TypeError` if unsuccessful.

    ##### Examples #####

    ```python
    >>> to_verbosity(0)
    0

    >>> to_verbosity(8)
    8

    >>> to_verbosity(-1)
    Traceback (most recent call last):
        ...
    TypeError: Expected verbosity to be non-negative integer less than `sys.maxsize`, given int: -1

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


def is_verbosity_level(value: object) -> TypeIs[VerbosityLevel]:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and is_verbosity(value[0])
        and is_level(value[1])
    )


def is_verbosity_value(value: Any) -> TypeIs[VerbosityValue]:
    from splatlog.levels.verbosity_level_resolver import (
        VerbosityLevelResolver,
    )

    if isinstance(value, VerbosityLevelResolver):
        return True

    if isinstance(value, Sequence) and all(
        is_verbosity_level(vl) for vl in value
    ):
        return True

    return False


### Level Spec ###

LevelSpec: TypeAlias = Union[
    LevelValue,
    "VerbosityLevelResolver",
    dict[str, Union[LevelValue, "VerbosityLevelResolver"]],
]

ToLevelSpec: TypeAlias = (
    Level | VerbosityValue | Mapping[str, Level | VerbosityValue]
)


def to_level_spec(value: ToLevelSpec) -> LevelSpec:
    """
    Normalized an input `value` to a `LevelSpec`, which — in a loose sense — is
    anything you would specify as a level/verbosity-based filter on a logger or
    handler.

    ## Examples

    Normalizes {py:type}`Level` values to {py:type}`LevelValue` integers, see
    {py:func}`to_level_value` for details.

    ```python

    >>> import logging
    >>> to_level_spec("DEBUG")
    10
    >>> to_level_spec(logging.DEBUG)
    10
    >>> to_level_spec(99)
    99

    ```

    Normalizes verbosity/level mappings to a
    {py:class}`splatlog.levels.VerbosityLevelResolver`.

    ```python

    >>> from splatlog.levels import VerbosityLevelResolver
    >>> isinstance(
    ...     to_level_spec([(0, "ERROR"), (1, "WARNING"), (3, "INFO")]),
    ...     VerbosityLevelResolver
    ... )
    True

    ```

    A mapping is converted to a dict with normalized values:

    ```python

    >>> to_level_spec({"console": "DEBUG", "export": "INFO"})
    {'console': 10, 'export': 20}

    ```
    """
    from splatlog.levels.verbosity_level_resolver import (
        VerbosityLevelResolver,
    )

    # Already a VerbosityLevelResolver
    if isinstance(value, VerbosityLevelResolver):
        return value

    # Level as int or str (check before Sequence since str is a Sequence)
    if isinstance(value, (int, str)):
        return to_level_value(value)

    # Mapping[str, Level | VerbosityValue]
    if isinstance(value, Mapping):
        result: dict[str, LevelValue | VerbosityLevelResolver] = {}
        for key, val in value.items():
            if isinstance(val, VerbosityLevelResolver):
                result[key] = val
            elif isinstance(val, (int, str)):
                result[key] = to_level_value(val)
            elif isinstance(val, Sequence):
                result[key] = VerbosityLevelResolver(val)
            else:
                raise TypeError(
                    "Expected Level or VerbosityValue for key {}, "
                    "given {}: {}".format(fmt(key), fmt_type_of(val), fmt(val))
                )
        return result

    # Sequence[VerbosityLevel]
    if isinstance(value, Sequence):
        return VerbosityLevelResolver(value)

    assert_never(value, ToLevelSpec)


# Rich
# ============================================================================

StdioName = Literal["stdout", "stderr"]


def is_stdout_name(value: Any) -> TypeIs[StdioName]:
    """Is `value` a {py:type}`StdioName`?

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
What can be converted to a `console` named handler, mainly via constructing a
{py:class}`splatlog.rich_handler.RichHandler`.

See {py:func}`splatlog.named_handlers.to_console_handler` for details.
"""

ToExportHandler = logging.Handler | KwdMapping | str | Path | IO[str]
"""
What can be converted to an `export` named handler, mainly via constructing a
{py:class}`splatlog.json.JSONHandler`.

See {py:func}`splatlog.named_handlers.to_export_handler` for details.
"""

JSONEncoderStyle = Literal["compact", "pretty"]

ToJSONFormatter = Union[None, "JSONFormatter", JSONEncoderStyle, KwdMapping]

JSONEncoderCastable = Union[None, "JSONEncoder", JSONEncoderStyle, KwdMapping]

# Etc
# ============================================================================

# Modes that makes sense to open a logging file in
FileHandlerMode = Literal["a", "ab", "w", "wb"]

# It's not totally clear to me what the correct typing of "exc info" is... I
# read the CPython source, I looked at the Pylance types (from Microsoft), and
# this is what I settled on for this use case.
ExcInfo = tuple[Type[BaseException], BaseException, Optional[TracebackType]]
