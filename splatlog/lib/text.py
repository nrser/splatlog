from __future__ import annotations
import dataclasses
from functools import wraps
from inspect import isroutine
import sys
import typing
from typing import (
    Any,
    Callable,
    ForwardRef,
    Generic,
    Literal,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    overload,
)
import types
from collections import abc

from splatlog.lib.collections import partition_mapping

BUILTINS_MODULE = object.__module__
TYPING_MODULE = typing.__name__
LAMBDA_NAME = (lambda x: x).__name__


def is_typing(x: Any) -> bool:
    return bool(
        get_origin(x) or get_args(x) or type(x).__module__ == TYPING_MODULE
    )


FmtOptsSelf = TypeVar("FmtOptsSelf", bound="FmtOpts")
TFallback = TypeVar("TFallback")
TFallbackCon = TypeVar("TFallbackCon", covariant=True)


class Formatter(Protocol):
    @overload
    def __call__(
        self, *args, fallback: Callable[[Any], TFallback], **kwds
    ) -> Union[str, TFallback]: ...

    @overload
    def __call__(self, *args, **kwds) -> str: ...


@dataclasses.dataclass(frozen=True)
class FmtOpts(Generic[TFallback]):
    @classmethod
    def of(cls: type[FmtOptsSelf], x) -> FmtOptsSelf:
        if x is None:
            return cls()
        if isinstance(x, cls):
            return x
        return cls(**x)

    @classmethod
    def provide(cls, fn) -> Formatter:
        field_names = {field.name for field in dataclasses.fields(cls)}

        @wraps(fn)
        def wrapped(*args, **kwds):
            field_kwds, fn_kwds = partition_mapping(kwds, field_names)
            if isinstance(args[-1], cls):
                *args, instance = args
                if field_kwds:
                    instance = dataclasses.replace(instance, **field_kwds)
            elif field_kwds:
                instance = cls(**field_kwds)
            else:
                instance = DEFAULT_FMT_OPTS

            return fn(*args, instance, **fn_kwds)

        return wrapped

    fallback: abc.Callable[[object], TFallback] = cast(
        abc.Callable[[object], TFallback], repr
    )
    module_names: bool = True
    omit_builtins: bool = True


DEFAULT_FMT_OPTS = FmtOpts()


@FmtOpts.provide
def get_name(x: Any, opts: FmtOpts) -> Optional[str]:
    """
    ##### Examples #####

    ```python
    >>> get_name(str)
    'str'

    >>> get_name(str, omit_builtins=False)
    'builtins.str'

    >>> get_name(get_name)
    'splatlog.lib.text.get_name'

    >>> get_name(get_name, module_names=False)
    'get_name'

    >>> get_name(FmtOpts)
    'splatlog.lib.text.FmtOpts'

    >>> get_name(str.count)
    'str.count'

    >>> class Screwy:
    ...     def __init__(self, name):
    ...         self.__qualname__ = name
    >>> get_name(Screwy(123)) is None
    True

    >>> get_name(int.__add__)
    'int.__add__'

    ```
    """
    name = getattr(x, "__qualname__", None) or getattr(x, "__name__", None)
    if not isinstance(name, str):
        return None
    if (
        opts.module_names
        and (module_name := getattr(x, "__module__", None))
        and not (module_name == BUILTINS_MODULE and opts.omit_builtins)
    ):
        return f"{module_name}.{name}"
    return name


@FmtOpts.provide
def fmt(x: Any, opts: FmtOpts[TFallback]) -> Union[str, TFallback]:
    """
    ##### Examples #####

    ```python
    >>> fmt(int.__add__)
    'int.__add__()'

    ```
    """
    if is_typing(x):
        return fmt_type_hint(x, opts)

    if isinstance(x, type):
        return fmt_type(x, opts)

    if isroutine(x):
        return fmt_routine(x, opts)

    return opts.fallback(x)


@FmtOpts.provide
def p(x: Any, opts: FmtOpts, **kwds) -> None:
    print(fmt(x, opts), **kwds)


@FmtOpts.provide
def fmt_routine(
    fn: types.FunctionType, opts: FmtOpts[TFallback]
) -> Union[str, TFallback]:
    """
    ##### Examples #####

    ```python
    >>> fmt_routine(fmt_routine)
    'splatlog.lib.text.fmt_routine()'

    >>> fmt_routine(fmt_routine, module_names=False)
    'fmt_routine()'

    >>> fmt_routine(lambda x, y: x + y)
    'λ()'

    >>> def f():
    ...     def g():
    ...         pass
    ...     return g
    >>> fmt_routine(f())
    'splatlog.lib.text.f.<locals>.g()'

    >>> fmt_routine(FmtOpts.provide)
    'splatlog.lib.text.FmtOpts.provide()'

    ```
    """

    if fn.__name__ == LAMBDA_NAME:
        return "λ()"

    if name := get_name(fn, opts):
        return name + "()"

    return opts.fallback(fn)


