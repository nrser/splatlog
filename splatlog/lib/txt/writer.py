from __future__ import annotations
from collections.abc import Callable, Iterable
from contextlib import contextmanager
import dataclasses as dc
from io import StringIO
from typing import (
    ContextManager,
    Literal,
    Self,
    Unpack,
)
from io import TextIOBase

from .opts import Opts, OptsKwds

type JoinSpace = Literal["never", "opt", "req"]


@dc.dataclass
class Writer:
    io: TextIOBase
    opts: Opts = dc.field(default_factory=Opts)

    at_newline: bool = True
    indent_level: int = 0

    def with_opts(self, **kwds: Unpack[OptsKwds]) -> Self:
        return dc.replace(self, opts=dc.replace(self.opts, **kwds))

    def write(self, text: str) -> None:
        """
        Write a string to the output. `value` is assumed to be a coherent
        chunk.
        """
        if text == "":
            return

        if "\n" in text:
            return self.write_lines(text.split("\n"))

        # If we're on a new line and have an indent level then write the indent
        # first
        if self.at_newline and self.indent_level:
            self.io.write(" " * self.indent_level)

        # Write the content
        self.io.write(text)

        # As we handled empty text and text with newlines separately we know
        # we're no longer on a new line
        self.at_newline = False

    def write_lines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.io.write(line)
            self.io.write("\n")

    @contextmanager
    def concat(self):
        """
        Stick chunks written in this context together (concatenate).
        """
        chunks = self.io
        self.io = StringIO()
        yield
        s = self.io.getvalue()
        self.io = chunks
        self.write(s)

    def join(
        self,
        sep: str,
        *,
        space: JoinSpace | tuple[JoinSpace, JoinSpace] = "never",
    ) -> ContextManager:
        """
        Join chunks written in this context, adding `space` around the separator
        — both sides or different before and after.
        """
        raise NotImplementedError("TODO")

    def space(self) -> None:
        """
        Insert a space between chunks written before and after.
        """
        self.io.write(" ")
        self.at_newline = False

    def write_obj(self, obj: object) -> None:
        self.write(repr(obj))

    def write_fmt(self, obj: object) -> None:
        raise NotImplementedError("TODO")

    def newline(self) -> None:
        self.io.write("\n")
        self.at_newline = True

    def p(self, *items):
        for item in items:
            if isinstance(item, str):
                self.write(item)
            else:
                self.write_fmt(item)
