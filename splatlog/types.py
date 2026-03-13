"""
Type definitions for splatlog.

Provides type aliases, protocols, type guards, and conversion functions used
throughout the package. Many types accept a variety of input formats that can
be converted to a canonical form (the `To*` convention).
"""

from __future__ import annotations
from inspect import isclass
import logging
import os
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
    Never,
)
from collections.abc import Mapping, Callable

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


def assert_never(arg: Never, typ: Any) -> Never:
    """Statically assert that a line of code is unreachable.

    If a type checker finds that a call to `assert_never` is reachable, it will
    emit an error. At runtime, raises {py:class}`AssertionError`.

    ## Parameters

    -   `arg`: The value that should be unreachable ({py:class}`typing.Never`).
    -   `typ`: The expected type, included in the error message for clarity.

    ## Examples

    ```python
    def int_or_str(arg: int | str) -> None:
        match arg:
            case int():
                print("It's an int")
            case str():
                print("It's a str")
            case _:
                assert_never(arg, int | str)
    ```
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


SupportsRichComparison: TypeAlias = (
    SupportsDunderLT[Any] | SupportsDunderGT[Any]
)
"""
A type that supports `<` and `>` operations (`__lt__` and `__gt__` methods).

Adapted from Pyright's type definitions.
"""


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
"""
Upper bound (exclusive) on verbosity values. Verbosities must be in
`range(0, VERBOSITY_MAX)`.
"""


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
"""
A {py:class}`collections.abc.Mapping` of logger names to their level
configuration, allowing per-logger level or verbosity-based filtering.
"""

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

Rich: TypeAlias = ConsoleRenderable | RichCast
"""
An object that implements {py:mod}`rich` rendering. It is the union of
{py:class}`rich.console.ConsoleRenderable` and
{py:class}`rich.console.RichCast`.

1.  {py:class}`~rich.console.ConsoleRenderable` — _directly_ renders itself as a
    stream or sequence of plain or styled text and other {py:type}`Rich`
    objects, with the {py:class}`rich.console.Console` available for reference.

    Implements

    ```python
    def __rich_console__(
        self,
        console: rich.console.Console,
        options: rich.console.ConsoleOptions,
    ) -> rich.console.RenderResult:
        ...
    ```

    where {py:type}`rich.console.RenderResult` is a
    {py:class}`~collections.abc.Iterable` of

    -   {py:class}`str` — plain text.
    -   {py:class}`rich.segment.Segment` — styled text.
    -   Other {py:type}`Rich` objects that can then be rendered-down further.

    As seen in the {py:meth}`~rich.console.ConsoleRenderable.__rich_console__`
    method signature, a {py:class}`~rich.console.Console` and
    {py:class}`~rich.console.ConsoleOptions` are passed in as arguments, allowing
    implementors to inspect the available {py:class}`rich.style.Style` and
    specify fallbacks.

2.  {py:class}`~rich.console.RichCast` — _converts_ itself to plain text or
    another {py:type}`Rich` object.

    Implements

    ```python
    def __rich__(
        self,
    ) -> rich.console.ConsoleRenderable | rich.console.RichCast | str:
        ...
    ```

    to convert itself into one of:

    -   {py:class}`str` — plain text.
    -   {py:class}`~rich.console.ConsoleRenderable` — directly renderable, as
        detailed above.
    -   {py:class}`~rich.console.RichCast` — another object that implements
        {py:meth}`~rich.console.RichCast.__rich__`, where the process can be repeated until a {py:class}`str` or
        {py:class}`~rich.console.ConsoleRenderable` is reached or a loop is
        detected.
"""

StdioName: TypeAlias = Literal["stdout", "stderr"]
"""
Name of a standard I/O output stream — `"stdout"` or `"stderr"`. May be used to
indicate the destination when configuring a handler (which is why `"stdin"` is
absent).
"""

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
    by {py:func}`splatlog.rich.enrich_type` to format object types.

    ## Examples

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
    │ splatlog.types.A                   │
    ╰──────────────────────────────────────╯

    ```
    """

    def __rich_type__(self) -> RenderableType: ...


# JSON Types
# ----------------------------------------------------------------------------

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

JSONEncoderPreset = Literal["compact", "pretty"]
"""
Names of preset configurations for {py:class}`splatlog.json.JSONEncoder`. Pass
to {py:meth}`splatlog.json.JSONEncoder.of` to construct instances with those
preset configurations.

## Examples

```python
>>> import sys
>>> from splatlog.json import JSONEncoder

>>> compact = JSONEncoder.of("compact")
>>> compact.dump({"x": 1, "y": 2}, sys.stdout)
{"x":1,"y":2}

>>> pretty = JSONEncoder.of("pretty")
>>> pretty.dump({"x": 1, "y": 2}, sys.stdout)
{
    "x": 1,
    "y": 2
}

```
"""

T_JSONFormatter = TypeVar("T_JSONFormatter", bound="JSONFormatter")
ToJSONFormatter = Union[T_JSONFormatter, None, JSONEncoderPreset, KwdMapping]
"""
Something that can be converted to a {py:class}`splatlog.json.JSONFormatter`.
When parameterized as {py:data}`ToJSONFormatter`[T], only values that can become
T are accepted (e.g. {py:data}`ToJSONFormatter`[MyFormatter] excludes the base
and other subclasses), so class methods like
{py:meth}`splatlog.json.JSONFormatter.of` can use
{py:data}`ToJSONFormatter`[Self] and have the type checker enforce the receiver
class.
"""

T_JSONEncoder = TypeVar("T_JSONEncoder", bound="JSONEncoder")
ToJSONEncoder = Union[T_JSONEncoder, None, JSONEncoderPreset, KwdMapping]
"""
Something that can be converted to a JSON encoder. When parameterized as
{py:data}`ToJSONEncoder`\\ [T], only values that can become T are accepted.
Use {py:data}`ToJSONEncoder`\\ [Self] in {py:meth}`splatlog.json.JSONEncoder.of`.
"""