@FmtOpts.provide
def fmt_type(t: Type, opts: FmtOpts[TFallback]) -> Union[str, TFallback]:
    """
    ##### Examples #####

    ```python
    >>> fmt_type(abc.Collection)
    'collections.abc.Collection'

    >>> fmt_type(abc.Collection, module_names=False)
    'Collection'

    >>> fmt_type(abc.Collection, FmtOpts(module_names=False))
    'Collection'

    >>> fmt_type(abc.Collection, FmtOpts(module_names=False), module_names=True)
    'collections.abc.Collection'

    ```
    """

    if name := get_name(t, opts):
        return name

    # This should not really ever happen..
    return opts.fallback(t)


@FmtOpts.provide
def fmt_type_of(x: object, opts: FmtOpts[TFallback]) -> str | TFallback:
    return fmt_type(type(x), opts)


@FmtOpts.provide
def fmt_type_value(x: object, opts: FmtOpts[TFallback]) -> str | TFallback:
    """Helper to produce the `TYPE: VALUE` format we often use in error
    messages.

    Nothing fancy, just calls {py:func}`fmt_type_of` and {py:func}`fmt`.

    ## Examples

    ```python

    fmt_type_value(123)
    "int: 123"

    ```
    """
    return f"{fmt_type_of(x, opts)}: {fmt(x, opts)}"


def _nest(formatted: str, nested: bool) -> str:
    return f"({formatted})" if nested else formatted


@FmtOpts.provide
def _fmt_optional(
    t: Any, opts: FmtOpts[TFallback], *, nested: bool = False
) -> Union[str, TFallback]:
    if get_origin(t) is Literal:
        return _nest("None | " + fmt_type_hint(t, opts), nested)
    return fmt_type_hint(t, opts, nested=True) + "?"


@FmtOpts.provide
def fmt_type_hint(
    t: Any, opts: FmtOpts[TFallback], *, nested: bool = False
) -> Union[str, TFallback]:
    """
    ##### Examples #####

    Examples can be found in <doc/splatlog/lib/text/fmt_type_hint.md>.

    """

    if t is Ellipsis:
        return "..."

    if t is types.NoneType:
        return "None"

    if isinstance(t, ForwardRef):
        return t.__forward_arg__

    if isinstance(t, TypeVar):
        # NOTE  Just gonna punt on this for now... for some reason the way
        #       Python handles generics just manages to frustrate and confuse
        #       me...
        return repr(t)

    origin = get_origin(t)
    args = get_args(t)

    if args == ():
        return fmt_type(origin or t, opts)

    if origin is Union:
        if len(args) == 2:
            if args[0] is types.NoneType:
                return _fmt_optional(args[1], opts, nested=nested)
            if args[1] is types.NoneType:
                return _fmt_optional(args[0], opts, nested=nested)

        return _nest(
            " | ".join(
                fmt_type_hint(
                    arg, opts, nested=(get_origin(arg) is not Literal)
                )
                for arg in args
            ),
            nested,
        )

    if origin is Literal:
        return _nest(" | ".join(fmt(arg) for arg in args), nested)

    if origin is dict:
        return (
            "{"
            + fmt_type_hint(args[0], opts, nested=True)
            + ": "
            + fmt_type_hint(args[1], opts, nested=True)
            + "}"
        )

    if origin is list:
        return fmt_type_hint(args[0], opts, nested=True) + "[]"

    if origin is tuple:
        return "(" + ", ".join(fmt_type_hint(arg, opts) for arg in args) + ")"

    if origin is set:
        return "{" + fmt_type_hint(args[0], opts) + "}"

    if origin is abc.Callable:
        return _nest(
            "("
            + ", ".join(fmt_type_hint(arg, opts) for arg in args[0])
            + ") -> "
            + fmt_type_hint(args[1], opts),
            nested,
        )

    return opts.fallback(t)


def fmt_range(rng: range) -> str:
    length = len(rng)
    if length <= 3:
        return str(list(rng))
    if rng.stop == sys.maxsize:
        if rng.step == 1:
            return f"[{rng[0]}, ...]"
        return f"[{rng[0]}, {rng[1]}, ...]"
    return f"[{rng[0]}, {rng[1]}, ..., {rng.stop}]"
