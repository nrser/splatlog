"""
Text formatting implementations, including {py:func}`fmt` entry point.
"""

from collections.abc import Callable, Iterable
from inspect import isclass, isroutine
import sys
from traceback import format_exception
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
    is_number,
    is_typing,
    Routine,
)
from .formatter import formatter, FmtResult, FmtOpts
from .number import fmt_number
from .datetime import fmt_datetime, fmt_date, fmt_time
from .timedelta import fmt_timedelta


# Constants
# ============================================================================

LAMBDA_NAME = (lambda x: x).__name__
"""
The `__name__` attribute value for lambda functions (`"<lambda>"`).

The name is `'<lambda>'`, we get it from `(lambda x: x).__name__`.
"""

FQN_SEP = "."
"""
Separator for fully-qualified names, for example the '.' in 'typing.Any'.
"""

# Dispatcher
# ============================================================================
#
# Inspects the value and dispatches to the appropriate formatter function.


@formatter(auto_quote=False)
def fmt(x: object, opts: FmtOpts) -> FmtResult:
    """
    Format a value for concise, human-readable output.

    Dispatches to specialized formatters based on the value's type:
    typing constructs, types, and routines each have dedicated formatters.

    ## Parameters

    -   `x`: The value to format.
    -   `opts`: Formatting options.

    ## Returns

    A formatted string representation.

    ## Examples

    -   **Types & Type Hints** — Formats {py:class}`type` by qualified name, and
        {py:mod}`typing` hints with concise shorthands, clearly distinguished by
        enclosing angle brackets:

        ```pycon
        >>> from typing import Optional, Callable, Literal
        >>> from collections.abc import Collection

        >>> fmt(str)
        '<str>'

        >>> fmt(Collection)
        '<collections.abc.Collection>'

        >>> fmt(str | None)
        '<str?>'

        >>> fmt(list[int])
        '<int[]>'

        >>> fmt(dict[str, int])
        '<{str: int}>'

        >>> fmt(Literal["A", "B", "C"])
        "<'A' | 'B' | 'C'>"

        >>> fmt(Callable[[int, int], str])
        '<(int, int) -> str>'

        ```

        Additionally, the formatted runtime {py:class}`type` can be added as a
        prefix when formatting a value by setting the {py:attr}`FmtOpts.type`
        option:

        ```pycon
        >>> fmt(123, t=True)
        '<int> 123'

        >>> fmt({"x": 123, "y": 456}, t=True)
        "<dict> {'x': 123, 'y': 456}"

        ```

        See {py:func}`fmt_type` and {py:func}`fmt_type_hint` for options and
        additional examples.

    -   **Functions & Methods** — Uses {py:func}`inspect.isroutine` to detect
        functions and methods and format them clearly and concisely:

        ```pycon
        >>> fmt(int.__add__)
        'int.__add__()'

        ```

        Compare to what {py:class}`str` (and {py:func}`repr`) will give you:

        ```pycon
        >>> str(int.__add__)
        "<slot wrapper '__add__' of 'int' objects>"

        ```

        See {py:func}`fmt_routine` for more info.

    -   **Numbers** — Formats {py:class}`int`, {py:class}`float`,
        {py:class}`decimal.Decimal`, {py:class}`fractions.Fraction`, and
        {py:class}`complex` via {py:meth}`str.format` templates. By default
        {py:class}`int` is grouped without a decimal point and
        {py:class}`float`/{py:class}`decimal.Decimal` use grouped "general"
        format:

        ```pycon
        >>> fmt(1234567)
        '1,234,567'

        >>> fmt(1234.5678)
        '1,234.57'

        ```

        The {py:attr}`FmtOpts.i_fmt` and {py:attr}`FmtOpts.f_fmt` options
        (plus {py:attr}`FmtOpts.dec_fmt`, {py:attr}`FmtOpts.Q_fmt`, and
        {py:attr}`FmtOpts.C_fmt` for
        {py:class}`~decimal.Decimal`/{py:class}`~fractions.Fraction`/{py:class}`complex`)
        take any f-string spec, so grouping, precision, currency, and more are
        expressible inline:

        ```pycon
        >>> fmt(1234567.5, f_fmt="${:,.2f}")
        '$1,234,567.50'

        ```

        See {py:func}`fmt_number` for more.

    -   **Dates & Times** — Formats {py:class}`datetime.datetime` using the
        {py:attr}`FmtOpts.dt_fmt` option:

        ```pycon
        >>> from datetime import datetime, date, time, timedelta

        >>> fmt(datetime(2026, 3, 10, 14, 23, 45, 123_456))
        '2026-03-10 14:23:45.123'

        ```

        Check out {py:func}`fmt_datetime` for details.

        Also handles {py:class}`datetime.date` and {py:class}`datetime.time`:

        ```pycon
        >>> fmt(date(2026, 3, 10))
        '2026-03-10'

        >>> fmt(time(14, 23, 45, 123_456))
        '14:23:45.123'

        ```

        See {py:func}`fmt_date` and {py:func}`fmt_time` for more.

        Produces a concise, readable rendering of {py:class}`datetime.timedelta`
        as well:

        ```pycon
        >>> fmt(timedelta(milliseconds=12))
        '00:00:00.012'

        >>> fmt(timedelta(days=1, hours=23, minutes=45, seconds=56))
        '1d 23:45:56'

        ```

        {py:func}`fmt_timedelta` has more information and examples.
    """
    # If asked to include the type handoff to `fmt_type_value`
    if opts.t:
        return fmt_type_value(x, opts.replace(t=False))

    # If `x` is a `str` and the option is set to pass-through raw strings simply
    # return it
    if isinstance(x, str) and opts.s_raw:
        return x

    if isinstance(x, type):
        return fmt_type(x, opts)

    if is_typing(x):
        return fmt_type_hint(x, opts)

    if isroutine(x):
        return fmt_routine(x, opts)

    # `bool` is an `int` subclass we want left as `True`/`False` by the
    # fallback; `is_number` excludes it from the numeric dispatch.
    if is_number(x):
        return fmt_number(x, opts)

    if isinstance(x, dt.datetime):
        return fmt_datetime(x, opts)

    if isinstance(x, dt.date):
        return fmt_date(x, opts)

    if isinstance(x, dt.time):
        return fmt_time(x, opts)

    if isinstance(x, dt.timedelta):
        return fmt_timedelta(x, opts)

    if isinstance(x, Exception):
        return fmt_err(x, opts)

    return opts.fallback(x, opts)


