"""
Text utilities.

:::{warning}
### No cross-package `import` at top-level

This module is considered _foundational_ due to its primary use in formatting
error messages. To avoid circular imports it is prohibited from importing other
{py:mod}`splatlog` modules at the top-level.

Imports of other {py:mod}`splatlog` modules should be avoided, and placed inside
function or method bodies if they can't be.

:::
"""

from collections.abc import Callable, Iterable, Sequence
from inspect import isclass, isroutine
import sys
import types
from typing import (
    ForwardRef,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
from warnings import warn
import datetime as dt

from splatlog.lib.types import (
    BUILTINS_MODULE_NAME,
    TYPING_MODULE_NAME,
    is_typing,
)
from .decorator import formatter, FmtResult
from .opts import FmtOpts

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

LAMBDA_NAME = (lambda x: x).__name__
"""
The `__name__` attribute value for lambda functions (`"<lambda>"`).

The name is `'<lambda>'`, we get it from `(lambda x: x).__name__`.
"""

FQN_SEP = "."
"""
Separator for fully-qualified names, for example the '.' in 'typing.Any'.
"""


@formatter()
def fmt(x: object, opts: FmtOpts) -> FmtResult:
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

            >>> from typing import Optional
            >>> from collections.abc import Collection

            >>> fmt(str)
            'str'

            >>> fmt(Collection)
            'collections.abc.Collection'

            >>> fmt(str | None)
            'str?'

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
            '0.012s'

            >>> fmt_timedelta(
            ...     dt.timedelta(days=1, hours=23, minutes=45, seconds=56)
            ... )
            '1d 23:45:56.000'

        {py:func}`fmt_timedelta` has more information and examples.
    """
    if isinstance(x, type):
        return fmt_type(x, opts)

    if is_typing(x):
        return fmt_type_hint(x, opts)

    if isroutine(x):
        return fmt_routine(x, opts)

    if isinstance(x, dt.datetime):
        return fmt_datetime(x, opts)

    if isinstance(x, dt.date):
        return fmt_date(x, opts)

    if isinstance(x, dt.time):
        return fmt_time(x, opts)

    if isinstance(x, dt.timedelta):
        return fmt_timedelta(x, opts)

    if isinstance(x, str) and opts.s_raw:
        return x

    return opts.fallback(x)


@formatter
def fmt_name(x: object, opts: FmtOpts) -> str:
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
        and (module_name != BUILTINS_MODULE_NAME or opts.fq_builtins)
        and (module_name != TYPING_MODULE_NAME or opts.fq_typing)
    ):
        return f"{module_name}.{name}"
    return name


@formatter
def fmt_routine(x: Routine, opts: FmtOpts) -> FmtResult:
    """
    Format a function or method for display.

    Lambdas are shown as `λ()`. Named functions include their qualified name
    followed by `()`.

    ## Parameters

    -   `fn`: The function to format.
    -   `opts`: Formatting options.

    ## Returns

    A formatted string like `module.func()` or `λ()`.

    ## Examples

    ```pycon
    >>> import splatlog

    >>> fmt_routine(splatlog.setup)
    'splatlog.setup()'

    >>> fmt_routine(splatlog.setup, fqn=False)
    'setup()'

    >>> fmt_routine(lambda x, y: x + y)
    'λ()'

    >>> def f():
    ...     def g():
    ...         pass
    ...     return g
    >>> fmt_routine(f())
    'splatlog.lib.text.formatting.formatters.f.<locals>.g()'

    ```
    """
    if x.__name__ == LAMBDA_NAME:
        return "λ()"

    if name := fmt_name(x, opts):
        return name + "()"

    return opts.fallback(x)


@formatter()
def fmt_type(x: type, opts: FmtOpts) -> FmtResult:
    """
    Format a type for display.

    ## Parameters

    -   `x`: The type to format.
    -   `opts`: Formatting options.

    ## Returns

    The type's qualified name, with or without module prefix per options.

    ## Examples

    ```pycon
    >>> from collections.abc import Collection
    >>> fmt_type(Collection)
    'collections.abc.Collection'

    >>> fmt_type(Collection, fqn=False)
    'Collection'

    >>> fmt_type(Collection, FmtOpts(fqn=False))
    'Collection'

    >>> fmt_type(Collection, FmtOpts(fqn=False), fqn=True)
    'collections.abc.Collection'

    ```
    """
    return fmt_name(x, opts)


@formatter
def fmt_type_of(x: object, opts: FmtOpts) -> str:
    """
    Format the type of a value.

    Shorthand for `fmt_type(type(x), opts)`.

    ## Parameters

    -   `x`: The value whose type to format.
    -   `opts`: Formatting options.

    ## Returns

    The formatted type name.
    """
    return fmt_type(type(x), opts)


@formatter(auto_quote=False)
def fmt_type_value(x: object, opts: FmtOpts) -> FmtResult:
    """
    Format the type of a value.

    Shorthand for `fmt_type(type(x), opts)`.

    ## Parameters

    -   `x`: The value whose type to format.
    -   `opts`: Formatting options.

    ## Returns

    The formatted type name.

    Examples
    --------------------------------------------------------------------------

        >>> fmt_type_value(123)
        'int: 123'

        >>> fmt_type_value(123, quote=True)
        '`int`: `123`'

    """
    yield fmt_type(type(x), opts)
    yield ": "
    yield fmt(x, opts)


@formatter
def fmt_type_hint(x: object, opts: FmtOpts) -> FmtResult:
    """
    Format a type hint for human-readable display.

    Produces concise representations:

    -   `str?` for `str | None` and `Optional[str]`
    -   `int[]` for `list[int]`
    -   `{str: int}` for `dict[str, int]`

    ## Parameters

    -   `t`: The type hint to format.
    -   `opts`: Formatting options.
    -   `nested`: Whether this is a nested type (used internally for
        parenthesization).

    ## Returns

    A formatted string representation of the type hint.

    Examples
    ------------------------------------------------------------------------

    -   **Optional types** — unions of {py:data}`None` with a _single_ other
        type are abbreviated with a `?` suffix:

            >>> fmt_type_hint(int | None)
            'int?'

            >>> fmt_type_hint(None | int)
            'int?'

        This includes construction using {py:obj}`typing.Optional`:

            >>> from typing import Optional

            >>> fmt_type_hint(Optional[int])
            'int?'

        We used to exclude {py:obj}`typing.Literal` from this rule, but on
        revisit favored consistency and simplicity:

            >>> from typing import Literal

            >>> fmt_type_hint(Literal["some"] | None)
            "'some'?"

            >>> fmt_type_hint(Optional[Literal[123]])
            '123?'

        You can disable this feature by setting the
        {py:attr}`~splatlog.lib.fmt.opts.FmtOpts.short_optional` option to
        {py:data}`False`:

            >>> fmt_type_hint(int | None, short_optional=False)
            'int | None'

            >>> fmt_type_hint(Optional[Literal["some"]], short_optional=False)
            "'some' | None"

    """
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
        yield opts.fallback(x)
        return

    origin = get_origin(x)
    args = get_args(x)

    if args == ():
        if isclass(origin):
            yield fmt_type(origin, opts)
        elif isclass(x):
            yield fmt_type(x, opts)
        else:
            yield repr(origin or x)
        return

    if origin is Union or origin is types.UnionType:
        if opts.short_optional and len(args) == 2:
            match [arg for arg in args if arg is not types.NoneType]:
                case [arg]:
                    yield fmt_type_hint(arg, opts)
                    yield "?"
                    return

        yield " | ".join(fmt_type_hint(arg, opts) for arg in args)
        return

    if origin is Literal:
        yield " | ".join(fmt_type_hint(arg, opts) for arg in args)
        return

    if origin is dict:
        yield "{"
        yield fmt_type_hint(args[0], opts)
        yield ": "
        yield fmt_type_hint(args[1], opts)
        yield "}"
        if len(args) > 2:
            warn(f"`dict` typing has more than 2 args: {args!r}")
        return

    if origin is list:
        yield fmt_type_hint(args[0], opts)
        yield "[]"
        return

    if origin is tuple:
        yield "("
        yield ", ".join(fmt_type_hint(arg, opts) for arg in args)
        yield ")"
        return

    if origin is set:
        yield "{"
        yield ", ".join(fmt_type_hint(arg, opts) for arg in args)
        yield "}"
        return

    if origin is Callable:
        yield "("
        yield ", ".join(fmt_type_hint(arg, opts) for arg in args[0])
        yield ") -> "
        yield fmt_type_hint(args[1], opts)
        return

    yield repr(x)


@formatter
def fmt_range(rng: range, opts: FmtOpts) -> str:
    """
    Format a range for concise display.

    Short ranges (≤3 elements) are shown in full. Longer ranges show the
    first elements and an ellipsis.

    ## Parameters

    -   `rng`: The range to format.

    ## Returns

    A string like `[0, 1, 2]` or `[0, 1, ..., 100]`.
    """
    length = len(rng)
    if length <= 3:
        return str(list(rng))
    if rng.stop == sys.maxsize:
        if rng.step == 1:
            return f"[{rng[0]}, ...]"
        return f"[{rng[0]}, {rng[1]}, ...]"
    return f"[{rng[0]}, {rng[1]}, ..., {rng.stop}]"


# Let the `items` quote individually as they hit the next formatter.
@formatter(auto_quote=False)
def fmt_list(items: Iterable, opts: FmtOpts) -> str:
    """
    Format a list of `items`. By default this is comma-separated, like
    `A, B, C`.

    Examples
    --------------------------------------------------------------------------

        >>> fmt_list([1, 2, 3], quote=True, ls_conj="and")
        '`1`, `2`, and `3`'

    """
    if opts.ls_conj is None:
        return f"{opts.ls_sep} ".join(fmt(item, opts) for item in items)

    s = ""
    sep_sp = f"{opts.ls_sep} "
    ls = list(items)
    i_end = len(ls) - 1
    for i, item in enumerate(ls):
        if i == i_end:
            if opts.ls_ox:
                s += opts.ls_sep
            s += f" {opts.ls_conj} "
        elif i > 0:
            s += sep_sp

        s += fmt(item, opts)

    return s


@formatter
def fmt_seq(seq: Sequence, opts: FmtOpts) -> str:
    """
    Format a sequence, respecting the {py:attr}`FmtOpts.items` limit and
    {py:attr}`FmtOpts.ellipsis` for truncation.

    ## Parameters

    -   `seq`: The sequence to format (list or tuple).
    -   `opts`: Formatting options.

    ## Returns

    A formatted string like `[1, 2, 3]` or `(1, 2, ...)`.

    ## Examples

    ```pycon
    >>> fmt_seq([1, 2, 3])
    '[1, 2, 3]'

    >>> fmt_seq((1, 2, 3))
    '(1, 2, 3)'

    >>> fmt_seq([1, 2, 3, 4, 5], items=3)
    '[1, 2, 3, ...]'

    >>> fmt_seq((1, 2, 3, 4, 5), items=2)
    '(1, 2, ...)'

    >>> fmt_seq([1, 2, 3, 4, 5], items=3, ellipsis='…')
    '[1, 2, 3, …]'

    >>> fmt_seq([])
    '[]'

    >>> fmt_seq(())
    '()'

    >>> fmt_seq([1, 2], items=5)
    '[1, 2]'

    ```
    """
    is_tuple = isinstance(seq, tuple)
    open_bracket, close_bracket = ("(", ")") if is_tuple else ("[", "]")

    if opts.items is not None and len(seq) > opts.items:
        items = [fmt(item, opts) for item in seq[: opts.items]]
        items.append(opts.ellipsis)
    else:
        items = [fmt(item, opts) for item in seq]

    return open_bracket + ", ".join(items) + close_bracket


@formatter
def fmt_timedelta(td: dt.timedelta, opts: FmtOpts) -> str:
    """Format a {py:class}`datetime.timedelta` as a compact human-readable
    string with millisecond precision.

    Like {py:meth}`datetime.timedelta.__str__` but without leading zero
    components — the most significant unit has no padding, and sub-components
    are zero-padded to two digits.

    ## Examples

    Sub-second — the default {py:attr}`splatlog.lib.text.FmtOpts.td_base`
    is seconds (`"s"`), so milliseconds will appear as fraction of a second:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(milliseconds=12))
    '0.012s'

    >>> fmt_timedelta(dt.timedelta(milliseconds=500))
    '0.500s'

    ```

    {py:attr}`~splatlog.lib.text.FmtOpts.td_base` can be set to milliseconds
    (`"ms"`) through the options.
    This is basically for when you're working with intervals you expect to
    consistently be in the millisecond range, such as RPC requests. Once the
    number of milliseconds is over `1,000` the format will still switch to `s`.

    ```pycon
    >>> fmt_timedelta(dt.timedelta(milliseconds=12), td_base="ms")
    '12ms'

    >>> fmt_timedelta(dt.timedelta(milliseconds=500), td_base="ms")
    '500ms'

    >>> fmt_timedelta(dt.timedelta(milliseconds=2_500), td_base="ms")
    '2.500s'

    ```

    Sub-minute seconds are displayed as the integer with an `s` unit, and
    fractional milliseconds if present.

    ```pycon
    >>> fmt_timedelta(dt.timedelta(seconds=5))
    '5s'

    >>> fmt_timedelta(dt.timedelta(seconds=12, milliseconds=345))
    '12.345s'

    ```

    Lowering the base unit has no effect when large units are present:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(seconds=1, milliseconds=12), td_base="ms")
    '1.012s'

    >>> fmt_timedelta(dt.timedelta(seconds=1, milliseconds=500), td_base="ms")
    '1.500s'

    ```

    When there are minutes and hour the `HH:MM:SS` format is used, including
    leading zeros, without any unit designation:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(minutes=5, seconds=30))
    '00:05:30'

    >>> fmt_timedelta(dt.timedelta(minutes=5, seconds=30, milliseconds=10))
    '00:05:30.010'

    >>> fmt_timedelta(
    ...     dt.timedelta(hours=12, minutes=34, seconds=56, milliseconds=789)
    ... )
    '12:34:56.789'

    ```

    You can force this format by setting
    {py:attr}`~splatlog.lib.text.FmtOpts.td_base` to `"HH:MM:SS"`:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(milliseconds=12), td_base="HH:MM:SS")
    '00:00:00.012'

    >>> fmt_timedelta(
    ...     dt.timedelta(seconds=1, milliseconds=12),
    ...     td_base="HH:MM:SS",
    ... )
    '00:00:01.012'

    ```

    Days continue with the `HH:MM:SS` format, with fractional milliseconds when
    hours, minutes, seconds or milliseconds are present. Basically the same as
    the built-in {py:meth}`datetime.timedelta.__str__`, but using the shorter
    `d` unit and defaulting to millisecond precision.

    ```pycon
    >>> fmt_timedelta(dt.timedelta(days=1))
    '1d'

    >>> fmt_timedelta(dt.timedelta(days=1, seconds=1))
    '1d 00:00:01'

    >>> fmt_timedelta(dt.timedelta(days=7, minutes=5, seconds=30))
    '7d 00:05:30'

    >>> fmt_timedelta(dt.timedelta(days=123, milliseconds=500))
    '123d 00:00:00.500'

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

    ```pycon
    >>> fmt_timedelta(dt.timedelta())
    '0s'

    >>> fmt_timedelta(dt.timedelta(), td_base="ms")
    '0ms'

    >>> fmt_timedelta(dt.timedelta(), td_base="HH:MM:SS")
    '00:00:00'

    ```

    Negative:

    ```pycon
    >>> fmt_timedelta(-dt.timedelta(seconds=1, milliseconds=500))
    '-1.500'

    >>> fmt_timedelta(-dt.timedelta(hours=2, minutes=30))
    '-2:30:00.000'

    ```
    """
    if td < dt.timedelta(0):
        pos = fmt_timedelta(-td, opts)
        if pos.endswith("s"):
            return "-" + pos[:-1]
        return "-" + pos

    base = opts.td_base
    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    ms = td.microseconds // 1000

    def clock_hms(
        h: int,
        m: int,
        s: int,
        sub_ms: int,
        *,
        always_ms: bool = False,
        pad_hours: bool = False,
    ) -> str:
        """HH:MM:SS[.mmm].

        When ``pad_hours`` is false (standalone clock): hours unpadded if
        ``h > 0``, else ``00``. When true (after ``Nd``): hours zero-padded.

        When ``always_ms`` is true, emit a millisecond field even if zero
        (used when the leading clock unit is hours, excluding ``Nd`` forms).
        """
        if pad_hours:
            out = f"{h:02d}:{m:02d}:{s:02d}"
        elif h > 0:
            out = f"{h}:{m:02d}:{s:02d}"
        else:
            out = f"00:{m:02d}:{s:02d}"
        if sub_ms or always_ms:
            out += f".{sub_ms:03d}"
        return out

    def day_suffix(h: int, m: int, s: int, sub_ms: int) -> str:
        if h == 0 and m == 0 and s == 0 and sub_ms == 0:
            return ""
        always_ms = h > 0 and sub_ms == 0
        return " " + clock_hms(
            h, m, s, sub_ms, always_ms=always_ms, pad_hours=True
        )

    # Zero
    if td == dt.timedelta(0):
        if base == "ms":
            s = "0ms"
        elif base == "HH:MM:SS":
            s = "00:00:00"
        else:
            s = "0s"
    # Forced wall-clock (sub-day only in doctests; multi-day uses day + remainder)
    elif base == "HH:MM:SS":
        if days == 0:
            s = clock_hms(
                hours,
                minutes,
                seconds,
                ms,
                always_ms=(hours > 0 and ms == 0),
            )
        else:
            s = f"{days}d" + day_suffix(hours, minutes, seconds, ms)
    elif days > 0:
        s = f"{days}d" + day_suffix(hours, minutes, seconds, ms)
    elif hours > 0 or minutes > 0:
        s = clock_hms(
            hours,
            minutes,
            seconds,
            ms,
            always_ms=(hours > 0 and ms == 0),
        )
    elif base == "ms":
        total_ms = seconds * 1000 + ms
        if seconds == 0 and total_ms < 1000:
            s = f"{total_ms}ms"
        elif ms:
            s = f"{seconds}.{ms:03d}s"
        else:
            s = f"{seconds}s"
    else:
        # td_base == "s"
        if ms:
            s = f"{seconds}.{ms:03d}s"
        else:
            s = f"{seconds}s"

    if opts.quote:
        return "`" + s + "`"

    return s


@formatter
def fmt_datetime(t: dt.datetime, opts: FmtOpts) -> str:
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

        >>> fmt_datetime(t, dt_fmt="%3f ms")
        '123 ms'

    Mixed with standard directives:

        >>> fmt_datetime(t, dt_fmt="%H:%M:%S.%3f")
        '14:23:45.123'

    Standard ``%f`` (microseconds) still works:

        >>> fmt_datetime(t, dt_fmt="%H:%M:%S.%f")
        '14:23:45.123456'

    No custom directives — passes through to
    {py:meth}`~datetime.datetime.strftime`:

        >>> fmt_datetime(t, dt_fmt="%X")
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


@formatter
def fmt_date(d: dt.date, opts: FmtOpts) -> str:
    """
    Format a {py:class}`datetime.date`.

    Uses {py:attr}`FmtOpts.date_fmt` as the format string, defaulting to
    ISO 8601 (``%Y-%m-%d``).

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_date(dt.date(2026, 3, 10))
    '2026-03-10'

    >>> fmt_date(dt.date(2026, 3, 10), date_fmt="%m/%d/%Y")
    '03/10/2026'

    >>> fmt_date(dt.date(2026, 12, 25), date_fmt="%B %d, %Y")
    'December 25, 2026'

    ```
    """
    return d.strftime(opts.date_fmt).strip()


@formatter
def fmt_time(t: dt.time, opts: FmtOpts) -> str:
    """
    Format a {py:class}`datetime.time` with sub-second directives.

    Uses {py:attr}`FmtOpts.time_fmt` as the format string, defaulting to
    `%H:%M:%S.%3f`. Supports the `%3f` directive for milliseconds, same
    as {py:func}`fmt_datetime`.

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_time(dt.time(14, 23, 45, 123_456))
    '14:23:45.123'

    >>> fmt_time(dt.time(14, 23, 45), time_fmt="%I:%M %p")
    '02:23 PM'

    >>> fmt_time(dt.time())
    '00:00:00.000'

    ```

    """
    fmt = opts.time_fmt
    if "%3f" in fmt:
        fmt = fmt.replace("%3f", f"{t.microsecond // 1000:03d}")
    return t.strftime(fmt).strip()
