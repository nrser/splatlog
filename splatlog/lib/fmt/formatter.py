from __future__ import annotations
from collections.abc import Callable, Iterable
import dataclasses as dc
from typing import (
    Concatenate,
    Never,
    Self,
    Unpack,
    cast,
)

from splatlog.types import assert_never

from .opts import FmtOpts, FmtOptsKwds


@dc.dataclass(frozen=True)
class Formatter[**P]:
    fn: Callable[Concatenate[FmtOpts, P], str | Iterable[str]]
    opts: FmtOpts = dc.field(default_factory=FmtOpts)

    def with_opts(self, opts: FmtOpts | None = None, **kwds: Unpack[FmtOptsKwds]) -> Self:
        new_opts = self.opts

        if opts:
            new_opts = dc.replace(new_opts, **dc.asdict(opts))

        if kwds:
            new_opts = dc.replace(new_opts, **kwds)

        return dc.replace(self, opts=new_opts)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> str:
        match self.fn(self.opts, *args, **kwds):
            case str(s):
                return s
            case itr if isinstance(itr, Iterable):
                return "".join(itr)
            case other:
                assert_never(cast(Never, other), str | Iterable[str])