# Formatters
# ============================================================================


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
    'splatlog.lib.text.fmt.f.<locals>.g()'

    ```
    """
    if x.__name__ == LAMBDA_NAME:
        return "λ()"

    if name := fmt_name(x, opts):
        return name + "()"

    return opts.fallback(x, opts)


@formatter()
def fmt_type(x: type, opts: FmtOpts) -> FmtResult:
    """
    Format a {py:class}`type` for display.

    Renders the type name with {py:func}`fmt_name`, surrounded by angle brackets
    (configurable) to distinguish it.

    ## Parameters

    -   `x`: The type to format.
    -   `opts`: Formatting options.

    ## Returns

    The type's qualified name, with or without module prefix per options.

    ## Examples

    ```pycon
    >>> from collections.abc import Collection
    >>> fmt_type(Collection)
    '<collections.abc.Collection>'

    >>> fmt_type(Collection, fqn=False)
    '<Collection>'

    >>> fmt_type(Collection, FmtOpts(fqn=False))
    '<Collection>'

    >>> fmt_type(Collection, FmtOpts(fqn=False), fqn=True)
    '<collections.abc.Collection>'

    ```
    """
    yield opts.t_start
    yield fmt_name(x, opts)
    yield opts.t_end


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

    Shorthand for `fmt_type(type(x), opts)`{l=py}.

    ## Parameters

    -   `x`: The value whose type to format.
    -   `opts`: Formatting options.

    ## Returns

    The formatted type name.

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> fmt_type_value(123)
    '<int> 123'

    >>> fmt_type_value(123, q=True)
    '`<int>` `123`'

    ```
    """
    yield fmt_type(type(x), opts)
    s_val = fmt(x, opts.replace(pad="s"))
    if s_val.startswith("\n"):
        yield ":"
    else:
        yield " "
    yield s_val


@formatter
def fmt_type_hint(x: object, opts: FmtOpts) -> FmtResult:
    """
    Format a type hint for human-readable display.

    Produces concise representations:

    -   `str?` for `str | None`{l=py} and `Optional[str]`{l=py}
    -   `int[]` for `list[int]`{l=py}
    -   `{str: int}` for `dict[str, int]`{l=py}

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

        ```pycon
        >>> fmt_type_hint(int | None)
        '<int?>'

        >>> fmt_type_hint(None | int)
        '<int?>'

        ```

        This includes construction using {py:obj}`typing.Optional`:

        ```pycon
        >>> from typing import Optional

        >>> fmt_type_hint(Optional[int])
        '<int?>'

        ```

        We used to exclude {py:obj}`typing.Literal` from this rule, but on
        revisit favored consistency and simplicity:

        ```pycon
        >>> from typing import Literal

        >>> fmt_type_hint(Literal["some"] | None)
        "<'some'?>"

        >>> fmt_type_hint(Optional[Literal[123]])
        '<123?>'

        ```

        You can disable this feature by setting the
        {py:attr}`~splatlog.lib.text.FmtOpts.t_opt_q` option to
        {py:data}`False`:

        ```pycon
        >>> fmt_type_hint(int | None, t_opt_q=False)
        '<int | None>'

        >>> fmt_type_hint(Optional[Literal["some"]], t_opt_q=False)
        "<'some' | None>"

        ```

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
        yield opts.fallback(x, opts)
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

    # Everything below here is a
    inner_opts = opts.replace(t_start="", t_end="")

    if origin is Union or origin is types.UnionType:
        if opts.t_opt_q and len(args) == 2:
            match [arg for arg in args if arg is not types.NoneType]:
                case [arg]:
                    yield opts.t_start
                    yield fmt_type_hint(arg, inner_opts)
                    yield "?"
                    yield opts.t_end
                    return

        # TODO  This is not great for large unions, such as `ToConsoleHandler`.
        #       Ideally we'd line-break like `fmt_pretty_repr` does.
        yield opts.t_start
        yield " | ".join(fmt_type_hint(arg, inner_opts) for arg in args)
        yield opts.t_end
        return

    if origin is Literal:
        yield opts.t_start
        yield " | ".join(fmt_type_hint(arg, inner_opts) for arg in args)
        yield opts.t_end
        return

    if origin is dict:
        yield opts.t_start
        yield "{"
        yield fmt_type_hint(args[0], inner_opts)
        yield ": "
        yield fmt_type_hint(args[1], inner_opts)
        yield "}"
        yield opts.t_end
        if len(args) > 2:
            warn(f"`dict` typing has more than 2 args: {args!r}")
        return

    if origin is list:
        yield opts.t_start
        yield fmt_type_hint(args[0], inner_opts)
        yield "[]"
        yield opts.t_end
        return

    if origin is tuple:
        yield opts.t_start
        yield "("
        yield ", ".join(fmt_type_hint(arg, inner_opts) for arg in args)
        yield ")"
        yield opts.t_end
        return

    if origin is set:
        yield opts.t_start
        yield "{"
        yield ", ".join(fmt_type_hint(arg, inner_opts) for arg in args)
        yield "}"
        yield opts.t_end
        return

    if origin is Callable:
        yield opts.t_start
        yield "("
        yield ", ".join(fmt_type_hint(arg, inner_opts) for arg in args[0])
        yield ") -> "
        yield fmt_type_hint(args[1], inner_opts)
        yield opts.t_end
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

        >>> fmt_list([1, 2, 3], q=True, ls_conj="and")
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


@formatter(auto_quote=False)
def fmt_err(err: Exception, opts: FmtOpts) -> FmtResult:
    t_err = type(err)
    if opts.e_trace and (tb := err.__traceback__):
        yield from format_exception(t_err, err, tb)
    else:
        yield fmt_name(t_err, opts)
        yield ": "
        yield str(err)
        if notes := getattr(err, "__notes__", None):
            yield "\n"
            for note in notes:
                yield note
                yield "\n"
