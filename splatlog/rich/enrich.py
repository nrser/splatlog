from __future__ import annotations
from typing import Callable, Literal, overload
from inspect import isclass, isroutine

from rich.console import RenderableType
from rich.pretty import Pretty
from rich.highlighter import ReprHighlighter
from rich.text import Text

from splatlog.lib.text import fmt_routine

from .enriched_type import EnrichedType
from .typings import is_rich


REPR_HIGHLIGHTER = ReprHighlighter()


def repr_highlight(value: object, *, use_ascii: bool = False) -> Text:
    text = Text(ascii(value) if use_ascii else repr(value), end="")
    REPR_HIGHLIGHTER.highlight(text)
    return text


def enrich_type(typ: type[object]) -> RenderableType:
    if (rich_type := getattr(typ, "__rich_type__", None)) and isinstance(
        rich_type, Callable
    ):
        return rich_type()
    return EnrichedType(typ)


def enrich_type_of(value: object) -> RenderableType:
    return enrich_type(type(value))


@overload
def enrich(value: object, inline: Literal[True]) -> Text: ...


@overload
def enrich(value: object, inline: Literal[False]) -> RenderableType: ...


@overload
def enrich(value: object) -> RenderableType: ...


def enrich(value, inline=False):
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
