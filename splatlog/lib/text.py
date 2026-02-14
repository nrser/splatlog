"""
Text formatting utilities for human-readable output.

Provides functions for formatting types, type hints, routines, and values in
a concise, readable style. The {py:class}`FmtOpts` dataclass controls
formatting behavior like module name inclusion and list formatting.
"""

from __future__ import annotations
import dataclasses
from functools import wraps
from inspect import isroutine
import sys
import typing
from typing import (
    Any,
    ForwardRef,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
import types
from collections import abc

# `Self` was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import rich.repr

from .collections import partition_mapping

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


def str_find_all(s: str, char: str) -> abc.Iterable[int]:
    """
    Find all occurrences of a character in a string.

    ## Parameters

    -   `s`: The string to search.
    -   `char`: The character to find.

    ## Returns

    An iterable of indices where `char` occurs in `s`.
    """
    i = s.find(char)
    while i != -1:
        yield i
        i = s.find(char, i + 1)


class Formatter(Protocol):
    """Protocol for formatter functions that return strings."""

    def __call__(self, *args, **kwds) -> str: ...


@dataclasses.dataclass(frozen=True)
class FmtOpts:
    """
    Options controlling text formatting behavior.

    This is a frozen dataclass; use {py:func}`dataclasses.replace` to create
    modified copies. The {py:meth}`provide` decorator allows functions to
    accept these options either as a final positional argument or as keyword
    arguments.
    """

    @classmethod
    def of(cls: type[Self], x) -> Self:
        """
        Coerce a value to a {py:class}`FmtOpts` instance.

        ## Parameters

        -   `x`: {py:data}`None` (returns default), an existing instance
            (returned as-is), or a dict of field values.

        ## Returns

        A {py:class}`FmtOpts` instance.
        """
        if x is None:
            return cls()
        if isinstance(x, cls):
            return x
        return cls(**x)

    @classmethod
    def provide(cls, fn) -> Formatter:
        """
        Decorator that adds {py:class}`FmtOpts` support to a function.

        The decorated function can receive options as:

        -   A final positional argument of type {py:class}`FmtOpts`
        -   Keyword arguments matching {py:class}`FmtOpts` field names
        -   Both of the above, with keyword arguments replacing values in the
            instance.
        -   Neither, using a {py:class}`FmtOpts` with all default values.

        ## Parameters

        -   `fn`: The function to decorate. Should accept a {py:class}`FmtOpts`
            instance as its last positional parameter.

        ## Returns

        A wrapped function with flexible options handling.

        ## Examples

        Using default options (no arguments):

        ```python
        >>> fmt_type(str)
        'str'

        ```

        Using keyword arguments for options:

        ```python
        >>> fmt_type(str, omit_builtins=False)
        'builtins.str'

        ```

        Using a FmtOpts instance as final positional argument:

        ```python
        >>> fmt_type(str, FmtOpts(omit_builtins=False))
        'builtins.str'

        ```

        Combining instance with keyword overrides:

        ```python
        >>> opts = FmtOpts(module_names=False)
        >>> fmt_type(str, opts, module_names=True, omit_builtins=False)
        'builtins.str'

        ```
        """
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

    def __rich_repr__(self) -> rich.repr.Result:
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if value != field.default:
                yield field.name, value

    fallback: abc.Callable[[object], str] = repr
    """Fallback formatter when no specific formatter applies."""

    module_names: bool = True
    """Whether to include module names in formatted output."""

    omit_builtins: bool = True
    """Whether to omit the `builtins` module prefix for built-in types."""

    items: int | None = None
    """
    Max number of items to show in a {py:class}`collections.abc.Sequence`, with
    any additional items being replaced with the {py:attr}`ellipsis`.
    """

    ellipsis: str = "..."
    """
    Sting to replace characters in long {py:class}`str`, items in long
    {py:class}`collections.abc.Sequence`, etc.

    ## See Also

    1.  {py:attr}`items`
    """

    ls_sep: str = ","
    """
    List separator. {py:func}`fmt_list` will stick this between items (along
    with a space).
    """

    ls_conj: str | None = None
    """
    List conjunction. When {py:data}`None` {py:func}`fmt_list` will use the
    {py:attr}`FmtOpts.ls_sep` throughout, like `A, B, C`. Configuring a
    conjunction `"and"` would get you `A, B, and C`.
    """

    ls_ox: bool = True
    """
    Should {py:func}`fmt_list` use the [Oxford comma][] style?
    """

    typing: bool = False
    """
    Add formatted type.
    """


DEFAULT_FMT_OPTS = FmtOpts()
"""A {py:class}`FmtOpts` instance with all defaults attributes."""


@FmtOpts.provide
def get_name(x: Any, opts: FmtOpts) -> Optional[str]:
    """
    Get the qualified name of an object, optionally with module prefix.

    ## Parameters

    -   `x`: The object to get the name of.
    -   `opts`: Formatting options.

    ## Returns

    The name as a string, or {py:data}`None` if the object has no name.

    ## Examples

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
def fmt(x: Any, opts: FmtOpts) -> str:
    """
    Format a value for human-readable output.

    Dispatches to specialized formatters based on the value's type:
    typing constructs, types, and routines each have dedicated formatters.

    ## Parameters

    -   `x`: The value to format.
    -   `opts`: Formatting options.

    ## Returns

    A formatted string representation.

    ## Examples

    ```python
    >>> fmt(int.__add__)
    'int.__add__()'

    ```
    """
    if opts.typing:
        opts = dataclasses.replace(opts, typing=False)
        return fmt_type_value(x, opts)

    if is_typing(x):
        return fmt_type_hint(x, opts)

    if isinstance(x, type):
        return fmt_type(x, opts)

    if isroutine(x):
        return fmt_routine(x, opts)

    return opts.fallback(x)


@FmtOpts.provide
def p(x: Any, opts: FmtOpts, **kwds) -> None:
    """
    Print a formatted value.

    Shorthand for `print(fmt(x, opts), **kwds)`.

    ## Parameters

    -   `x`: The value to format and print.
    -   `opts`: Formatting options.
    -   `**kwds`: Additional arguments passed to {py:func}`print`.
    """
    print(fmt(x, opts), **kwds)


@FmtOpts.provide
def fmt_routine(fn: types.FunctionType, opts: FmtOpts) -> str:
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
def fmt_type(t: type, opts: FmtOpts) -> str:
    """
    Format a type for display.

    ## Parameters

    -   `t`: The type to format.
    -   `opts`: Formatting options.

    ## Returns

    The type's qualified name, with or without module prefix per options.

    ## Examples

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


@FmtOpts.provide
def fmt_type_value(x: object, opts: FmtOpts) -> str:
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
def _fmt_optional(t: Any, opts: FmtOpts, *, nested: bool = False) -> str:
    if get_origin(t) is Literal:
        return _nest("None | " + fmt_type_hint(t, opts), nested)
    return fmt_type_hint(t, opts, nested=True) + "?"


@FmtOpts.provide
def fmt_type_hint(t: Any, opts: FmtOpts, *, nested: bool = False) -> str:
    """
    Format a type hint for human-readable display.

    Produces concise representations like `str?` for `Optional[str]`,
    `int[]` for `list[int]`, and `{str: int}` for `dict[str, int]`.

    ## Parameters

    -   `t`: The type hint to format.
    -   `opts`: Formatting options.
    -   `nested`: Whether this is a nested type (used internally for
        parenthesization).

    ## Returns

    A formatted string representation of the type hint.
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


@FmtOpts.provide
def fmt_list(items: abc.Iterable, opts: FmtOpts) -> str:
    """
    Format a list of `items`. By default this is comma-separated, like
    `A, B, C`.
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


@FmtOpts.provide
def fmt_seq(seq: abc.Sequence, opts: FmtOpts) -> str:
    """
    Format a sequence, respecting the {py:attr}`FmtOpts.items` limit and
    {py:attr}`FmtOpts.ellipsis` for truncation.

    ## Parameters

    -   `seq`: The sequence to format (list or tuple).
    -   `opts`: Formatting options.

    ## Returns

    A formatted string like `[1, 2, 3]` or `(1, 2, ...)`.

    ## Examples

    ```python
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