OnReducerError: TypeAlias = Literal["continue", "raise", "warn"]
"""
Ways to handle when a {py:class}`splatlog.json.JSONReducer` raises an error
matching or reducing an object in {py:meth}`splatlog.json.JSONEncoder.default`:

-   `"continue"` (default) — ignore and continue with the next reducer.
-   `"raise"` — raise an error.
-   `"warn"` — issue a warning and continue with the next reducer. Uses
    {py:func}`warnings.warn` as we're a logging library and don't want to
    depend on logging being setup or end up circling back to the same problem.
"""

# Named Handler Types
# ----------------------------------------------------------------------------

OnConflict: TypeAlias = Literal["raise", "ignore", "replace"]
"""
Strategy for handling conflicts when registering a named handler that already
exists: `"raise"`, `"ignore"`, or `"replace"`.

-   `"raise"`: Raise an exception.
-   `"ignore"`: Pretend it didn't happen.
-   `"replace"`: Clobber the old handler, installing the new one.
"""

NamedHandlerFactory = Callable[[Any], None | logging.Handler]
"""
A function that casts an argument to a {py:class}`logging.Handler` or returns
{py:data}`None`.

Once registered by name with
{py:func}`splatlog.named_handlers.put_factory` or the
{py:func}`splatlog.named_handlers.register` decorator, the name can be
used as a keyword argument to {py:func}`splatlog.setup`.
"""

ToConsoleHandler = (
    logging.Handler | KwdMapping | Literal[True] | ToLevel | ToRichConsole
)
"""
What can be converted to a `console` named handler, mainly via constructing a
{py:class}`splatlog.rich.RichHandler`.

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

FileHandlerMode = Literal["a", "ab", "w", "wb"]
"""File open modes that make sense for logging file handlers."""

ExcInfo = tuple[Type[BaseException], BaseException, Optional[TracebackType]]
"""
Exception info tuple, as returned by {py:func}`sys.exc_info` when an
exception is active.
"""

# Tests
# ============================================================================

# Level Tests
# ----------------------------------------------------------------------------


def is_level_name(
    name: object, *, case_sensitive: bool = False
) -> TypeIs[LevelName]:
    """
    Test if `name` is a registered log level name.

    ## Parameters

    -   `name`: Value to test.
    -   `case_sensitive`: When {py:data}`False` (default), `name` is
        upper-cased before checking.

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

    return name in logging.getLevelNamesMapping()


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
    """Test if `x` is a {py:type}`VerbositySpec`."""
    return isinstance(x, Mapping) and all(
        isinstance(k, int) and can_be_level(v) for k, v in x.items()
    )


# Spec Tests
# ----------------------------------------------------------------------------


def is_name_map_spec(x: object) -> TypeIs[NameMapSpec]:
    """Test if `x` is a {py:type}`NameMapSpec`."""
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


def is_to_rich_console(value: object) -> TypeIs[ToRichConsole]:
    """Is `value` a {py:type}`ToRichConsole`?

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


# JSON Tests
# ----------------------------------------------------------------------------


def is_json_encoder_preset(value: object) -> TypeIs[JSONEncoderPreset]:
    """
    Is `value` a {py:type}`JSONEncoderPreset`?

    ## Examples

    ```python
    >>> is_json_encoder_preset("compact")
    True

    >>> is_json_encoder_preset("pretty")
    True

    >>> is_json_encoder_preset("invalid")
    False

    ```
    """
    try:
        check_type(value, JSONEncoderPreset)
    except TypeCheckError:
        return False
    return True


# Conversions
# ============================================================================

# Level Conversions
# ----------------------------------------------------------------------------


def to_level_name(level_value: Level) -> LevelName:
    """
    Get the name of a log level.

    ## Parameters

    -   `level_value`: The integer log level.

    ## Returns

    The registered name for the level (e.g. `"DEBUG"` for `10`).
    """
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
    """
    Convert a {py:type}`StdioName` to the corresponding {py:data}`sys.stdout`
    or {py:data}`sys.stderr` stream.

    ## Parameters

    -   `name`: `"stdout"` or `"stderr"`.

    ## Returns

    The {py:class}`typing.IO` stream object.
    """
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


def assert_level(level: ToLevel, *, var_name: str = "level") -> None:
    """
    Assert that `level` is a valid {py:type}`ToLevel` value.

    ## Parameters

    -   `level`: The value to validate.
    -   `var_name`: Variable name to include in error messages.

    ## Raises

    -   {py:class}`ValueError`:
        1.  If `level` is {py:data}`True` or {py:data}`False` (which are
            {py:class}`int`, but we exclude them).
        2.  a {py:class}`str` that is not a registered level name.

    -   {py:class}`AssertionError`: If `level` is not an {py:class}`int` or
        {py:class}`str`.
    """
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


ReportInclude: TypeAlias = Literal["all", "configured"]
"""
Filter options for which loggers to include in the report.

-   `"all"`: Include all loggers registered in the logging manager.
-   `"configured"`: Include only loggers with handlers or non-NOTSET level.
"""


# Doctests
# ============================================================================

# Are we testing? ENV flag is set in `tox.ini`, can set manually if need when
# running commands directly.
if os.environ.get("TESTING"):
    # `doctest` doesn't automatically pickup the "following docstring" format
    # used by Sphinx/MyST to document constants, so we need to do some AST
    # parsing and stick it in a `__test__` dict, which `doctest` looks for
    from splatlog._testing import get_constant_docstrings

    __test__ = get_constant_docstrings(__name__)
