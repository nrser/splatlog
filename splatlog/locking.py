from contextlib import nullcontext
import logging
from typing import ContextManager

_NULL_CONTEXT = nullcontext()


def lock() -> ContextManager:
    """
    Attempt to get the `_lock` attribute from {py:mod}`logging`. If it's not
    there for some reason returns a {py:class}`contextlib.nullcontext`.

    Use like

    ```python
    with lock():
        # Do race-sensitive mutations
    ```
    """
    logging_lock = getattr(logging, "_lock", None)
    if logging_lock:
        return logging_lock
    return _NULL_CONTEXT
