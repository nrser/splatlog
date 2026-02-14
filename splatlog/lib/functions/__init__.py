"""
Function and decorator utilities.

Provides tools for inspecting callable signatures and a slot-compatible
cached property decorator.
"""

from collections.abc import Callable
from inspect import signature, Parameter

from .slot_cached_property import SlotCachedProperty

__all__ = [
    "SlotCachedProperty",
    "REQUIRABLE_PARAMETER_KINDS",
    "is_required_parameter",
    "required_arity",
    "is_callable_with",
]


REQUIRABLE_PARAMETER_KINDS = frozenset(
    (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.KEYWORD_ONLY,
    )
)
"""
{py:attr}`inspect.Parameter.kind` values that can be required (i.e., lack a
default value).

Excludes {py:attr}`inspect.Parameter.VAR_POSITIONAL` (`*args`) and
{py:attr}`inspect.Parameter.VAR_KEYWORD` (`**kwargs`), which are never
required.
"""


def is_required_parameter(parameter: Parameter) -> bool:
    """
    Check if a parameter is required (has no default value).

    A parameter is required if its kind is in
    {py:data}`REQUIRABLE_PARAMETER_KINDS` and it has no default value.

    ## Parameters

    -   `parameter`: The {py:class}`inspect.Parameter` to check.

    ## Returns

    {py:data}`True` if the parameter is required, {py:data}`False` otherwise.
    """
    return (
        parameter.kind in REQUIRABLE_PARAMETER_KINDS
        and parameter.default is Parameter.empty
    )


def required_arity(fn: Callable) -> int:
    """
    Compute the number of required parameters for a callable.

    Counts positional-only, keyword-only, and positional-or-keyword parameters
    that have no default value.

    ## Parameters

    -   `fn`: The callable to inspect.

    ## Returns

    The count of required parameters.

    ## Examples

    ```python
    >>> def f_1():
    ...     pass
    >>> required_arity(f_1)
    0

    >>> def f_2(x):
    ...     pass
    >>> required_arity(f_2)
    1

    >>> def f_3(x=1):
    ...     pass
    >>> required_arity(f_3)
    0

    >>> def f_4(x, y, *, w, z=3):
    ...     pass
    >>> required_arity(f_4)
    3

    >>> def f_5(*args, **kwds):
    ...     pass
    >>> required_arity(f_5)
    0

    ```
    """
    return sum(
        int(is_required_parameter(parameter))
        for parameter in signature(fn).parameters.values()
    )


def is_callable_with(fn: Callable, *args, **kwds) -> bool:
    """
    Check if a callable can be invoked with the given arguments.

    Uses {py:meth}`inspect.Signature.bind` to verify the arguments match the
    callable's signature without actually calling it.

    ## Parameters

    -   `fn`: The callable to check.
    -   `*args`: Positional arguments to test.
    -   `**kwds`: Keyword arguments to test.

    ## Returns

    {py:data}`True` if `fn` can be called with the given arguments,
    {py:data}`False` otherwise.

    ## Examples

    ```python
    >>> def f(x, y, z):
    ...     pass

    >>> is_callable_with(f, 1, 2, z=3)
    True

    >>> is_callable_with(f, 1, 2)
    False

    ```
    """
    sig = signature(fn)
    try:
        sig.bind(*args, **kwds)
    except TypeError:
        return False
    return True
