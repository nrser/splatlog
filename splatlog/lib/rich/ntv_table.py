from __future__ import annotations
from typing import (
    Any,
    Callable,
    Optional,
    Protocol,
    TypeAlias,
    TypeVar,
    cast,
)
from inspect import isclass
from collections.abc import Mapping, Iterable
import dataclasses as dc

from rich.table import Table, Column
from rich.padding import PaddingDimensions
from rich.box import Box
from rich.console import Console, ConsoleOptions, RenderResult

from .typings import is_rich
from .enrich import enrich, enrich_type, enrich_type_of

# Typings
# ============================================================================

_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsDunderLT(Protocol[_T_contra]):
    def __lt__(self, __other: _T_contra) -> bool: ...


class SupportsDunderGT(Protocol[_T_contra]):
    def __gt__(self, __other: _T_contra) -> bool: ...


# If we need them in the future...
#
# class SupportsDunderLE(Protocol[_T_contra]):
#     def __le__(self, __other: _T_contra) -> bool:
#         ...
#
# class SupportsDunderGE(Protocol[_T_contra]):
#     def __ge__(self, __other: _T_contra) -> bool:
#         ...


#: A type that supports `<` and `>` operations (`__lt__` and `__gt__` methods).
#:
#: Copied from whatever VSCode is using for type definitions since I can't
#: figure out how to import or reference it.
#:
SupportsRichComparison: TypeAlias = (
    SupportsDunderLT[Any] | SupportsDunderGT[Any]
)

# If we need it in the future...
# SupportsRichComparisonT = TypeVar("SupportsRichComparisonT", bound=SupportsRichComparison)


#: A collection of name/value associations, as either:
#:
#: 1.   `collections.abc.Mapping` of `{str: object}` pairs
#: 2.   `collections.abc.Iterable` of `(str, object)` pairs
#:
TableSource = Mapping[str, object] | Iterable[tuple[str, object]]


# Renderable Class
# ============================================================================
#
# To work around failures when rendering a NTV table from `rich.print` and other
# ways that don't have our additional theme styles available.


@dc.dataclass
class NtvTable:
    """
    Renderable that constructs an NTV `Table` at render time so we can resolve
    styles against the rendering `Console` with graceful fallbacks.
    """

    source: TableSource
    headers: tuple[Column | str, ...] = dc.field(default_factory=tuple)
    box: Box | None = None
    padding: PaddingDimensions = (0, 1)
    collapse_padding: bool = True
    show_header: bool = False
    show_footer: bool = False
    show_edge: bool = False
    pad_edge: bool = False
    sort: bool | Callable[[tuple[str, object]], SupportsRichComparison] = False
    rich_table_kwds: dict[str, Any] = dc.field(default_factory=dict)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(
            *self.headers,
            box=self.box,
            padding=self.padding,
            collapse_padding=self.collapse_padding,
            show_header=self.show_header,
            show_footer=self.show_footer,
            show_edge=self.show_edge,
            pad_edge=self.pad_edge,
            **self.rich_table_kwds,
        )

        if len(self.headers) == 0:
            name_style = console.get_style(
                "log.data.name", default="repr.attrib_name"
            )
            table.add_column("Name", style=name_style, min_width=10)
            # table.add_column("Type", style="log.data.type")
            table.add_column("Type", min_width=10, max_width=40)
            table.add_column("Value", min_width=10)

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

        yield table


# Functional API
# ============================================================================
#
# Pre-dates the renderable class, now simply offers a convenient interface
# similar to the `rich.table.Table` constructor to create a `NtvTable`.


def ntv_table(
    source: TableSource,
    *headers: Column | str,
    box: Optional[Box] = None,
    padding: PaddingDimensions = (0, 1),
    collapse_padding: bool = True,
    show_header: bool = False,
    show_footer: bool = False,
    show_edge: bool = False,
    pad_edge: bool = False,
    sort: bool | Callable[[tuple[str, object]], SupportsRichComparison] = False,
    **rich_table_kwds: Any,
) -> NtvTable:
    """
    Create a renderable that prints a `rich.table.Table` with (name, type, value)
    columns from a `TableSource` mapping `str` names to `object` values.

    ##### Parameters #####

    -   `source` — a `TableSource` mapping `str` names to `object` values.

    -   `headers` — if given, passed to `rich.table.Table`. If omitted then then
        Name, Type and Value columns are automatically added (see source).

    -   `sort` — when...

        1.  `False` (default) — source rows are added in iteration order. Note
            that you can control this externally by passing an
            `Iterable[tuple[str, object]]` instead of a `Mapping[str, object]`.

        2.  `True` — source is converted to an `Iterable[tuple[str, object]]`
            (if needed) and passed through `sorted`, which pretty much amounts
            to sorting the rows by name.

        3.  `((str, object)) -> SupportsRichComparison` — same as (2) but with
            `sort` given as the `key=` parameter, allowing you to customize the
            sort order.

    -   everything else — passed to `rich.table.Table`.

    ##### Returns #####

    A renderable that renders to a `rich.table.Table` with three columns (name,
    type, value). Styles are resolved at render time with a fallback so it works
    with `rich.print` even if the default console theme lacks custom styles.

    ##### Examples #####

    1.  Basic usage

        ```py
        >>> import rich

        >>> rich.print(ntv_table({"a": 1, "b": "bee!"}))
        a           int          1
        b           str          bee!

        ```

    2.  Show column names

        ```py
        >>> rich.print(ntv_table({"a": 1, "b": "bee!"}, show_header=True))
        Name        Type        Value
        a           int          1
        b           str          bee!

        ```

    3.  Sort rows by name

        ```py
        >>> rich.print(
        ...     ntv_table({"bob": 123, "carol": 456, "alice": 789}, sort=True)
        ... )
        alice       int          789
        bob         int          123
        carol       int          456

        ```

    4.  Custom sort (descending by value)

        ```py
        >>> rich.print(
        ...     ntv_table(
        ...         {"bob": 123, "carol": 456, "alice": 789},
        ...         sort=lambda kv: -kv[1]
        ...     )
        ... )
        alice       int          789
        carol       int          456
        bob         int          123

        ```
    """

    return NtvTable(
        source=source,
        headers=headers,
        box=box,
        padding=padding,
        collapse_padding=collapse_padding,
        show_header=show_header,
        show_footer=show_footer,
        show_edge=show_edge,
        pad_edge=pad_edge,
        sort=sort,
        **rich_table_kwds,
    )
