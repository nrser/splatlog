from collections.abc import Callable
from inspect import isclass, isroutine
import os
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

from .writer import FmtWriter
from .formatter import Formatter, formatter
from .opts import FmtOpts

__all__ = [
    "FmtWriter",
    "Formatter",
    "FmtOpts",
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


@formatter
def fmt(f: FmtWriter, x: object) -> None:
    if is_typing(x):
        return fmt_type_hint.into(f, x)

    if isinstance(x, type):
        return fmt_type.into(f, x)

    if isroutine(x):
        return fmt_routine.into(f, x)

    f.write_obj(x)


@formatter
def fmt_name(f: FmtWriter, named: object):
    name = (
        getattr(named, "__qualname__", None)
        or getattr(named, "__name__", None)
        or str(named)
    )

    if (
        f.opts.fqn
        and (mod_name := get_module_name(named))
        and (mod_name != BUILTINS_MODULE or f.opts.fq_builtins)
    ):
        f.write(mod_name)
        f.write(FQN_SEP)
    f.write(name)


@formatter
def fmt_routine(f: FmtWriter, x: Routine) -> None:
    """
    Format a function or method for display.

    Lambdas are shown as `λ()`. Named functions include their qualified name
    followed by `()`.

    ## Parameters

    -   `opts`: Formatting options.
    -   `named`: The function to format.

    ## Returns

    A formatted string like `module.func()` or `λ()`.

    ## Examples

    ```python
    >>> import datetime

    >>> fmt_routine(datetime.date.today)
    'datetime.date.today()'

    >>> fmt_routine.with_opts(fqn=False)(datetime.date.today)
    'date.today()'

    >>> fmt_routine(lambda x, y: x + y)
    'λ()'

    >>> def f():
    ...     def g():
    ...         pass
    ...     return g
    >>> fmt_routine(f())
    'splatlog.lib.fmt.f.<locals>.g()'

    ```
    """
    if x.__name__ == LAMBDA_NAME:
        f.write("λ()")
        return

    fmt_name.into(f, x)
    f.write("()")


@formatter
def fmt_type(f: FmtWriter, x: type) -> None:
    if f.opts.fqn and (x.__module__ != BUILTINS_MODULE or f.opts.fq_builtins):
        f.write(x.__module__)
        f.write(FQN_SEP)
    f.write(x.__qualname__)


@formatter
def fmt_type_value(f: FmtWriter, x: object) -> None:
    with f.concat():
        fmt_type.into(f, type(x))
        f.write(":")
    f.space()
    fmt.into(f, x)


@formatter
def fmt_type_hint(f: FmtWriter, x: Any) -> None:
    if x is Ellipsis:
        f.write("...")
        return

    if x is types.NoneType:
        f.write("None")
        return

    if isinstance(x, ForwardRef):
        f.write(x.__forward_arg__)
        return

    if isinstance(x, TypeVar):
        # NOTE  Just gonna punt on this for now... for some reason the way
        #       Python handles generics just manages to frustrate and confuse
        #       me...
        f.write_obj(x)
        return

    origin = get_origin(x)
    args = get_args(x)

    if args == ():
        if isclass(origin):
            return fmt_type.into(f, origin)
        elif isclass(x):
            return fmt_type.into(f, x)
        else:
            # Unexpected!?!
            warn("expected typing|origin with no args to be type")
            warn("received typing {t!r} with origin {origin!r}")
            return f.write_obj(origin or x)

    if origin is Union or origin is Literal:
        with f.join("|", space="opt"):
            for arg in args:
                fmt_type_hint.into(f, arg)
        return

    if origin is dict:
        f.write("{")
        with f.concat():
            fmt_type_hint.into(f, args[0])
            f.write(":")
        f.space()
        fmt_type_hint.into(f, args[1])
        f.write("}")

        if len(args) > 2:
            warn(f"`dict` typing has more than 2 args: {args!r}")

        return

    if origin is list:
        with f.concat():
            fmt_type_hint.into(f, args[0])
            f.write("[]")
        return

    if origin is tuple:
        f.write("(")
        with f.join(",", space=("never", "req")):
            for arg in args:
                fmt_type_hint.into(f, arg)
        f.write(")")
        return

    if origin is set:
        f.write("{")
        with f.join(",", space=("never", "req")):
            for arg in args:
                fmt_type_hint.into(f, arg)
        f.write("}")
        return

    if origin is Callable:
        f.write("(")
        with f.join(",", space=("never", "req")):
            for arg in args[0]:
                fmt_type_hint.into(f, arg)
        f.write(")")
        f.space()
        f.write("->")
        f.space()
        fmt_type_hint.into(f, args[1])
        return

    f.write_obj(x)


# Helpers
# ============================================================================


def get_module_name(x: object) -> str | None:
    if mod_name := getattr(x, "__module__", None):
        return mod_name

    if self := getattr(x, "__self__", None):
        return get_module_name(self)

    return None


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


# Testing
# ============================================================================

if os.environ.get("TESTING"):
    from splatlog._testing import get_formatter_docstrings

    __test__ = get_formatter_docstrings(__name__)
