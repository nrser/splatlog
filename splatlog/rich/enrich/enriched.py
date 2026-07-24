"""
Base class for enriched values.

{py:mod}`splatlog.rich.enrich` produces small wrapper objects — like
{py:class}`~splatlog.rich.enrich.EnrichedPath`,
{py:class}`~splatlog.rich.enrich.EnrichedType`,
{py:class}`~splatlog.rich.enrich.EnrichedException`, and
{py:class}`~splatlog.rich.enrich.EnrichedId` — that pair a Python value with a
Rich rendering of it (each implements the Rich console protocol).

{py:class}`Enriched` is their common base, so callers can:

-   test whether a value is an enriched wrapper with a single
    `isinstance(value, Enriched)`, and
-   recover the underlying value with {py:attr}`Enriched.value` or
    {py:func}`unwrap`.

This matters when an enriched value flows somewhere that cares about the
_original_ — e.g. determining the value's real {py:class}`type`, or serializing
it — rather than its display form.
"""

from __future__ import annotations
import dataclasses as dc
from abc import ABC, abstractmethod
from typing import overload

from rich.console import Console, ConsoleOptions, RenderResult


@dc.dataclass(frozen=True)
class Enriched[T](ABC):
    """
    Abstract base for Rich-renderable wrappers around a value of type `T`.

    The wrapped value is a plain {py:attr}`value` field that subclasses provide
    at construction — there's no property for subclasses to implement.

    Subclasses must render themselves via {py:meth}`__rich_console__` (the
    abstract method enforced here); a subclass that would rather implement
    {py:meth}`__rich__` can simply forward to it.
    """

    value: T
    """The underlying value this wrapper enriches."""

    @abstractmethod
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render this wrapper (Rich console protocol)."""
        ...


@overload
def unwrap[T](value: Enriched[T]) -> T: ...


@overload
def unwrap[T](value: T) -> T: ...


def unwrap(value):
    """
    Return the underlying value if `value` is {py:class}`Enriched`, otherwise
    return `value` unchanged.

    ## Examples

    ```pycon
    >>> from splatlog.rich.enrich import EnrichedId

    >>> unwrap(EnrichedId(5733))
    5733

    >>> unwrap(5733)
    5733

    ```
    """
    return value.value if isinstance(value, Enriched) else value
