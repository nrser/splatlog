from string import Formatter
from typing import Any, Callable, Mapping, Sequence, TypeVar, cast

from rich.text import Text
from rich.segment import Segment

from splatlog.lib.typeguard import check_type
from splatlog.lib.text import fmt, fmt_type_of
from .enrich import enrich, repr_highlight


Self = TypeVar("Self", bound="Inline")


class Inline(tuple[object, ...]):
    def __new__(cls: type[Self], *values) -> Self:
        return tuple.__new__(cls, values)

    def __str__(self) -> str:
        return " ".join(
            (entry if isinstance(entry, str) else repr(entry)) for entry in self
        )

    def __rich__(self):
        text = Text()
        for index, entry in enumerate(self):
            if index != 0:
                text.append(" ")
            if isinstance(entry, str):
                text.append(entry)
            else:
                text.append(enrich(entry, inline=True))
        return text
