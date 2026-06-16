"""
Testing utilities for splatlog.

Provides helpers for doctests and pytest tests, including text assertion
utilities and log record factories.
"""

from __future__ import annotations

import logging
import sys
import textwrap
from typing import Any, Optional, Union, TYPE_CHECKING
import ast
import inspect
from datetime import datetime
from io import StringIO
from types import ModuleType

from splatlog.lib.text import fmt
from splatlog.types import ExcInfo, ToLevel, to_level

if TYPE_CHECKING:
    from rich.console import Console, RenderableType
    from rich.style import Style

__all__ = [
    "assert_renders_segment",
    "assert_text",
    "get_constant_docstrings",
    "make_log_record",
]


def _get_default_console() -> "Console":
    """Create a default Console for rendering tests."""
    from rich.console import Console

    return Console(file=StringIO(), no_color=True, force_terminal=False)


def assert_renders_segment(
    renderable: "RenderableType",
    text: str,
    *,
    style: "str | Style | None" = None,
    console: "Console | None" = None,
) -> None:
    """
    Assert that rendering produces a segment containing the given text.

    Renders `renderable` to segments and asserts that at least one segment
    contains `text`. If `style` is provided, also asserts that the matching
    segment has the specified style.

    ## Parameters

    -   `renderable`: Any Rich renderable object.
    -   `text`: Text that must appear in at least one segment.
    -   `style`: Optional style name or Style object the segment must have.
    -   `console`: Optional Console to use for rendering. If not provided,
        a default Console is created.

    ## Examples

    >>> from rich.text import Text
    >>> from splatlog.testing import assert_renders_segment
    >>> assert_renders_segment(Text("hello world"), "hello")
    >>> assert_renders_segment(Text("hello", style="bold"), "hello", style="bold")
    """
    __tracebackhide__ = True

    from rich.style import Style as RichStyle

    if console is None:
        console = _get_default_console()

    resolved_style: RichStyle | None = None
    if style is not None:
        if isinstance(style, str):
            resolved_style = console.get_style(style)
        else:
            resolved_style = style

    segments = list(console.render(renderable))

    for segment in segments:
        if segment.text and text in segment.text:
            if resolved_style is None or segment.style == resolved_style:
                return

    if style is not None:
        raise AssertionError(
            f"No segment containing {text!r} with style {style!r} found in\n\n"
            f"{fmt(segments, quote=True)}"
        )
    else:
        raise AssertionError(
            f"No segment containing {text!r} found in\n\n{segments!r}"
        )


def assert_text(
    actual: str,
    expected: str,
    *,
    leading_newlines: int | None = None,
    trailing_newlines: int | None = None,
) -> None:
    """
    Assert that two strings match after normalizing whitespace artifacts
    from source-code embedding.

    :::{tip}
    To enable useful feedback when this assertion fails you need to add this to
    `tests/conftest.py`:

    ```py
    pytest.register_assert_rewrite("splatlog.testing")
    ```
    :::

    Both `actual` and `expected` are normalized by:

    1.  Dedenting (removing common leading whitespace)
    2.  Stripping trailing whitespace from each line
    3.  Stripping leading and trailing blank lines

    This allows the `expected` string to be written with natural indentation
    inside test functions without worrying about source-level whitespace
    artifacts.

    Optional keyword arguments assert on visually-hidden properties of
    `actual` that normalization would otherwise discard:

    -   `leading_newlines` — expected count of leading ``\\n`` characters
    -   `trailing_newlines` — expected count of trailing ``\\n`` characters

    ## Examples

    >>> from splatlog.testing import assert_text
    >>> assert_text("hello\\nworld", '''
    ...     hello
    ...     world
    ... ''')

    >>> assert_text("hello\\n", "hello", trailing_newlines=1)
    """
    # Tell Pytest not to show this function as the error location
    __tracebackhide__ = True

    def _normalize(s: str) -> str:
        s = textwrap.dedent(s)
        lines = s.splitlines()
        lines = [line.rstrip() for line in lines]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    assert _normalize(actual) == _normalize(expected)

    if leading_newlines is not None:
        n = len(actual) - len(actual.lstrip("\n"))
        if n != leading_newlines:
            raise AssertionError(
                f"Expected {leading_newlines} leading newline(s), got {n}"
            )

    if trailing_newlines is not None:
        n = len(actual) - len(actual.rstrip("\n"))
        if n != trailing_newlines:
            raise AssertionError(
                f"Expected {trailing_newlines} trailing newline(s), got {n}"
            )


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
        from splatlog.testing import get_constant_docstrings

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
