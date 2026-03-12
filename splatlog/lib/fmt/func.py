from __future__ import annotations
from collections.abc import Callable
import dataclasses as dc
from typing import (
    Concatenate,
    Self,
)

from .opts import FmtOpts
from .writer import FmtWriter
from .chunk_io import ChunkIO, FmtOut


@dc.dataclass(frozen=True)
class FmtFunc[**P]:
    fn: Callable[Concatenate[FmtWriter, P], None]
    opts: FmtOpts = dc.field(default_factory=FmtOpts)

    def with_opts(
        self,
        *,
        fallback: Callable[[object], str] = repr,
        fqn: bool = True,
        fq_builtins: bool = False,
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
                fqn=fqn,
                fq_builtins=fq_builtins,
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

    def into(self, f: FmtWriter, *args: P.args, **kwds: P.kwargs) -> None:
        # TODO  This would need handling before and after to group the output
        #       from the call together
        self.fn(f, *args, **kwds)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> FmtOut:
        io = ChunkIO()
        f = FmtWriter(io=io, opts=self.opts)
        self.into(f, *args, **kwds)
        return io.getvalue()
