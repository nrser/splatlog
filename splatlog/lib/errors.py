"""
Helpers for working with errors, which generally revolve exceptions.
"""

from collections.abc import Callable
from typing import Any


class NoErrorError(Exception):
    """
    Raised by {py:func}`err_catch` when the `fn` it invokes fails to raise an
    `Exception`.
    """


def err_catch[**P](
    fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
) -> Exception:
    """
    Return the {py:class}`Exception` raised by `fn` when called with `args` and
    `kwargs`.

    ## Raises

    -   {py:exc}`NoErrorError` if `fn` does not raise.
    """
    try:
        fn(*args, **kwargs)
    except Exception as err:
        return err
    raise NoErrorError(f"Expected {fn!r} to raise but it returned")
