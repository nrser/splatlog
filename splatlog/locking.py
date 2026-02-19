"""
Locking support for thread-safe operations, provided as a
{py:class}`typing.ContextManager`.
"""

from contextlib import nullcontext
import logging
from typing import ContextManager
from warnings import warn

_NULL_CONTEXT = nullcontext()
"""
Fallback no-op context manager used when {py:mod}`logging` does not expose
its internal lock.
"""


def lock() -> ContextManager:
    """
    Acquire the {py:mod}`logging` module's internal lock as a context manager.

    Attempts to get the `_lock` attribute from {py:mod}`logging`, which is
    expected to be a {py:class}`threading.RLock` (technically a factory
    function, despite appearing as a class) that satisfies
    {py:class}`typing.ContextManager`. If it's not available for some
    reason, emits a {py:func}`warnings.warn` and returns a
    {py:class}`contextlib.nullcontext`.

    ## Returns

    A {py:class}`typing.ContextManager` — either the real
    {py:mod}`logging` lock or a no-op {py:class}`contextlib.nullcontext`.

    ## Examples

    ```python
    >>> from splatlog.locking import lock

    >>> with lock():
    ...     pass  # Do race-sensitive mutations here

    ```
    """
    logging_lock = getattr(logging, "_lock", None)
    if isinstance(logging_lock, ContextManager):
        return logging_lock
    warn(f"`logging._lock` is not a `typing.ContextManager`: {logging_lock!r}")
    return _NULL_CONTEXT
