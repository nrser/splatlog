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
    NewType,
    Optional,
    Type,
    TypeAlias,
    Union,
    TYPE_CHECKING,
)
import typing
from collections.abc import Mapping, Callable

# TypeIs was added to stdlib typing in 3.13; simplify when requires-python >= 3.13
if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

from typeguard import check_type, TypeCheckError

from splatlog.lib import fmt_type_of
from splatlog.lib.text import fmt
from splatlog.rich import ToRichConsole

if TYPE_CHECKING:
    from splatlog.json import JSONFormatter, JSONEncoder

# Helpers
# ============================================================================

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


# Types
# ============================================================================

# Level Types
# ----------------------------------------------------------------------------
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


# Verbosity Types
# ----------------------------------------------------------------------------

Verbosity = NewType("Verbosity", int)
"""
Representation of a common "verbose" flag, where the repetition is stored as
a count — no flag is `0`, `-v` is `1`, `-vv` is `2`, etc.

Implemented as a {py:class}`typing.NewType` because using bare {py:class}`int`
in verbosity/level associations easily loses context. Consider

    {
        0: "warning",
        1: "info",
        2: "debug",
    }

compared to

    {
        Verbosity(0): "warning",
        Verbosity(1): "info",
        Verbosity(2): "debug",
    }

The second example makes it much easier to remember what the keys represent. As
`Verbosity` is an {py:type}`int` at runtime the first form can still be used in
the REPL, as well as in scripts and programs that forgo type checking.
"""

ToVerbosity: TypeAlias = int | str
"""
What can be converted into a {py:type}`Verbosity`, in the sense of the
`verbosity` argument to {py:func}`splatlog.setup`
"""

VERBOSITY_MAX: Verbosity = Verbosity(16)


# Spec Types
# ----------------------------------------------------------------------------

VerbositySpec: TypeAlias = Mapping[Verbosity, Level]
"""
A {py:class}`collections.abc.Mapping` of {py:type}`Verbosity` to
{py:type}`Level`, indicating the level that takes effect at various verbosities.

Given a verbosity `v and spec `S`, the effective level is

    S[max(k for k in S if k <= v)]

"""

NameMapSpec: TypeAlias = Mapping[str, Level | VerbositySpec]

LevelSpec: TypeAlias = Level | VerbositySpec | NameMapSpec
"""
What you can set a logger of handler `level` to in Splatlog.

Really, it's logical combination of the `level` and `filter` functionality of
{py:class}`logging.Logger` and {py:class}`logging.Handler`, both of which act
to filter {py:class}`logging.LogRecord` instances.

If the filtering can be accomplished by setting `level` attributes, it will be.
More sophisticated filtering is achieved by adding a
{py:class}`splatlog.levels.Filter` instance.
"""

# Rich Types
# ----------------------------------------------------------------------------

StdioName = Literal["stdout", "stderr"]

# Named Handler Types
# ----------------------------------------------------------------------------

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
{py:class}`splatlog.RichHandler`.

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

# Other Types
# ----------------------------------------------------------------------------

# Modes that makes sense to open a logging file in
FileHandlerMode = Literal["a", "ab", "w", "wb"]

# It's not totally clear to me what the correct typing of "exc info" is... I
# read the CPython source, I looked at the Pylance types (from Microsoft), and
# this is what I settled on for this use case.
ExcInfo = tuple[Type[BaseException], BaseException, Optional[TracebackType]]

# Tests
# ============================================================================

# Level Tests
# ----------------------------------------------------------------------------


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


# Verbosity Tests
# ----------------------------------------------------------------------------


def is_verbosity(x: object) -> TypeIs[Verbosity]:
    """
    Test if a value is a _verbosity_.

    ## Examples

    ```python
    >>> is_verbosity(0)
    True

    >>> is_verbosity(8)
    True

    >>> is_verbosity(-1)
    False

    >>> is_verbosity(VERBOSITY_MAX)
    False

    >>> is_verbosity(VERBOSITY_MAX - 1)
    True

    ```
    """
    return isinstance(x, int) and x >= 0 and x < VERBOSITY_MAX


def is_verbosity_spec(x: object) -> TypeIs[VerbositySpec]:
    return isinstance(x, Mapping) and all(
        isinstance(k, int) and is_level(v) for k, v in x.items()
    )


# Spec Tests
# ----------------------------------------------------------------------------


def is_name_map_spec(x: object) -> TypeIs[NameMapSpec]:
    return isinstance(x, Mapping) and all(
        isinstance(k, str) and (is_level(v) or is_verbosity_spec(v))
        for k, v in x.items()
    )


# Rich Tests
# ----------------------------------------------------------------------------


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


# Conversions
# ============================================================================

# Level Conversions
# ----------------------------------------------------------------------------


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
                "Neither given value {} or upper-case version {} are valid level names"
            ).format(fmt(level), fmt(upper_level))
        )

    assert_never(level, Level)


# Verbosity Conversions
# ----------------------------------------------------------------------------


def to_verbosity(x: object) -> Verbosity:
    """
    Cast a value to a _verbosity_, raising `TypeError` if unsuccessful.

    ## Examples

    ```python
    >>> to_verbosity(0)
    0

    >>> to_verbosity(8)
    8

    >>> to_verbosity(-1)
    Traceback (most recent call last):
        ...
    TypeError: Expected verbosity to be non-negative integer less than 16, given int: -1

    ```
    """
    if isinstance(x, str):
        x = int(x)

    if is_verbosity(x):
        return x

    raise TypeError(
        "Expected verbosity to be non-negative integer less than {}, given {}: {}".format(
            fmt(VERBOSITY_MAX), fmt(type(x)), fmt(x)
        )
    )


# Spec Conversions
# ----------------------------------------------------------------------------


# Assertions
# ============================================================================


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
