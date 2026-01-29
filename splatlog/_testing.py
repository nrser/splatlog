"""
Shit just used in tests (doctest at the moment), excluded from the distributed
package.
"""

import logging
import sys
from typing import Any, Optional, Union
import ast
import inspect
from datetime import datetime
from types import ModuleType

from splatlog.typings import ExcInfo, ToLevel, to_level

__all__ = ["get_constant_docstrings", "make_log_record"]


def get_constant_docstrings(module: str | ModuleType):
    """
    {py:mod}`doctest` doesn't automatically pickup the "following docstring"
    format used by Sphinx/MyST to document constants, so we need to parse the
    AST to collect them.

    ## Parameters

    -   `module`: name of or reference to the module.

    ## Returns

    A {py:class}`dict` mapping constant names to their Sphinx-style docstring,
    suitable to assign to `__test__` for {py:mod}`doctest` to pickup.

    ## Examples

    ```python
    import os

    if os.environ.get("TESTING"):
        from splatlog._testing import get_constant_docstrings

        __test__ = get_constant_docstrings(sys.modules[__name__])
    ```
    """
    if isinstance(module, str):
        module = sys.modules[module]

    source = inspect.getsource(module)
    tree = ast.parse(source)

    docstrings = {}
    for i, node in enumerate(tree.body[:-1]):
        if isinstance(node, ast.Assign):
            next_node = tree.body[i + 1]
            if isinstance(next_node, ast.Expr) and isinstance(
                next_node.value, ast.Constant
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        docstrings[target.id] = next_node.value.value

    return docstrings


def make_log_record(
    name: str = __name__,
    level: ToLevel = logging.INFO,
    pathname: str = __file__,
    lineno: int = 123,
    msg: str = "Test message",
    args: Union[tuple, dict[str, Any]] = (),
    exc_info: Optional[ExcInfo] = None,
    func: Optional[str] = None,
    sinfo: Optional[str] = None,
    *,
    created: Union[None, float, datetime] = None,
    data: Optional[dict[str, Any]] = None,
) -> logging.LogRecord:
    """
    Used in testing to make `logging.LogRecord` instances. Provides defaults
    for all of the parameters, since you often only care about setting some
    subset.

    Provides a hack to set the `logging.LogRecord.created` attribute (as well as
    associated `logging.LogRecord.msecs` and `logging.LogRecord.relativeCreated`
    attributes) by providing an extra `created` keyword parameter.

    Also provides a way to set the `data` attribute by passing the extra `data`
    keyword parameter.

    SEE https://docs.python.org/3.10/library/logging.html#logging.LogRecord
    """
    record = logging.LogRecord(
        name=name,
        level=to_level(level),
        pathname=pathname,
        lineno=lineno,
        msg=msg,
        args=args,
        exc_info=exc_info,
        func=func,
        sinfo=sinfo,
    )

    if created is not None:
        if isinstance(created, datetime):
            created = created.timestamp()
        record.created = created
        record.msecs = (created - int(created)) * 1000
        record.relativeCreated = (created - logging._startTime) * 1000  # type: ignore
    if data is not None:
        setattr(record, "data", data)

    return record
