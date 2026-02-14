"""
Name-Type-Value table rendering for Rich.
"""

from __future__ import annotations
from typing import Any, Callable, ClassVar, TypeAlias, cast
from inspect import isclass
from collections.abc import Mapping, Iterable
import dataclasses as dc

from rich.table import Table, Column
from rich.padding import PaddingDimensions
from rich.box import Box
from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderResult,
)

from splatlog.types import SupportsRichComparison, is_rich

from .enrich import enrich, enrich_type, enrich_type_of


TableSource: TypeAlias = Mapping[str, object] | Iterable[tuple[str, object]]
"""
A collection of name/value associations, as either:

1.  {py:class}`~collections.abc.Mapping` of `{str: object}` pairs
2.  {py:class}`~collections.abc.Iterable` of `(str, object)` pairs
"""


# Renderable Class
# ============================================================================
#
# To work around failures when rendering a NTV table from `rich.print` and other
# ways that don't have our additional theme styles available.


@dc.dataclass
class NtvTable(ConsoleRenderable):
    """
    A {py:class}`rich.console.ConsoleRenderable` that renders a
    {py:class}`rich.table.Table` with `(name, type, value)` columns from a
    {py:type}`TableSource` mapping {py:class}`str` names to {py:class}`object`
    values.

    This {py:func}`dataclasses.dataclass` holds the configuration and constructs
    the {py:class}`rich.table.Table` at render-time so we can resolve styles
    against the given {py:class}`rich.console.Console` with graceful fallbacks.

    ## Examples

    1.  Basic usage

        ```py
        >>> from rich.console import Console
        >>> _print = Console(no_color=True, force_terminal=False).print

        >>> _print(NtvTable({"a": 1, "b": "bee!"}))
        a           int          1
        b           str          bee!

        ```

    2.  Show column names

        ```py
        >>> _print(NtvTable({"a": 1, "b": "bee!"}, show_header=True))
        Name        Type        Value
        a           int          1
        b           str          bee!

        ```

    3.  Sort rows by name

        ```py
        >>> _print(
        ...     NtvTable({"bob": 123, "carol": 456, "alice": 789}, sort=True)
        ... )
        alice       int          789
        bob         int          123
        carol       int          456

        ```

    4.  Custom sort (descending by value)

        ```py
        >>> _print(
        ...     NtvTable(
        ...         {"bob": 123, "carol": 456, "alice": 789},
        ...         sort=lambda kv: -kv[1]
        ...     )
        ... )
        alice       int          789
        carol       int          456
        bob         int          123

        ```
    """

    DEFAULT_COL_SETUP: ClassVar[tuple[dict[str, Any], ...]] = (
        {"min_width": 10},
        {"min_width": 10, "max_width": 40},
        {"min_width": 10},
    )
    """
    Defaults values for header {py:class}`rich.table.Column`, by column index.
    """

    source: TableSource
    """
    A {py:type}`TableSource` mapping {py:class}`str` names to {py:class}`object`
    values.
    """

    headers: tuple[Column | str, ...] = dc.field(
        default=("Name", "Type", "Value")
    )
    """
    Column headers for the table, see {py:meth}`NtvTable.columns` for details.
    """

    box: Box | None = None
    """See {py:class}`rich.table.Table`."""

    padding: PaddingDimensions = (0, 1)
    """See {py:class}`rich.table.Table`."""

    collapse_padding: bool = True
    """See {py:class}`rich.table.Table`."""

    show_header: bool = False
    """See {py:class}`rich.table.Table`."""

    show_footer: bool = False
    """See {py:class}`rich.table.Table`."""

    show_edge: bool = False
    """See {py:class}`rich.table.Table`."""

    pad_edge: bool = False
    """See {py:class}`rich.table.Table`."""

    sort: bool | Callable[[tuple[str, object]], SupportsRichComparison] = False
    """
    How to sort the table rows:

    1.  `False` (default) — source rows are added in iteration order. Note
        that you can control this externally by passing an
        `Iterable[tuple[str, object]]` instead of a `Mapping[str, object]`.

    2.  `True` — source is converted to an `Iterable[tuple[str, object]]` (if
        needed) and passed through {py:func}`sorted`, which pretty much amounts
        to sorting the rows by name.

    3.  `((str, object)) -> SupportsRichComparison` — same as (2) but with this
        function given as the `key=` parameter, allowing you to customize the
        sort order.
    """

    extras: dict[str, Any] = dc.field(default_factory=dict)
    """Additional keyword arguments for {py:class}`rich.table.Table`."""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """
        Render the {py:class}`rich.table.Table`, using the instance attributes
        as well as style (and potentially other) information from the given
        {py:class}`rich.console.Console`.
        """
        table = Table(
            *self.columns(console),
            box=self.box,
            padding=self.padding,
            collapse_padding=self.collapse_padding,
            show_header=self.show_header,
            show_footer=self.show_footer,
            show_edge=self.show_edge,
            pad_edge=self.pad_edge,
            **self.extras,
        )

        items = (
            cast(Iterable[tuple[str, object]], self.source.items())
            if isinstance(self.source, Mapping)
            else self.source
        )

        if self.sort is False:
            pass
        elif self.sort is True:
            items = sorted(items)
        else:
            items = sorted(items, key=self.sort)

        for key, value in items:
            if is_rich(value) and value.__class__.__module__.startswith(
                "rich."
            ):
                rich_value_type = None
                rich_value = value
            elif isclass(value):
                rich_value_type = None
                rich_value = enrich_type(value)
            else:
                rich_value_type = enrich_type_of(value)
                rich_value = enrich(value)
            table.add_row(key, rich_value_type, rich_value)

        return (table,)

    def columns(self, console: Console) -> list[Column]:
        """
        Convert the {py:attr}`NtvTable.headers` to a {py:class}`list` of
        {py:class}`rich.table.Column` to use as the {py:class}`rich.table.Table`
        headers.

        Builds columns from {py:class}`str` headers, applying style and the
        {py:data}`NtvTable.DEFAULT_COL_SETUP` values for the corresponding
        index, if any.

        {py:class}`rich.table.Column` headers have the style and defaults
        applied if those attributes are {py:data}`None`.

        Needs the {py:class}`rich.console.Console` to get styles with fallback,
        so we can prefer Splatlog styles but manage without them.
        """
        style = console.get_style("log.data.name", default="repr.attrib_name")

        columns: list[Column] = []

        for i, header in enumerate(self.headers):
            defaults: dict[str, Any] = {"style": style}
            if i < len(self.DEFAULT_COL_SETUP):
                defaults.update(self.DEFAULT_COL_SETUP[i])

            match header:
                case str(name):
                    columns.append(Column(name, **defaults))

                case col if isinstance(col, Column):
                    for k, v in defaults.items():
                        if getattr(col, k, None) is None:
                            setattr(col, k, v)

                    columns.append(col)

        return columns
