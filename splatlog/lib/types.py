"""
Library types: general, project-agnostic type hints and helpers.
"""

from inspect import isclass
import typing
import types

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!! IMPORTANT No cross-package `import` at top-level
# !!!
# !!! This module is considered _foundational_ — _any_ other module should be
# !!! able to import it without triggering an import loop.
# !!!
# !!! Imports of other project modules should be avoided, and placed inside
# !!! function or method bodies if they can't be.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Constants
# ============================================================================

BUILTINS_MODULE_NAME = object.__module__
"""
The module name for built-in types (e.g., `str`, `int`).

The name is `'builtins'` but we read it from `object.__module__`.
"""

TYPING_MODULE_NAME = typing.__name__
"""
The module name of the {py:mod}`typing` module.

The name is `'typing'` but we read it from `typing.__name__`.
"""


def is_typing(x: typing.Any, *, include_type: bool = True) -> bool:
    """
    Test if a value is a _type hint_.

    :::{warning}

    This function is best-effort — correctly identifying type hints is not
    strait-forward. Python's type hint system is convoluted.

    :::

    Parameters
    --------------------------------------------------------------------------

    -   `x`: The value to check.

    Returns
    --------------------------------------------------------------------------

    {py:data}`True` if `x` appears to be a typing.

    Examples
    --------------------------------------------------------------------------

    Works for the usual {py:mod}`typing` constructs:

    ```pycon
    >>> import typing

    >>> is_typing(typing.Any)
    True

    >>> is_typing(int | str)
    True

    >>> is_typing(typing.Literal["a", "b"])
    True

    >>> T = typing.TypeVar("T")
    >>> is_typing(T)
    True

    >>> N = typing.NewType("N", int)
    >>> is_typing(N)
    True

    >>> class P(typing.Protocol):
    ...     def f(x: int) -> str: ...

    >>> is_typing(P)
    True

    ```

    Classes ({py:class}`type` instances) are considered types, because they can
    be used as a type hint. This can be disabled with `include_type=False`.

        >>> is_typing(int)
        True

        >>> is_typing(int, include_type=False)
        False

    Recognizes the subscripted abstract classes from {py:mod}`collections.abc`,
    as well as subscripted built-ins like {py:class}`list` and {py:class}`dict`:

        >>> is_typing(list[str])
        True

        >>> from collections import abc

        >>> is_typing(abc.Mapping[str, typing.Any])
        True

    The objects used to construct type hints should not themselves be
    considered typings:

        >>> is_typing(typing.Optional)
        False

    """
    if x is typing.Any:
        return True

    if isinstance(x, type) and include_type:
        return True

    if isinstance(
        x,
        (
            # list[T], dict[K, V], etc.
            types.GenericAlias,
            # T | V
            types.UnionType,
            # TypeVar("T")
            typing.TypeVar,
            # NewType("T", object)
            typing.NewType,
        ),
    ):
        return True

    # Literal[...], Optional[T], Union[T, V]
    if typing.get_origin(x) is not None:
        return True

    return False


def is_builtins(obj: object) -> bool:
    """
    Is an {py:class}`object` `obj` part of the {py:mod}`builtins` package of
    all "built-in" identifiers of Python.

    I'm not sure that we can always tell, but we try!
    """

    if isclass(obj):
        return obj.__module__ == BUILTINS_MODULE_NAME
    return type(obj).__module__ == BUILTINS_MODULE_NAME
