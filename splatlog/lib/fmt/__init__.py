import os
from collections.abc import Callable
from inspect import isclass, isroutine
import types
from typing import (
    Any,
    ForwardRef,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
import typing
from warnings import warn
import datetime as dt

from .formatter import Formatter
from .opts import FmtOpts, FmtOut

__all__ = [
    "Formatter",
    "FmtOpts",
    "FmtOut",
    "fmt",
]


Routine = (
    types.FunctionType
    | types.LambdaType
    | types.MethodType
    | types.BuiltinFunctionType
    | types.BuiltinMethodType
    | types.WrapperDescriptorType
    | types.MethodDescriptorType
    | types.ClassMethodDescriptorType
)

BUILTINS_MODULE = object.__module__
"""
The module name for built-in types (e.g., `str`, `int`).

The name is `'builtins'` but we read it from `object.__module__`.
"""

TYPING_MODULE = typing.__name__
"""
The module name of the {py:mod}`typing` module.

The name is `'typing'` but we read it from `typing.__name__`.
"""

LAMBDA_NAME = (lambda x: x).__name__
"""
The `__name__` attribute value for lambda functions (`"<lambda>"`).

The name is `'<lambda>'`, we get it from `(lambda x: x).__name__`.
"""

FQN_SEP = "."
"""
Separator for fully-qualified names, for example the '.' in 'typing.Any'.
"""


@Formatter
def fmt(opts: FmtOpts, x: object) -> FmtOut:
    """
    Format a `value` for concise, human-readable output.

    Dispatches to specialized formatters based on the value's type:
    typing constructs, types, and routines each have dedicated formatters.

    ## Parameters

    -   `opts`: Formatting options.
    -   `value`: The value to format.

    ## Returns

    A formatted string representation.

    ## Examples

    -   **Types & Type Hints** — Formats types by qualified name, and type
        hints with concise shorthands:

            >>> from collections.abc import Collection

            >>> fmt(str)
            'str'

            >>> fmt(Collection)
            'collections.abc.Collection'

            >>> fmt(str | None)
            'str | None'

            >>> fmt(list[int])
            'int[]'

            >>> fmt(dict[str, int])
            '{str: int}'

        See {py:func}`fmt_type` and {py:func}`fmt_type_hint` for more info.

    -   **Functions & Methods** — Uses {py:func}`inspect.isroutine` to detect
        functions and methods and format them clearly and concisely:

            >>> fmt(int.__add__)
            'int.__add__()'

        Compare to what {py:class}`str` (and {py:func}`repr`) will give you:

            >>> str(int.__add__)
            "<slot wrapper '__add__' of 'int' objects>"

        See {py:func}`fmt_routine` for more info.

    -   **Dates & Times** — Formats {py:class}`~datetime.datetime`, see
        {py:func}`fmt_datetime` and {py:attr}`FmtOpts.dt_fmt`.

            >>> import datetime as dt

            >>> fmt(dt.datetime(2026, 3, 10, 14, 23, 45, 123_456))
            '2026-03-10 14:23:45.123'

        Also handles {py:class}`datetime.date` and {py:class}`datetime.time`:

            >>> fmt(dt.date(2026, 3, 10))
            '2026-03-10'

            >>> fmt(dt.time(14, 23, 45, 123_456))
            '14:23:45.123'

        Produces a concise, readable rendering of {py:class}`datetime.timedelta`
        as well:

            >>> fmt_timedelta(dt.timedelta(milliseconds=12))
            '0.012'

            >>> fmt_timedelta(
            ...     dt.timedelta(days=1, hours=23, minutes=45, seconds=56)
            ... )
            '1d 23:45:56.000'

        {py:func}`fmt_timedelta` has more information and examples.
    """
    if is_typing(x):
        return fmt_type_hint.with_opts(opts)(x)

    if isinstance(x, type):
        return fmt_type.with_opts(opts)(x)

    if isroutine(x):
        return fmt_routine.with_opts(opts)(x)

    if isinstance(x, dt.datetime):
        return fmt_datetime.with_opts(opts)(x)

    if isinstance(x, dt.date):
        return fmt_date.with_opts(opts)(x)

    if isinstance(x, dt.time):
        return fmt_time.with_opts(opts)(x)

    if isinstance(x, dt.timedelta):
        return fmt_timedelta.with_opts(opts)(x)

    return opts.fallback(x)


@Formatter
def fmt_name(opts: FmtOpts, x: object) -> str:
    """
    Get the qualified name of an object, optionally with module prefix.

    ## Parameters

    -   `x`: The object to get the name of.
    -   `opts`: Formatting options.

    ## Returns

    The name as a string, or {py:data}`None` if the object has no name.
    """
    name = getattr(x, "__qualname__", None) or getattr(x, "__name__", None)
    if not isinstance(name, str):
        return ""
    if (
        opts.fqn
        and (module_name := getattr(x, "__module__", None))
        and (module_name != BUILTINS_MODULE or opts.fq_builtins)
    ):
        return f"{module_name}.{name}"
    return name


@Formatter
def fmt_routine(opts: FmtOpts, x: Routine) -> FmtOut:
    if x.__name__ == LAMBDA_NAME:
        return "λ()"

    if name := fmt_name.with_opts(opts)(x):
        return name + "()"

    return opts.fallback(x)


@Formatter
def fmt_type(opts: FmtOpts, x: type) -> FmtOut:
    if opts.fqn and (x.__module__ != BUILTINS_MODULE or opts.fq_builtins):
        yield x.__module__
        yield FQN_SEP
    yield x.__qualname__


@Formatter
def fmt_type_value(opts: FmtOpts, x: object) -> FmtOut:
    yield fmt_type.with_opts(opts)(type(x))
    yield ": "
    yield fmt.with_opts(opts)(x)


@Formatter
def fmt_type_hint(opts: FmtOpts, x: Any) -> FmtOut:
    if x is Ellipsis:
        yield "..."
        return

    if x is types.NoneType:
        yield "None"
        return

    if isinstance(x, ForwardRef):
        yield x.__forward_arg__
        return

    if isinstance(x, TypeVar):
        # NOTE  Just gonna punt on this for now... for some reason the way
        #       Python handles generics just manages to frustrate and confuse
        #       me...
        yield repr(x)
        return

    origin = get_origin(x)
    args = get_args(x)

    if args == ():
        if isclass(origin):
            yield fmt_type.with_opts(opts)(origin)
        elif isclass(x):
            yield fmt_type.with_opts(opts)(x)
        else:
            warn("expected typing|origin with no args to be type")
            warn(f"received typing {x!r} with origin {origin!r}")
            yield repr(origin or x)
        return

    if origin is Union or origin is Literal:
        yield " | ".join(fmt_type_hint.with_opts(opts)(arg) for arg in args)
        return

    if origin is dict:
        yield "{"
        yield fmt_type_hint.with_opts(opts)(args[0])
        yield ": "
        yield fmt_type_hint.with_opts(opts)(args[1])
        yield "}"
        if len(args) > 2:
            warn(f"`dict` typing has more than 2 args: {args!r}")
        return

    if origin is list:
        yield fmt_type_hint.with_opts(opts)(args[0])
        yield "[]"
        return

    if origin is tuple:
        yield "("
        yield ", ".join(fmt_type_hint.with_opts(opts)(arg) for arg in args)
        yield ")"
        return

    if origin is set:
        yield "{"
        yield ", ".join(fmt_type_hint.with_opts(opts)(arg) for arg in args)
        yield "}"
        return

    if origin is Callable:
        yield "("
        yield ", ".join(fmt_type_hint.with_opts(opts)(arg) for arg in args[0])
        yield ") -> "
        yield fmt_type_hint.with_opts(opts)(args[1])
        return

    yield repr(x)


@Formatter
def fmt_timedelta(opts: FmtOpts, td: dt.timedelta) -> str:
    """Format a {py:class}`datetime.timedelta` as a compact human-readable
    string with millisecond precision.

    Like {py:meth}`datetime.timedelta.__str__` but without leading zero
    components — the most significant unit has no padding, and sub-components
    are zero-padded to two digits.

    ## Examples

    Sub-second:

    ```python
    >>> fmt_timedelta(dt.timedelta(milliseconds=12))
    '0.012'

    >>> fmt_timedelta(dt.timedelta(milliseconds=500))
    '0.500'

    ```

    Seconds:

    ```python
    >>> fmt_timedelta(dt.timedelta(seconds=5))
    '5.000'

    >>> fmt_timedelta(dt.timedelta(seconds=12, milliseconds=345))
    '12.345'

    ```

    Minutes and above:

    ```python
    >>> fmt_timedelta(dt.timedelta(minutes=5, seconds=30, milliseconds=100))
    '5:30.100'

    >>> fmt_timedelta(
    ...     dt.timedelta(hours=12, minutes=34, seconds=56, milliseconds=789)
    ... )
    '12:34:56.789'

    ```

    Days:

    ```python
    >>> fmt_timedelta(
    ...     dt.timedelta(
    ...         days=1, hours=23, minutes=45, seconds=56, milliseconds=789
    ...     )
    ... )
    '1d 23:45:56.789'

    >>> fmt_timedelta(
    ...     dt.timedelta(
    ...         days=100, hours=5, minutes=3, seconds=2, milliseconds=1
    ...     )
    ... )
    '100d 05:03:02.001'

    ```

    Zero:

    ```python
    >>> fmt_timedelta(dt.timedelta())
    '0.000'

    ```

    Negative:

    ```python
    >>> fmt_timedelta(-dt.timedelta(seconds=1, milliseconds=500))
    '-1.500'

    >>> fmt_timedelta(-dt.timedelta(hours=2, minutes=30))
    '-2:30:00.000'

    ```
    """
    if td < dt.timedelta(0):
        return "-" + fmt_timedelta.with_opts(opts)(-td)

    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    ms = td.microseconds // 1000

    if days:
        s = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    elif hours:
        s = f"{hours}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    elif minutes:
        s = f"{minutes}:{seconds:02d}.{ms:03d}"
    else:
        s = f"{seconds}.{ms:03d}"

    if opts.quote:
        return "`" + s + "`"

    return s


@Formatter
def fmt_datetime(opts: FmtOpts, t: dt.datetime) -> str:
    """
    Format a {py:class}`datetime.datetime` with sub-second directives.

    Wraps {py:meth}`datetime.datetime.strftime` and adds support for:

    -   `%3f` — milliseconds, zero-padded to 3 digits.

    The standard `%f` (microseconds, 6 digits) continues to work as it's handled
    by {py:class}`~datetime.datetime` itself.

    The implementation follows the same strategy Python uses for `%f`:
    pre-process the format string to replace custom directives before delegating
    to {py:meth}`~datetime.datetime.strftime`.

    It also calls {py:meth}`str.strip` on the result, allowing formats like
    `"%Y-%m-%d %H:%M:%S.%3f %Z"` to not produce a trailing space when used with
    naive {py:class}`~datetime.datetime` instances.

    Examples
    --------------------------------------------------------------------------

    We'll be demonstrating on the {py:class}`~datetime.datetime` `t`, which we
    set to the _naive_ (without timezone) moment of `March 14, 2026` at
    `14:23.123456` — that's `2:23PM` at `123,456` microseconds past the
    minute-mark.

        >>> import datetime as dt

        >>> t = dt.datetime(2026, 3, 10, 14, 23, 45, 123_456)
        >>> t.isoformat()
        '2026-03-10T14:23:45.123456'

    Default format:

        >>> fmt_datetime(t)
        '2026-03-10 14:23:45.123'

    Extract just the milliseconds:

        >>> fmt_datetime.with_opts(dt_fmt="%3f ms")(t)
        '123 ms'

    Mixed with standard directives:

        >>> fmt_datetime.with_opts(dt_fmt="%H:%M:%S.%3f")(t)
        '14:23:45.123'

    Standard ``%f`` (microseconds) still works:

        >>> fmt_datetime.with_opts(dt_fmt="%H:%M:%S.%f")(t)
        '14:23:45.123456'

    No custom directives — passes through to
    {py:meth}`~datetime.datetime.strftime`:

        >>> fmt_datetime.with_opts(dt_fmt="%X")(t)
        '14:23:45'

    With timezone:

        >>> fmt_datetime(
        ...     dt.datetime(2026, 3, 10, 14, 23, 45, 123_456, dt.timezone.utc)
        ... )
        '2026-03-10 14:23:45.123 UTC'

        >>> fmt_datetime(
        ...     dt.datetime(2026, 3, 10, 14, 23, 45, 123_456, dt.timezone.utc)
        ... )
        '2026-03-10 14:23:45.123 UTC'

    """
    fmt = opts.dt_fmt
    if "%3f" in fmt:
        fmt = fmt.replace("%3f", f"{t.microsecond // 1000:03d}")
    return t.strftime(fmt).strip()


@Formatter
def fmt_date(opts: FmtOpts, d: dt.date) -> str:
    """
    Format a {py:class}`datetime.date`.

    Uses {py:attr}`FmtOpts.d_fmt` as the format string, defaulting to
    ISO 8601 (``%Y-%m-%d``).

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_date(dt.date(2026, 3, 10))
    '2026-03-10'

    >>> fmt_date.with_opts(d_fmt="%m/%d/%Y")(dt.date(2026, 3, 10))
    '03/10/2026'

    >>> fmt_date.with_opts(d_fmt="%B %d, %Y")(dt.date(2026, 12, 25))
    'December 25, 2026'

    ```
    """
    return d.strftime(opts.d_fmt).strip()


@Formatter
def fmt_time(opts: FmtOpts, t: dt.time) -> str:
    """
    Format a {py:class}`datetime.time` with sub-second directives.

    Uses {py:attr}`FmtOpts.t_fmt` as the format string, defaulting to
    `%H:%M:%S.%3f`. Supports the `%3f` directive for milliseconds, same
    as {py:func}`fmt_datetime`.

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_time(dt.time(14, 23, 45, 123_456))
    '14:23:45.123'

    >>> fmt_time.with_opts(t_fmt="%I:%M %p")(dt.time(14, 23, 45))
    '02:23 PM'

    >>> fmt_time(dt.time())
    '00:00:00.000'

    ```

    """
    fmt = opts.t_fmt
    if "%3f" in fmt:
        fmt = fmt.replace("%3f", f"{t.microsecond // 1000:03d}")
    return t.strftime(fmt).strip()


# Helpers
# ============================================================================


def is_typing(x: Any) -> bool:
    """
    Check if a value is a typing construct (generic, type alias, etc.).

    ## Parameters

    -   `x`: The value to check.

    ## Returns

    {py:data}`True` if `x` appears to be from the `typing` module.
    """
    return bool(
        get_origin(x) or get_args(x) or type(x).__module__ == TYPING_MODULE
    )


def is_builtins(x: object) -> bool:
    if isclass(x):
        return x.__module__ == BUILTINS_MODULE
    return is_builtins(type(x))


if os.environ.get("TESTING"):
    from splatlog._testing import get_formatter_docstrings

    __test__ = get_formatter_docstrings(__name__)
