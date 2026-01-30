from __future__ import annotations
from inspect import isclass
import logging
from pathlib import Path
import sys
from types import TracebackType
from typing import (
    IO,
    Any,
    Literal,
    NewType,
    Optional,
    Protocol,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    TYPE_CHECKING,
    runtime_checkable,
)
import typing
from collections.abc import Mapping, Callable

# Never was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never

# TypeIs was added to stdlib typing in 3.13
if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

from rich.console import Console, ConsoleRenderable, RenderableType, RichCast
from rich.style import StyleType
from rich.theme import Theme
from typeguard import check_type, TypeCheckError

from splatlog.lib import fmt_list, fmt_type_of, fmt_type_value
from splatlog.lib.text import fmt


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

# Stdlib Types
# ----------------------------------------------------------------------------
#
# Adapted from Pyright types in order to conform to the stdlib


_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsDunderLT(Protocol[_T_contra]):
    def __lt__(self, __other: _T_contra) -> bool: ...


class SupportsDunderGT(Protocol[_T_contra]):
    def __gt__(self, __other: _T_contra) -> bool: ...


# If we need them in the future...
#
# class SupportsDunderLE(Protocol[_T_contra]):
#     def __le__(self, __other: _T_contra) -> bool:
#         ...
#
# class SupportsDunderGE(Protocol[_T_contra]):
#     def __ge__(self, __other: _T_contra) -> bool:
#         ...


#: A type that supports `<` and `>` operations (`__lt__` and `__gt__` methods).
#:
#: Copied from whatever VSCode is using for type definitions since I can't
#: figure out how to import or reference it.
#:
SupportsRichComparison: TypeAlias = (
    SupportsDunderLT[Any] | SupportsDunderGT[Any]
)

# If we need it in the future...
# SupportsRichComparisonT = TypeVar("SupportsRichComparisonT", bound=SupportsRichComparison)


class SupportsFilter(Protocol):
    """
    Type for objects that can filter, in the sense of
    {py:class}`logging.Filter`.
    """

    def filter(
        self, record: logging.LogRecord, /
    ) -> bool | logging.LogRecord: ...


FilterType: TypeAlias = (
    logging.Filter
    | Callable[[logging.LogRecord], bool | logging.LogRecord]
    | SupportsFilter
)
"""
The type of items in the `filters` list of {py:class}`logging.Filterer`.
"""

KwdMapping: TypeAlias = Mapping[str, Any]
"""
{py:class}`collections.abc.Mapping` with {py:class}`str` keys, named such
because it can be used as keyword arguments.
"""


# Level Types
# ----------------------------------------------------------------------------

Level: TypeAlias = int
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

1.  {py:func}`is_level_name`
2.  {py:func}`logging.addLevelName`
3.  {py:func}`logging.getLevelNamesMapping` (Python 3.11+)
"""

ToLevel: TypeAlias = Level | LevelName
"""
What can be converted into a {py:type}`Level`:

1.  Already a {py:type}`Level` integer,
2.  a {py:class}`str` encoding of one, or
3.  a {py:class}`str` that is a registered {py:type}`LevelName`
    (case-insensitive).

## See Also

1.  {py:func}`can_be_level`
2.  {py:func}`to_level`
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

VerbositySpec: TypeAlias = Mapping[Verbosity, ToLevel]
"""
A {py:class}`collections.abc.Mapping` of {py:type}`Verbosity` to
{py:type}`Level`, indicating the level that takes effect at various verbosities.

Given a verbosity `v and spec `S`, the effective level is

    S[max(k for k in S if k <= v)]

"""

NameMapSpec: TypeAlias = Mapping[str, ToLevel | VerbositySpec]

LevelSpec: TypeAlias = ToLevel | VerbositySpec | NameMapSpec
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

# An object that "is Rich".
Rich: TypeAlias = ConsoleRenderable | RichCast

StdioName: TypeAlias = Literal["stdout", "stderr"]

