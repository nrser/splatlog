"""
Rich-renderable wrapper for type objects.
"""

from __future__ import annotations

from rich.console import (
    Console,
    ConsoleOptions,
    RenderResult,
)
from rich.text import Text
from rich.measure import Measurement
from splatlog.lib.functions import SlotCachedProperty

from splatlog.lib.types import is_builtins
from splatlog.lib.text import fmt_type

_MODULE_STYLE = "inspect.class"
_CLASS_STYLE = "repr.tag_name"
_INDENT = "  "
_INDENT_LENGTH = len(_INDENT)


class EnrichedType:
    """
    Wraps a class object in a {py:class}`rich.console.ConsoleRenderable` that
    either prints it as a single line (if there is space) or a tree-like stack,
    distinctly styling the module and class name so they're easy to pick out.

    ## Examples

    ```python
    >>> import sys

    >>> wide = Console(file=sys.stdout, width=80, no_color=True, force_terminal=False)
    >>> narrow = Console(file=sys.stdout, width=30, no_color=True, force_terminal=False)

    >>> class MyType:
    ...     pass

    >>> wide.print(EnrichedType(MyType))
    splatlog.rich.enrich.enriched_type.MyType

    >>> narrow.print(EnrichedType(MyType))
    splatlog
      .rich
        .enrich
          .enriched_type
            .MyType

    ```
    """

    __slots__ = ("_type", "_min_width", "_max_width", "_parts")

    _type: type[object]
    """The wrapped type object."""

    def __init__(self, typ: type[object]):
        """
        Create an enriched type wrapper.

        ## Parameters

        -   `typ`: The type to wrap.
        """
        self._type = typ

    @SlotCachedProperty
    def parts(self) -> list[str]:
        """The module path segments plus the class name."""
        if is_builtins(self._type):
            return [self._type.__qualname__]
        parts = self._type.__module__.split(".")
        parts.append(self._type.__qualname__)
        return parts

    @SlotCachedProperty
    def min_width(self) -> int:
        """Minimum display width (stacked/tree format)."""
        if is_builtins(self._type):
            return len(self._type.__qualname__)
        return max(
            (len(name) + _INDENT_LENGTH * index + int(bool(index)))
            for index, name in enumerate(self.parts)
        )

    @SlotCachedProperty
    def max_width(self) -> int:
        """Maximum display width (single-line format)."""
        return len(self._type.__module__) + 1 + len(self._type.__qualname__)

    def __repr__(self) -> str:
        """
        ## Examples

        ```python
        >>> print(EnrichedType(dict))
        EnrichedType(dict)

        >>> from collections.abc import Mapping

        >>> print(EnrichedType(Mapping))
        EnrichedType(collections.abc.Mapping)

        ```
        """
        return f"{self.__class__.__name__}({fmt_type(self._type)})"

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the min/max width for layout."""
        return Measurement(self.min_width, self.max_width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """
        Render the type, adapting to available width.

        ## Examples

        Wide console prints single-line:

        ```python
        >>> import sys
        >>> from collections.abc import Mapping

        >>> wide = Console(file=sys.stdout, width=80, no_color=True, force_terminal=False)
        >>> wide.print(EnrichedType(Mapping))
        collections.abc.Mapping

        ```

        Narrow console prints as a tree:

        ```python
        >>> narrow = Console(file=sys.stdout, width=20, no_color=True, force_terminal=False)
        >>> narrow.print(EnrichedType(Mapping))
        collections
          .abc
            .Mapping

        ```
        """
        if is_builtins(self._type):
            yield Text(self._type.__qualname__, style=_CLASS_STYLE, end="")
        else:
            if self.max_width < options.max_width:
                text = Text(no_wrap=True)
                for name in self.parts[:-1]:
                    text.append(name, style=_MODULE_STYLE)
                    text.append(".")
                text.append(self._type.__qualname__, style=_CLASS_STYLE)
                yield text
            else:
                for index, name in enumerate(self.parts[:-1]):
                    if index == 0:
                        yield Text(name, style=_MODULE_STYLE, no_wrap=True)
                    else:
                        yield Text.assemble(
                            _INDENT * index,
                            ".",
                            (name, _MODULE_STYLE),
                            no_wrap=True,
                        )
                yield Text.assemble(
                    _INDENT * (len(self.parts) - 1),
                    ".",
                    (self._type.__qualname__, _CLASS_STYLE),
                    no_wrap=True,
                )
