from typing import Any, Optional
from collections.abc import Callable
from inspect import ismethod, signature, Parameter

# Re-exports
from .collections import (
    find as find,
    each as each,
    partition_mapping as partition_mapping,
    group_by as group_by,
)
from .text import (
    is_typing as is_typing,
    Formatter as Formatter,
    FmtOpts as FmtOpts,
    DEFAULT_FMT_OPTS as DEFAULT_FMT_OPTS,
    fmt as fmt,
    p as p,
    fmt_routine as fmt_routine,
    fmt_type as fmt_type,
    fmt_type_of as fmt_type_of,
    fmt_range as fmt_range,
    fmt_type_hint as fmt_type_hint,
)

from .typeguard import satisfies as satisfies


REQUIRABLE_PARAMETER_KINDS = frozenset(
    (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.KEYWORD_ONLY,
    )
)


def is_required_parameter(parameter: Parameter) -> bool:
    return (
        parameter.kind in REQUIRABLE_PARAMETER_KINDS
        and parameter.default is Parameter.empty
    )


def required_arity(fn: Callable) -> int:
    """
    Compute the number of required parameters for a `collections.abc.Callable`.

    Result includes positional-only, keyword-only, and position-or-keyword
    parameters.

    ##### Examples #####

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

    Ok, one weird corner-case to note...

    `inspect.Parameter.default` is set to `inspect.Parameter.empty` when the
    parameter does not have a default, as in `f_req_x`, which behaves as
    expected:

    ```python

    >>> def f_req_x(x):
    ...     return f"x is {x}"

    >>> required_arity(f_req_x)
    1

    >>> f_req_x()
    Traceback (most recent call last):
        ...
    TypeError: f_req_x() missing 1 required positional argument: 'x'

    ```

    However the user can also _explicitly_ define the parameter default to be
    `inspect.Parameter.empty`, as in `f_empty_x`, which causes odd behavior:

    ```python

    >>> def f_empty_x(x=Parameter.empty):
    ...     return f"x is {x}"

    ```

    This function measures a required arity of `1` for `f_empty_x`, as it can no
    longer tell that the default was set explicitly.

    ```python

    >>> required_arity(f_empty_x)
    1

    ```

    However, `f_empty_x` can be called with no arguments.

    ```python

    >>> f_empty_x()
    "x is <class 'inspect._empty'>"

    ```

    `inspect.Signature.bind` seems to get confused too.

    ```python

    >>> signature(f_empty_x).bind()
    Traceback (most recent call last):
        ...
    TypeError: missing a required argument: 'x'

    ```
    """
    return sum(
        int(is_required_parameter(parameter))
        for parameter in signature(fn).parameters.values()
    )


def has_method(
    obj: Any, method_name: str, req_arity: Optional[int] = None
) -> bool:
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

    ##### Examples #####

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


def respond_to(obj, name, *args, **kwds) -> bool:
    if not hasattr(obj, name):
        return False
    fn = getattr(obj, name)
    if not ismethod(fn):
        return False
    return is_callable_with(fn, *args, **kwds)
