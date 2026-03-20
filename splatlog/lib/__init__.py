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

from inspect import ismethod

# Re-exports
from .types import (
    is_builtins,
    is_typing,
)
from .collections import (
    find,
    partition_mapping,
    group_by,
    unary,
)
from .functions import (
    REQUIRABLE_PARAMETER_KINDS,
    is_required_parameter,
    required_arity,
    is_callable_with,
)
from .text import (
    str_find_all,
    formatter,
    Formatter,
    FmtOpts,
    FmtKwds,
    FmtFallback,
    FmtTdBase,
    FmtResult,
    fmt,
    fmt_name,
    fmt_type,
    fmt_type_of,
    fmt_type_value,
    fmt_type_hint,
    fmt_routine,
    fmt_range,
    fmt_list,
    fmt_seq,
    fmt_datetime,
    fmt_date,
    fmt_time,
    fmt_timedelta,
)

from .typeguard import satisfies

__all__ = [
    "find",
    "partition_mapping",
    "group_by",
    "unary",
    "REQUIRABLE_PARAMETER_KINDS",
    "is_required_parameter",
    "required_arity",
    "is_callable_with",
    # .text
    "str_find_all",
    "is_typing",
    "is_builtins",
    "formatter",
    "Formatter",
    "FmtOpts",
    "FmtResult",
    "FmtKwds",
    "FmtFallback",
    "FmtTdBase",
    "fmt",
    "fmt_name",
    "fmt_type",
    "fmt_type_of",
    "fmt_type_value",
    "fmt_type_hint",
    "fmt_routine",
    "fmt_range",
    "fmt_list",
    "fmt_seq",
    "fmt_datetime",
    "fmt_datetime",
    "fmt_date",
    "fmt_time",
    "fmt_timedelta",
    # .typeguard
    "satisfies",
    # .
    "has_method",
    "respond_to",
]


def has_method(
    obj: object, method_name: str, req_arity: int | None = None
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


def respond_to(obj: object, name: str, *args, **kwds) -> bool:
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
