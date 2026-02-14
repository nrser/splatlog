"""
Runtime type checking utilities wrapping the `typeguard` package.
"""

import sys
from typing import Any, TypeVar

from typeguard import check_type, TypeCheckError

# TypeIs was added to stdlib typing in 3.13; simplify when requires-python >= 3.13
if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

T = TypeVar("T")


def satisfies(value: Any, expected_type: type[T]) -> TypeIs[T]:
    """
    Check if a value satisfies a type at runtime.

    Uses {py:func}`typeguard.check_type` to perform the check and returns a
    {py:obj}`~typing.TypeIs` for use in type narrowing.

    ## Parameters

    -   `value`: The value to check.
    -   `expected_type`: The type to check against.

    ## Returns

    {py:data}`True` if `value` is of `expected_type`, {py:data}`False`
    otherwise.

    ## Examples

    ```python
    >>> satisfies(123, int)
    True

    >>> satisfies("hello", int)
    False

    >>> satisfies([1, 2, 3], list[int])
    True

    ```
    """
    try:
        check_type(value, expected_type)
    except TypeCheckError:
        return False
    return True
