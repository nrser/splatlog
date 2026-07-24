"""
Rich-renderable wrapper for type objects.
"""

from __future__ import annotations

import dataclasses as dc

from rich.console import (
    Console,
    ConsoleOptions,
    RenderResult,
)
from rich.text import Text
from rich.measure import Measurement

from splatlog.lib.types import is_builtins
from splatlog.lib.text import fmt_name

from .enriched import Enriched

_MODULE_STYLE = "inspect.class"
_CLASS_STYLE = "repr.tag_name"
_INDENT = "  "
_INDENT_LENGTH = len(_INDENT)


@dc.dataclass(frozen=True)
class EnrichedType(Enriched[type[object]]):
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
    splatlog.rich.enrich.typ.MyType

    >>> narrow.print(EnrichedType(MyType))
    splatlog
      .rich
        .enrich
          .typ
            .MyType

    ```
    """

    @property
    def parts(self) -> list[str]:
        """The module path segments plus the class name."""
        if is_builtins(self.value):
            return [self.value.__qualname__]
        parts = self.value.__module__.split(".")
        parts.append(self.value.__qualname__)
        return parts

    @property
    def min_width(self) -> int:
        """Minimum display width (stacked/tree format)."""
        if is_builtins(self.value):
            return len(self.value.__qualname__)
        return max(
            (len(name) + _INDENT_LENGTH * index + int(bool(index)))
            for index, name in enumerate(self.parts)
        )

    @property
    def max_width(self) -> int:
        """Maximum display width (single-line format)."""
        return len(self.value.__module__) + 1 + len(self.value.__qualname__)

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
        return f"{self.__class__.__name__}({fmt_name(self.value)})"

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
        if is_builtins(self.value):
            yield Text(self.value.__qualname__, style=_CLASS_STYLE, end="")
        else:
            if self.max_width < options.max_width:
                text = Text(no_wrap=True)
                for name in self.parts[:-1]:
                    text.append(name, style=_MODULE_STYLE)
                    text.append(".")
                text.append(self.value.__qualname__, style=_CLASS_STYLE)
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
                    (self.value.__qualname__, _CLASS_STYLE),
                    no_wrap=True,
                )
