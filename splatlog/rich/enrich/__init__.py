"""
Utilities for enriching Python values with Rich formatting.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, cast
from inspect import isroutine
import datetime as dt

from rich.console import RenderableType
from rich.pretty import Pretty
from rich.highlighter import Highlighter, ReprHighlighter
from rich.text import Text, TextType

from splatlog.lib import has_method
from splatlog.lib.types import is_number
from splatlog.types import is_rich

from .enriched import Enriched, unwrap
from .enrichment import (
    EnrichOpts,
    EnrichKwds,
    enrichment,
    get_default_enrich_opts,
    set_default_enrich_opts,
    override_enrich_opts,
)
from .exception import EnrichedException
from .path import EnrichedPath

# NOTE  Calling this `type` breaks the `type` built-in
from .typ import EnrichedType
from .number import enrich_number, EnrichedId
from .routine import enrich_routine
from .datetime import (
    enrich_datetime,
    enrich_date,
    enrich_time,
    enrich_timedelta,
)

__all__ = [
    "enrich_number",
    "enrich_routine",
    "enrich_type_of",
    "enrich_type",
    "enrich",
    "Enriched",
    "EnrichedException",
    "EnrichedId",
    "EnrichedType",
    "EnrichKwds",
    "EnrichOpts",
    "get_default_enrich_opts",
    "set_default_enrich_opts",
    "override_enrich_opts",
    "highlighted",
    "repr_highlight",
    "REPR_HIGHLIGHTER",
    "unwrap",
]


REPR_HIGHLIGHTER = ReprHighlighter()
"""
Shared {py:class}`rich.highlighter.ReprHighlighter` instance for {py:func}`repr`
syntax highlighting.
"""

# `enrich` — General Interface / Entry Point
# ============================================================================


@enrichment
def enrich(value: object, opts: EnrichOpts) -> RenderableType:
    """
    Convert a Python value to a Rich renderable.

    Leaf values (numbers, dates/times) are first formatted via
    {py:mod}`splatlog.lib.text` — honoring {py:class}`EnrichOpts` (an
    {py:class}`~splatlog.lib.text.FmtOpts`) — and then styled for Rich display.
    Types, routines, paths, and exceptions get their own enriched renderings,
    and values that are already Rich renderables are returned as-is.

    ## Parameters

    -   `value`: The value to enrich.
    -   `opts`: {py:class}`EnrichOpts` controlling formatting and enrichment.
    -   `kwds`: {py:class}`EnrichKwds` keyword arguments, merged over `opts`
        (see {py:meth}`EnrichOpts.replace`) — e.g. `enrich(x, i_fmt="{:_}")`.

    ## Returns

    A Rich renderable.

    ## Examples

    Printable strings are returned as-is:

    ```python
    >>> enrich("hello world")
    'hello world'

    ```

    Numbers are formatted (grouped by default) and styled:

    ```python
    >>> enrich(1234567).plain
    '1,234,567'

    ```

    Formatting is customized through {py:class}`EnrichKwds`/{py:class}`EnrichOpts`:

    ```python
    >>> enrich(1234567, i_fmt="{:_}").plain
    '1_234_567'

    ```

    Classes get special enriched formatting (module path . class name):

    ```python
    >>> from rich.console import Console
    >>> _print = Console(no_color=True, force_terminal=False).print

    >>> _print(enrich(dict))
    dict

    >>> from collections.abc import Mapping

    >>> _print(enrich(Mapping))
    collections.abc.Mapping

    ```

    Other values are wrapped in {py:class}`rich.pretty.Pretty`, which can break
    over multiple lines when the console is narrow.

    ```python
    >>> import sys
    >>> from rich.console import Console
    >>> narrow = Console(file=sys.stdout, width=15, no_color=True, force_terminal=False)
    >>> data = {"a": 1, "b": 2}

    >>> narrow.print(enrich(data))
    {
        'a': 1,
        'b': 2
    }

    ```
    """
    if has_method(value, "_enrich_"):
        return cast(Any, value)._enrich_()

    match value:
        # Does the object implement rich-rendering itself?
        case r if is_rich(r):
            # If so, use it as-is
            return r

        case str(s) if s.isprintable():
            return s

        case str(s):
            return repr_highlight(s)

        case type() as t:
            return enrich_type(t, opts)

        case fn if isroutine(fn):
            return enrich_routine(fn, opts)

        case Path() as p:
            return enrich_path(p)

        case BaseException() as err:
            return EnrichedException(err)

        case n if is_number(n):
            return enrich_number(n, opts)

        case dt.datetime() as d:
            return enrich_datetime(d, opts)

        case dt.date() as d:
            return enrich_date(d, opts)

        case dt.time() as t:
            return enrich_time(t, opts)

        case dt.timedelta() as t:
            return enrich_timedelta(t, opts.td_fmt)

        case _:
            return Pretty(value)


# Supporting Functions
# ============================================================================


def highlighted(
    text: TextType, highlighter: Highlighter = REPR_HIGHLIGHTER
) -> Text:
    r"""
    {py:meth}`~rich.highlighter.Highlighter.highlight` some `text`.

    Differs from {py:meth}`~rich.highlighter.Highlighter.__call__` in
    {py:class}`str` → {py:class}`~rich.text.Text` conversion: **_no_**
    `"\n"`{l=py} **_appended_**. That's it.

    ## Parameters

    -   `text`: to highlight.
    -   `highlighter`: By default, uses a
        {py:class}`~rich.highlighter.ReprHighlighter`, but you can provide
        another.

    ## Returns

    Highlighted {py:class}`~rich.text.Text`.
    """
    if isinstance(text, str):
        text = Text(text, end="")
    highlighter.highlight(text)
    return text


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


@enrichment
def enrich_type(typ: type[object], opts: EnrichOpts) -> RenderableType:
    """
    Create a Rich renderable for a type.

    If the type has a `__rich_type__` method, calls it. Otherwise wraps
    in {py:class}`EnrichedType`.

    ## Parameters

    -   `typ`: The type to enrich.
    -   `opts`: {py:class}`EnrichOpts`; its {py:attr}`~splatlog.lib.text.FmtOpts.fqn`
        controls whether the module prefix is included.
    -   `kwds`: {py:class}`EnrichKwds` keyword arguments, merged over `opts` —
        e.g. `enrich_type(t, fqn=False)`.

    ## Returns

    A Rich renderable representing the type.
    """
    if (rich_type := getattr(typ, "__rich_type__", None)) and isinstance(
        rich_type, Callable
    ):
        return rich_type()

    if opts.fqn:
        return EnrichedType(typ)

    return Text(typ.__qualname__, style="repr.tag_name", end="")


@enrichment
def enrich_type_of(value: object, opts: EnrichOpts) -> RenderableType:
    """
    Create a Rich renderable for the type of a value.

    Shorthand for `enrich_type(type(value))`, but {py:class}`Enriched` wrappers
    are {py:func}`unwrap`ped first so the _underlying_ value's type is reported
    (e.g. an {py:class}`EnrichedId` yields `int`, not `EnrichedId`).
    """
    return enrich_type(type(unwrap(value)), opts)


@enrichment
def enrich_path(path: Path, opts: EnrichOpts) -> RenderableType:
    """
    Create a Rich renderable for a path.

    Wraps in {py:class}`EnrichedPath` which shortens and adapts to
    available console width.

    ## Parameters

    -   `path`: The path to enrich.

    ## Returns

    A Rich renderable representing the path.
    """
    return EnrichedPath(path)
