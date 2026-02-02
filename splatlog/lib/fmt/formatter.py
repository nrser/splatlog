"""
The {py:class}`Formatter` interface, just so it's in a different file, so I
don't have to scroll up and down to it.
"""

from typing import (
    AnyStr,
    Callable,
    ContextManager,
    Literal,
    Protocol,
    TypeAlias,
)


JoinSpace: TypeAlias = Literal["never", "opt", "req"]


class Formatter(Protocol):
    fqn: bool
    fq_builtins: bool
    fallback: Callable[[object], str]

    def write(self, value: AnyStr) -> int:
        """
        Write a string to the output. `value` is assumed to be a coherent
        chunk.
        """
        ...

    def concat(self) -> ContextManager:
        """
        Stick chunks written in this context together (concatenate).
        """
        ...

    def join(
        self,
        sep: str,
        *,
        space: JoinSpace | tuple[JoinSpace, JoinSpace] = "never",
    ) -> ContextManager: ...

    def space(self) -> None:
        """
        Insert a space between chunks written before and after.
        """
        ...

    def write_object(self, x: object) -> None:
        self.write(repr(x))
