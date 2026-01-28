from typing import Self
from rich.text import Text
from .enrich import enrich


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
