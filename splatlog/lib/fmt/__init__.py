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

from .writer import FmtWriter
from .func import FmtFunc
from .opts import FmtOpts

__all__ = [
    "FmtWriter",
    "FmtFunc",
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


@FmtFunc
def fmt(f: FmtWriter, x: object) -> None:
    if is_typing(x):
        return fmt_type_hint.into(f, x)

    if isinstance(x, type):
        return fmt_type.into(f, x)

    if isroutine(x):
        return fmt_routine.into(f, x)

    f.write_obj(x)


# def fmt_name(f: Formatter, x: Any):
#     name = getattr(x, "__qualname__", None) or getattr(x, "__name__", None)
#     if (
#         f.fqn
#         and (module_name := getattr(x, "__module__", None))
#         and (module_name != BUILTINS_MODULE or f.fq_builtins)
#     ):
#         f.write(module_name)
#         f.write(FQN_SEP)
#     f.write(name)


@FmtFunc
def fmt_routine(f: FmtWriter, x: Routine) -> None:
    if x.__name__ == LAMBDA_NAME:
        f.write("λ()")
    else:
        if f.opts.fqn and (
            x.__module__ != BUILTINS_MODULE or f.opts.fq_builtins
        ):
            f.write(x.__module__)
            f.write(FQN_SEP)
        # concat: "stick" things written in this context together as one term
        with f.concat():
            f.write(x.__qualname__)
            f.write("()")


@FmtFunc
def fmt_type(f: FmtWriter, x: type) -> None:
    if f.opts.fqn and (x.__module__ != BUILTINS_MODULE or f.opts.fq_builtins):
        f.write(x.__module__)
        f.write(FQN_SEP)
    f.write(x.__qualname__)


@FmtFunc
def fmt_type_value(f: FmtWriter, x: object) -> None:
    with f.concat():
        fmt_type.into(f, type(x))
        f.write(":")
    f.space()
    fmt.into(f, x)


@FmtFunc
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
