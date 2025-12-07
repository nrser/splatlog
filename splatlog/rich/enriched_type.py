from __future__ import annotations
from typing import Type

from rich.console import (
    Console,
    ConsoleOptions,
    RenderResult,
)
from rich.text import Text
from rich.measure import Measurement
from splatlog.lib.functions import SlotCachedProperty

from splatlog.lib.text import BUILTINS_MODULE

_MODULE_STYLE = "inspect.class"
_CLASS_STYLE = "repr.tag_name"
_INDENT = "  "
_INDENT_LENGTH = len(_INDENT)


class EnrichedType:
    """
    Wraps a class object in a `rich.console.ConsoleRenderable` that either
    prints it as a single line (if there is space) or a tree-like stack,
    distinctly styling the module and class name so they're easy to pick out.

    ##### Examples #####

    ```python
    >>> wide = Console(width=80)
    >>> narrow = Console(width=30)

    >>> class MyType:
    ...     pass

    >>> wide.print(EnrichedType(MyType))
    splatlog.rich.enriched_type.MyType

    >>> narrow.print(EnrichedType(MyType))
    splatlog
      .rich
        .enriched_type
          .MyType

    ```
    """

    __slots__ = ("_type", "_min_width", "_max_width", "_parts")

    _type: Type[object]

    def __init__(self, typ: Type[object]):
        self._type = typ

    @SlotCachedProperty
    def parts(self) -> list[str]:
        if self._type.__module__ == BUILTINS_MODULE:
            return [self._type.__qualname__]
        parts = self._type.__module__.split(".")
        parts.append(self._type.__qualname__)
        return parts

    @SlotCachedProperty
    def min_width(self) -> int:
        if self._type.__module__ == BUILTINS_MODULE:
            return len(self._type.__qualname__)
        return max(
            (len(name) + _INDENT_LENGTH * index + int(bool(index)))
            for index, name in enumerate(self.parts)
        )

    @SlotCachedProperty
    def max_width(self) -> int:
        return len(self._type.__module__) + 1 + len(self._type.__qualname__)

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(self.min_width, self.max_width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self._type.__module__ == BUILTINS_MODULE:
            yield Text(self._type.__qualname__, style=_CLASS_STYLE)
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
