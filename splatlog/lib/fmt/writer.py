from __future__ import annotations
from collections.abc import Callable
from contextlib import contextmanager
import dataclasses as dc
from io import StringIO
from typing import (
    ContextManager,
    Literal,
    Self,
)
from io import TextIOBase

from .opts import FmtOpts
from .chunk_io import FmtOut

type JoinSpace = Literal["never", "opt", "req"]


@dc.dataclass
class FmtWriter:
    io: TextIOBase
    opts: FmtOpts = dc.field(default_factory=FmtOpts)

    def with_opts(
        self,
        *,
        fallback: Callable[[object], FmtOut] = repr,
        module_names: bool = True,
        omit_builtins: bool = True,
        items: int | None = None,
        ellipsis: str = "...",
        ls_sep: str = ",",
        ls_conj: str | None = None,
        ls_ox: bool = True,
        type: bool = False,
        quote: bool = False,
        d_fmt: str = FmtOpts.DEFAULT_D_FMT,
        t_fmt: str = FmtOpts.DEFAULT_T_FMT,
        dt_fmt: str = FmtOpts.DEFAULT_DT_FMT,
    ) -> Self:
        return dc.replace(
            self,
            opts=dc.replace(
                self.opts,
                fallback=fallback,
                module_names=module_names,
                omit_builtins=omit_builtins,
                items=items,
                ellipsis=ellipsis,
                ls_sep=ls_sep,
                ls_conj=ls_conj,
                ls_ox=ls_ox,
                type=type,
                quote=quote,
                d_fmt=d_fmt,
                t_fmt=t_fmt,
                dt_fmt=dt_fmt,
            ),
        )

    def write(self, value: str) -> int:
        """
        Write a string to the output. `value` is assumed to be a coherent
        chunk.
        """
        return self.io.write(value)

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
        self.write(" ")

    def write_obj(self, obj: object) -> None:
        self.write(repr(obj))
