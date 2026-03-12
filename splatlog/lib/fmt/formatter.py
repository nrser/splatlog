from __future__ import annotations
from collections.abc import Callable
import dataclasses as dc
from typing import (
    Concatenate,
    Self,
    Unpack,
    overload,
)

from .opts import FmtOpts, OptsKwds
from .writer import FmtWriter
from .chunk_io import ChunkIO, FmtOut


@overload
def formatter[**P](
    **kwds: Unpack[OptsKwds],
) -> Callable[[Callable[Concatenate[FmtWriter, P], None]], Formatter[P]]: ...


@overload
def formatter[**P](
    fn: Callable[Concatenate[FmtWriter, P], None],
    /,
) -> Formatter[P]: ...


def formatter[**P](
    fn: Callable[Concatenate[FmtWriter, P], None] | None = None,
    /,
    **kwds: Unpack[OptsKwds],
):
    def wrap(
        fn: Callable[Concatenate[FmtWriter, P], None],
        /,
    ) -> Formatter[P]:
        return Formatter(fn=fn, opts=FmtOpts(**kwds))

    if fn is None:
        return wrap

    return wrap(fn)


@dc.dataclass(frozen=True)
class Formatter[**P]:
    fn: Callable[Concatenate[FmtWriter, P], None]
    opts: FmtOpts = dc.field(default_factory=FmtOpts)

    def __post_init__(self):
        # Carry the `__doc__` along so we can doctest (after surmounting
        # additional challenges)
        if self.fn.__doc__:
            # Object is already frozen (why?!?), but we can get around that (of
            # course!) with `object.__setattr__`
            object.__setattr__(self, "__doc__", self.fn.__doc__)

    def with_opts(self, **kwds: Unpack[OptsKwds]) -> Self:
        return dc.replace(self, opts=dc.replace(self.opts, **kwds))

    def into(self, f: FmtWriter, *args: P.args, **kwds: P.kwargs) -> None:
        # TODO  This would need handling before and after to group the output
        #       from the call together
        self.fn(f, *args, **kwds)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> FmtOut:
        io = ChunkIO()
        f = FmtWriter(io=io, opts=self.opts)
        self.into(f, *args, **kwds)
        return io.getvalue()