ToRichConsole: TypeAlias = Console | Mapping[str, Any] | StdioName | IO[str]
"""
What we can convert to a {py:class}`rich.console.Console`. See
{py:func}`splatlog.rich.console.to_console`.
"""

ToTheme: TypeAlias = Theme | IO[str] | Mapping[str, StyleType]
"""
What we can convert to a {py:class}`rich.theme.Theme`. See
{py:func}`splatlog.rich.theme.to_theme` for details.
"""


@runtime_checkable
class RichTyped(Protocol):
    """
    An extension of the "rich dunder protocol" system to allow classes to
    control how their type is printed by Rich.

    As an extension, the protocol is not used by Rich itself, but is preferred
    by `splatlog.rich.enrich_type` to format object types.

    ##### Examples #####

    The method should be defined as a `classmethod` since the class is the
    receiver that makes sense. In this case, we'll define a class `A` that
    will print it's module and class name in a `rich.panel.Panel`.

    ```python
    >>> from rich.panel import Panel

    >>> class A:
    ...     @classmethod
    ...     def __rich_type__(cls) -> RenderableType:
    ...         return Panel(cls.__module__ + "." + cls.__qualname__)

    ```

    Note that both the `A` class _and_ instances will test as expressing the
    protocol.

    ```python
    >>> isinstance(A, RichTyped)
    True

    >>> isinstance(A(), RichTyped)
    True

    ```

    To wrap things up we'll create an instance of `A`, extract it's "Rich type"
    with `splatlog.rich.enrich_type`, and print our panel!

    ```python
    >>> from rich.console import Console
    >>> from splatlog.rich import enrich_type

    >>> a = A()
    >>> Console(width=40).print(enrich_type(a))
    ╭──────────────────────────────────────╮
    │ splatlog.typings.A                   │
    ╰──────────────────────────────────────╯

    ```
    """

    def __rich_type__(self) -> RenderableType: ...


# JSON Types
# ----------------------------------------------------------------------------

# SEE https://docs.python.org/3.10/library/json.html#json.JSONEncoder
JSONEncodable: TypeAlias = dict | list | tuple | str | int | float | bool | None
"""
Types that {py:class}`json.JSONEncoder` can encode (by default), from the list
in the class docs.
"""

JSONReduceFn: TypeAlias = Callable[[Any], JSONEncodable]
"""
A function that performs reducing to a {py:type}`JSONEncodable`, which
{py:class}`json.JSONEncoder` can then JSON encode.
"""

JSONEncoderStyle = Literal["compact", "pretty"]

ToJSONFormatter = Union[None, "JSONFormatter", JSONEncoderStyle, KwdMapping]

JSONEncoderCastable = Union[None, "JSONEncoder", JSONEncoderStyle, KwdMapping]

OnReducerError: TypeAlias = Literal["continue", "raise", "warn"]
"""
Ways to handle when a {py:class}`splatlog.json.JSONReducer` raises an error
matching or reducing an object in {py:meth}`splatlog.json.JSONEncoder.default`:

-   `"continue"` (default) — ignore and continue with the next reducer.
-   `"raise"` — raise an error.
-   `"warn"` — issue a warning and continue with the next reducer. Uses
    {py:func}`warnings.warn` as
"""

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

