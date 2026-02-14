"""
Utilities for enriching Python values with Rich formatting.
"""

from __future__ import annotations
from typing import Callable, Literal, overload
from inspect import isclass, isroutine

from rich.console import RenderableType
from rich.pretty import Pretty
from rich.highlighter import ReprHighlighter
from rich.text import Text

from splatlog.lib.text import fmt_routine
from splatlog.types import is_rich

from .enriched_type import EnrichedType


REPR_HIGHLIGHTER = ReprHighlighter()
"""
Shared {py:class}`rich.highlighter.ReprHighlighter` instance for repr syntax
highlighting.
"""


def repr_highlight(value: object, *, use_ascii: bool = False) -> Text:
    """
    Get a syntax-highlighted repr of a value.

    ## Parameters

    -   `value`: The object to repr.
    -   `use_ascii`: If {py:data}`True`, use {py:func}`ascii` instead of
        {py:func}`repr`.

    ## Returns

    A {py:class}`rich.text.Text` with repr highlighting applied.
    """
    text = Text(ascii(value) if use_ascii else repr(value), end="")
    REPR_HIGHLIGHTER.highlight(text)
    return text


def enrich_type(typ: type[object]) -> RenderableType:
    """
    Create a Rich renderable for a type.

    If the type has a `__rich_type__` method, calls it. Otherwise wraps
    in {py:class}`EnrichedType`.

    ## Parameters

    -   `typ`: The type to enrich.

    ## Returns

    A Rich renderable representing the type.
    """
    if (rich_type := getattr(typ, "__rich_type__", None)) and isinstance(
        rich_type, Callable
    ):
        return rich_type()
    return EnrichedType(typ)


def enrich_type_of(value: object) -> RenderableType:
    """
    Create a Rich renderable for the type of a value.

    Shorthand for `enrich_type(type(value))`.
    """
    return enrich_type(type(value))


@overload
def enrich(value: object, inline: Literal[True]) -> Text: ...


@overload
def enrich(value: object, inline: Literal[False]) -> RenderableType: ...


@overload
def enrich(value: object) -> RenderableType: ...


def enrich(value, inline=False):
    """
    Convert a Python value to a Rich renderable.

    Handles special cases like types, routines, and strings, applying
    appropriate formatting. Values that are already Rich renderables are
    returned as-is (unless `inline=True` and they're not {py:class}`Text`).

    ## Parameters

    -   `value`: The value to enrich.
    -   `inline`: If {py:data}`True`, always return a {py:class}`rich.text.Text`
        suitable for inline display.

    ## Returns

    A Rich renderable ({py:class}`Text` if `inline=True`).

    ## Examples

    Printable strings are returned as-is:

    ```python
    >>> enrich("hello world")
    'hello world'

    ```

    Classes get special enriched formatting (module path . class name):

    ```python
    >>> import rich

    >>> rich.print(enrich(dict))
    dict

    >>> from collections.abc import Mapping

    >>> rich.print(enrich(Mapping))
    collections.abc.Mapping

    ```

    Other values are wrapped for Rich rendering. With `inline=False` (default),
    {py:class}`rich.pretty.Pretty` is used which can break over multiple lines
    when the console is narrow. With `inline=True`, output is always single-line
    {py:class}`rich.text.Text`.

    ```python
    >>> import sys
    >>> from rich.console import Console
    >>> narrow = Console(file=sys.stdout, width=15, no_color=True)
    >>> data = {"a": 1, "b": 2}

    >>> narrow.print(enrich(data))
    {
        'a': 1,
        'b': 2
    }

    >>> narrow.print(enrich(data, inline=True))
    {'a': 1, 'b': 2}

    ```
    """
    if is_rich(value) and (inline is False or isinstance(value, Text)):
        return value

    if isinstance(value, str):
        if all(c.isprintable() or c.isspace() for c in value):
            return value
        else:
            return repr_highlight(value)

    fallback = repr_highlight if inline else Pretty

    if isclass(value):
        return enrich_type(value)

    if isroutine(value):
        return fmt_routine(value, fallback=fallback)

    return fallback(value)
