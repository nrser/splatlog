from __future__ import annotations
from inspect import isclass
from typing import Protocol, TypeGuard, runtime_checkable

from rich.repr import RichReprResult


def implements_rich_repr(x: object) -> TypeGuard[RichRepr]:
    return isinstance(x, RichRepr) and not isclass(x)


@runtime_checkable
class RichRepr(Protocol):
    def __rich_repr__(self) -> RichReprResult:
        ...
