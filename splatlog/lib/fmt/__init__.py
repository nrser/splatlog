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

            >>> from typing import Optional

            >>> fmt(Optional[str])
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

    return opts.fallback(x)


@Formatter
def fmt_routine(f: FmtOpts, x: Routine) -> FmtOut:
    if x.__name__ == LAMBDA_NAME:
        yield "λ()"
    else:
        if f.fqn and (x.__module__ != BUILTINS_MODULE or f.fq_builtins):
            yield x.__module__
            yield FQN_SEP
        else:
            yield x.__qualname__
            yield "()"


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


# def fmt_name(f: FmtOpts, x: Any):
#     name = getattr(x, "__qualname__", None) or getattr(x, "__name__", None)
#     if (
#         f.fqn
#         and (module_name := getattr(x, "__module__", None))
#         and (module_name != BUILTINS_MODULE or f.fq_builtins)
#     ):
#         yield module_name
#         yield FQN_SEP
#     yield name

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
