"""
The `lib` module is for general-purpose structures and utilities. `lib` should
_not_ depend on _any_ other project code — you should be able to paste it into
another project and have it _just work_[^1].

You can think of `lib` as "extra batteries" on top of the Python standard
library. Previously, I've been tempted to break this type of work out into its
own package, but experience has taught me that's a bad idea... general-purpose
code is very difficult to get right, and every breaking change creates a cascade
of work. Being part of a logging library is almost just as good though, as it
gets to piggy-back on functionality that most projects can use.

[^1]:   You would want to adjust cross-references in the docstrings, which
        currently start with `splatlog.` for symbols outside that same file, but
        that won't break the code. Also, as of writing (2026-01-29), you'd need
        to add the [typeguard][] dependency, but we're looking to get rid of
        that.

[typeguard]: https://pypi.org/project/typeguard/
"""

from typing import Any
from collections.abc import Callable
from inspect import ismethod, signature, Parameter

# Re-exports
from .collections import (
    find as find,
    partition_mapping as partition_mapping,
    group_by as group_by,
)
from .text import (
    is_typing as is_typing,
    str_find_all as str_find_all,
    Formatter as Formatter,
    FmtOpts as FmtOpts,
    DEFAULT_FMT_OPTS as DEFAULT_FMT_OPTS,
    fmt as fmt,
    p as p,
    fmt_routine as fmt_routine,
    fmt_type as fmt_type,
    fmt_type_of as fmt_type_of,
    fmt_type_value as fmt_type_value,
    fmt_range as fmt_range,
    fmt_type_hint as fmt_type_hint,
    fmt_list as fmt_list,
)

from .typeguard import satisfies as satisfies


REQUIRABLE_PARAMETER_KINDS = frozenset(
    (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.KEYWORD_ONLY,
    )
)
"""
{py:attr}`inspect.Parameter.kind` that can be required (i.e., lack a
default value).

Excludes {py:const}`inspect.Parameter.VAR_POSITIONAL` (`*args`) and
{py:const}`inspect.Parameter.VAR_KEYWORD` (`**kwargs`), which are never
required.
"""


def is_required_parameter(parameter: Parameter) -> bool:
    """
    Check if a parameter is required (has no default value).

    A parameter is required if its kind is in
    {py:const}`REQUIRABLE_PARAMETER_KINDS` and it has no default value.

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


def has_method(
    obj: Any, method_name: str, req_arity: int | None = None
) -> bool:
    """
    Check if an object has a method with the given name.

    Optionally verify the method has a specific required arity.

    ## Parameters

    -   `obj`: The object to check.
    -   `method_name`: The name of the method to look for.
    -   `req_arity`: If provided, the method must have exactly this many required
        parameters.

    ## Returns

    {py:data}`True` if the object has a bound method with the given name (and
    matching arity if specified), {py:data}`False` otherwise.
    """
    if not hasattr(obj, method_name):
        return False
    method = getattr(obj, method_name)
    if not ismethod(method):
        return False
    if req_arity is not None:
        return required_arity(method) == req_arity
    return True


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


def respond_to(obj: Any, name: str, *args, **kwds) -> bool:
    """
    Check if an object has a method that can be called with the given arguments.

    Combines {py:func}`has_method` and {py:func}`is_callable_with` to verify
    both that the method exists and accepts the specified arguments.

    ## Parameters

    -   `obj`: The object to check.
    -   `name`: The name of the method to look for.
    -   `*args`: Positional arguments the method should accept.
    -   `**kwds`: Keyword arguments the method should accept.

    ## Returns

    {py:data}`True` if `obj` has a method `name` that can be called with the
    given arguments, {py:data}`False` otherwise.
    """
    if not hasattr(obj, name):
        return False
    fn = getattr(obj, name)
    if not ismethod(fn):
        return False
    return is_callable_with(fn, *args, **kwds)