ToConsoleHandler = (
    logging.Handler | KwdMapping | Literal[True] | ToLevel | ToRichConsole
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

    if sys.version_info >= (3, 11):
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


def is_level(value: object) -> TypeIs[Level]:
    """
    Test if `value` is a {py:type}`Level`, which we define as any integer,
    excluding the booleans {py:data}`True` and {py:data}`False`.

    ## Examples

    ```python

    >>> is_level(logging.DEBUG)
    True

    >>> is_level(1234)
    True

    >>> is_level(-1)
    True

    >>> is_level(True)
    False

    >>> is_level(False)
    False

    ```
    """
    return isinstance(value, int) and not (value is True or value is False)


def can_be_level(
    value: object, *, case_sensitive: bool = False
) -> TypeIs[ToLevel]:
    """
    Can `value` be converted to a {py:type}`Level`?

    Must be one of:

    1.  Already a {py:type}`Level` (any {py:class}`int` besides {py:data}`True`
        and {py:data}`False`),
    2.  {py:class}`str` representation of a {py:type}`Level`, or
    3.  {py:class}`str` that is a registered {py:type}`LevelName`
        (case-insensitive).

    ## Examples

    ```python
    >>> can_be_level(logging.DEBUG)
    True

    >>> can_be_level("10")
    True

    >>> can_be_level("debug")
    True

    >>> can_be_level("DEBUG")
    True

    >>> can_be_level(-1)
    True

    >>> can_be_level("-1")
    False

    >>> can_be_level("not_a_level")
    False

    >>> can_be_level(True)
    False

    ```
    """
    return (
        is_level_name(value, case_sensitive=case_sensitive)
        or (isinstance(value, str) and value.isdigit())
        or is_level(value)
    )


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
        isinstance(k, int) and can_be_level(v) for k, v in x.items()
    )


# Spec Tests
# ----------------------------------------------------------------------------


def is_name_map_spec(x: object) -> TypeIs[NameMapSpec]:
    return isinstance(x, Mapping) and all(
        isinstance(k, str) and (can_be_level(v) or is_verbosity_spec(v))
        for k, v in x.items()
    )


# Rich Tests
# ----------------------------------------------------------------------------


def is_rich(x: object) -> TypeIs[Rich]:
    """
    Is an object "rich"? This amounts to:

    1.  Fulfilling one of the protocols:
        -   `rich.console.ConsoleRenderable` — having a `__rich_console__`
            method, the signature of which is:

            ```python
            def __rich_console__(
                self,
                console: rich.console.Console,
                options: rich.console.ConsoleOptions
            ) -> rich.console.RenderResult:
                ...
            ```

        -   `rich.console.RichCast` — having a `__rich__ method, the signature
            of which is:

            ```python
            def __rich__(self) -> rich.console.RenderableType:
                ...
            ```

    2.  **_Not_** being a class (tested with `inspect.isclass`).

        This check is applied a few places in the Rich rendering code, and is
        there because a simple check like

        ```python
        hasattr(renderable, "__rich_console__")
        ```

        is used to test if an object fulfills the protocols from (1). Those
        attributes are assumed to be _instance methods_, which show up as
        attributes on the class objects as well.

        The additional

        ```python
        not isclass(renderable)
        ```

        check prevents erroneously calling those instance methods on the class
        objects.
    """
    return isinstance(x, (ConsoleRenderable, RichCast)) and not isclass(x)


def is_stdio_name(value: Any) -> TypeIs[StdioName]:
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


def is_to_rich_console(value: Any) -> TypeIs[ToRichConsole]:
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


# Conversions
# ============================================================================

# Level Conversions
# ----------------------------------------------------------------------------


def to_level_name(level_value: Level) -> LevelName:
    return logging.getLevelName(level_value)


def to_level(value: ToLevel, *, case_sensitive: bool = False) -> Level:
    """
    Obtain a {py:mod}`logging` {py:type}`Level` integer from more
    useful/intuitive things, like strings you might get from an environment
    variable or command line option.

    ## Parameters

    -   `value`: {py:type}`ToLevel` value to convert.

    -   `case_sensitive`: when {py:data}`False` (default), both a given
        {py:class}`str` `value` and its {py:meth}`str.upper` transformation will
        be tried as level names.

        When {py:data}`True`, level names must be verbatim.

    ## Examples

    **{py:class}`int` Values**

    Any integer is simply returned. This tracks the current {py:mod}`logging`
    module logic, in particular the `_checkLevel` function.

    ```python
    >>> to_level(logging.DEBUG)
    10

    >>> to_level(123)
    123

    >>> to_level(-1)
    -1

    ```

    No, I have no idea what kind of mess using negative level values might
    cause.

    **{py:class}`str` Values**

    Integer levels can be encoded as strings. IDK if this will happen much in
    practice, but it's easy to tell what you mean, so we handle it. Again, the
    integers don't have to correspond to any named level.

    ```python
    >>> to_level("8")
    8

    ```

    We also accept level *names*.

    ```python
    >>> to_level("DEBUG")
    10

    ```

    By default, both the `value` and the {py:meth}`str.upper` version are
    tried.

    ```python
    >>> to_level("debug")
    10
    >>> to_level("DeBuG")
    10

    ```

    If you specify `case_sensitive` behavior then level names must be exact.

    ```python
    >>> to_level("debug", case_sensitive=True)
    Traceback (most recent call last):
        ...
    TypeError: 'debug' is not a valid level name (case-sensitive)...

    >>> to_level("DEBUG", case_sensitive=True)
    10

    ```

    This works with custom levels as well.

    ```python
    >>> logging.addLevelName(8, "LUCKY")
    >>> to_level("lucky")
    8

    ```

    **Other**

    Everything else can kick rocks:

    ```python
    >>> to_level([])
    Traceback (most recent call last):
        ...
    AssertionError: Expected `int | str`, given `list`: `[]`

    ```
    """

    if isinstance(value, int):
        assert_level(value)
        return value

    if isinstance(value, str):
        # Accept string representation of integer, like `"10" → 10`
        if value.isdigit():
            level = int(value)
            assert_level(level)
            return level

        if sys.version_info >= (3, 11):
            mapping = logging.getLevelNamesMapping()

            if value in mapping:
                return mapping[value]

            if case_sensitive:
                raise TypeError(
                    (
                        "{} is not a valid level name (case-sensitive), "
                        "valid names: {}"
                    ).format(fmt(value), fmt_list(mapping.keys()))
                )

            upper_value = value.upper()

            if upper_value in mapping:
                return mapping[upper_value]

            raise TypeError(
                (
                    "Neither given value {} or upper-case version {} are valid "
                    "level names, valid names: {}"
                ).format(fmt(value), fmt(upper_value), fmt_list(mapping.keys()))
            )

        # This is the funky, pre-3.11 way (that I know) to go about it...

        # If `value` _is_ a registered level name then `getLevelName` will
        # return the level value (go figure)
        level = logging.getLevelName(value)

        if isinstance(level, int):
            return level

        if case_sensitive:
            raise TypeError(
                "{} is not a valid level name (case-sensitive)".format(
                    fmt(value)
                )
            )

        upper_value = value.upper()

        level = logging.getLevelName(upper_value)

        if isinstance(level, int):
            return level

        raise TypeError(
            (
                "Neither given value {} or upper-case version {} are valid "
                "level names"
            ).format(fmt(value), fmt(upper_value))
        )

    assert_never(value, ToLevel)


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


# Rich Conversions
# ----------------------------------------------------------------------------


def to_stdio(name: StdioName) -> IO[str]:
    match name:
        case "stdout":
            return sys.stdout
        case "stderr":
            return sys.stderr
        case _:
            raise TypeError(
                "expected {}, given {}".format(
                    fmt(StdioName), fmt_type_value(name)
                )
            )


# Assertions
# ============================================================================


def assert_level(level: ToLevel, *, var_name: str = "level"):
    if isinstance(level, str):
        if not is_level_name(level):
            raise ValueError(
                "Expected `{}` to be `{}`, given `str` but {} is not a valid level name".format(
                    var_name, fmt(ToLevel), fmt(level)
                )
            )
    elif isinstance(level, int):
        if not is_level(level):
            raise ValueError(
                "Expected `{}` to be `{}`, given `int` but {} is not a valid level".format(
                    var_name, fmt(ToLevel), fmt(level)
                )
            )
    else:
        assert_never(level, ToLevel)
